"""PIN-based authentication middleware."""

from __future__ import annotations

import logging

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, Header

from config import settings

_logger = logging.getLogger("neofeed.auth")


def _is_bcrypt_hash(value: str) -> bool:
    return value.startswith(("$2b$", "$2a$", "$2y$")) and len(value) >= 59


def _check_pin(pin: str, pin_hash: str) -> bool:
    # #region agent log
    if not _is_bcrypt_hash(pin_hash):
        _logger.warning(
            "PIN_HASH is not a valid bcrypt hash (len=%d). "
            "Falling back to plain-text comparison. "
            "Run POST /auth/setup to generate a proper hash.",
            len(pin_hash),
        )
        return pin == pin_hash
    try:
        result = _bcrypt.checkpw(pin.encode(), pin_hash.encode())
        _logger.info(f"checkpw ok, result={result}, hash_len={len(pin_hash)}")
        return result
    except Exception as exc:
        _logger.error(f"checkpw failed: {type(exc).__name__}: {exc}")
        return pin == pin_hash
    # #endregion


def verify_pin(x_pin: str = Header(..., alias="X-Pin")) -> bool:
    if not settings.pin_hash:
        return True
    if not _check_pin(x_pin, settings.pin_hash):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return True


def optional_pin(x_pin: str | None = Header(None, alias="X-Pin")) -> bool:
    """For endpoints that work without auth but benefit from it."""
    if not settings.pin_hash:
        return True
    if x_pin and _check_pin(x_pin, settings.pin_hash):
        return True
    if settings.pin_hash and not x_pin:
        raise HTTPException(status_code=401, detail="PIN required")
    raise HTTPException(status_code=401, detail="Invalid PIN")
