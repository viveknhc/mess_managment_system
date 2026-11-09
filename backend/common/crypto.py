"""Encryption for secrets stored in the database (e.g. a business's Razorpay key secret).

The key comes from FIELD_ENCRYPTION_KEY, or is derived from SECRET_KEY when that is unset.
Changing either makes stored secrets unreadable; owners then re-enter them.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    source = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(source.encode("utf-8")).digest())
    return Fernet(key)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii") if value else ""


def decrypt(token: str) -> str:
    """Plain text, or "" if empty or unreadable (key changed)."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return ""
