"""PIN-based authentication middleware."""

from __future__ import annotations

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, Header

from config import settings


def _check_pin(pin: str, pin_hash: str) -> bool:
    return _bcrypt.checkpw(pin.encode(), pin_hash.encode())


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
