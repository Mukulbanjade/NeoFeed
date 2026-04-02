"""PIN-based authentication middleware."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Header
from passlib.hash import bcrypt

from config import settings


def verify_pin(x_pin: str = Header(..., alias="X-Pin")) -> bool:
    if not settings.pin_hash:
        return True
    if not bcrypt.verify(x_pin, settings.pin_hash):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return True


def optional_pin(x_pin: str | None = Header(None, alias="X-Pin")) -> bool:
    """For endpoints that work without auth but benefit from it."""
    if not settings.pin_hash:
        return True
    if x_pin and bcrypt.verify(x_pin, settings.pin_hash):
        return True
    if settings.pin_hash and not x_pin:
        raise HTTPException(status_code=401, detail="PIN required")
    raise HTTPException(status_code=401, detail="Invalid PIN")
