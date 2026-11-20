"""Account services — self-service password reset by email."""

import logging

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.accounts.models import User

logger = logging.getLogger(__name__)


class InvalidResetLink(ValueError):
    """uid/token don't match an active user, or the token expired / was already used."""


def _reset_link(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"


def _send_reset_email(user):
    minutes = settings.PASSWORD_RESET_TIMEOUT // 60
    where = f" at {user.business.name}" if user.business_id else ""
    text = (
        f"Hi {user.name or user.username},\n\n"
        f"Someone asked to reset the password for your MessDeck account{where}.\n"
        f"Username: {user.username}\n\n"
        f"Set a new password here (the link works once, for {minutes} minutes):\n"
        f"{_reset_link(user)}\n\n"
        "If you didn't ask for this, ignore this email; your password stays the same."
    )
    send_mail("Reset your MessDeck password", text, settings.DEFAULT_FROM_EMAIL, [user.email])


class PasswordResetService:
    @staticmethod
    def request_reset(identifier):
        """Email a reset link to every active account matching a username or email.

        Returns nothing either way — callers must not reveal whether an account exists.
        One email can belong to several accounts (e.g. a customer of two messes); each gets a link.
        """
        identifier = identifier.strip()
        if not identifier:
            return
        users = (
            User.objects.select_related("business")
            .filter(Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=True)
            .exclude(email="")
        )
        for user in users:
            try:
                _send_reset_email(user)
            except Exception:  # SMTP down etc. — log, keep the response identical
                logger.exception("Password reset email to user %s failed", user.pk)

    @staticmethod
    def user_for_link(uid, token):
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise InvalidResetLink() from None
        if not default_token_generator.check_token(user, token):
            raise InvalidResetLink()
        return user

    @staticmethod
    @transaction.atomic
    def reset_password(uid, token, new_password):
        """Set the new password and sign the user out everywhere.

        Raises InvalidResetLink, or django ValidationError for a weak password.
        The token is single-use: it's derived from the password hash, which changes here.
        """
        user = PasswordResetService.user_for_link(uid, token)
        validate_password(new_password, user)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)
        return user


# ── Customer portal logins (created by the mess owner/manager) ───────────

# No look-alike characters (0/o, 1/l/i) — the owner reads these out or sends them on WhatsApp.
_PASSWORD_LETTERS = "abcdefghjkmnpqrstuvwxyz"
_PASSWORD_DIGITS = "23456789"


def generate_password(length=8):
    """Readable random password with at least one letter and one digit."""
    import secrets

    alphabet = _PASSWORD_LETTERS + _PASSWORD_DIGITS
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c in _PASSWORD_DIGITS for c in pwd) and any(c in _PASSWORD_LETTERS for c in pwd):
            return pwd


def _validation_error(field, message):
    from rest_framework.exceptions import ValidationError

    return ValidationError({field: [message]})


def _check_password(password, user):
    from django.core.exceptions import ValidationError as DjangoValidationError

    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        from rest_framework.exceptions import ValidationError

        raise ValidationError({"password": list(exc.messages)}) from None


def _sign_out_everywhere(user):
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)


class CustomerLoginService:
    """Create and manage CUSTOMER-role users for the customer portal.

    The owner sets (or auto-generates) the password and shares it with the customer.
    Passwords are returned to the caller once and never stored in plain text.
    """

    @staticmethod
    @transaction.atomic
    def create_login(*, business_id, username, password=None, name="", email="", phone=""):
        """Returns (user, plain_password)."""
        from django.contrib.auth.validators import UnicodeUsernameValidator
        from django.core.exceptions import ValidationError as DjangoValidationError

        from common.constants import Role

        username = (username or "").strip()
        if not username:
            raise _validation_error("username", "Enter a username (the customer's phone number works well).")
        try:
            UnicodeUsernameValidator()(username)
        except DjangoValidationError:
            raise _validation_error(
                "username", "Use only letters, numbers and @ . + - _ (no spaces)."
            ) from None
        if User.objects.filter(username__iexact=username).exists():
            raise _validation_error("username", "This username is already taken. Try another one.")

        user = User(
            username=username,
            name=name,
            email=email,
            phone=phone,
            role=Role.CUSTOMER,
            business_id=business_id,
            is_active=True,
        )
        if password:
            _check_password(password, user)
        else:
            password = generate_password()
        user.set_password(password)
        user.save()
        return user, password

    @staticmethod
    @transaction.atomic
    def reset_password(user, password=None):
        """Set a new password (given or generated) and sign the customer out everywhere."""
        if password:
            _check_password(password, user)
        else:
            password = generate_password()
        user.set_password(password)
        user.save(update_fields=["password"])
        _sign_out_everywhere(user)
        return password

    @staticmethod
    @transaction.atomic
    def set_active(user, active):
        user.is_active = active
        user.save(update_fields=["is_active"])
        if not active:
            _sign_out_everywhere(user)
        return user
