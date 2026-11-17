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
