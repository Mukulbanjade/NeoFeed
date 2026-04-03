"""PIN-based authentication middleware."""

from __future__ import annotations

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, Header

from config import settings


def _check_pin(pin: str, pin_hash: str) -> bool:
    # #region agent log
    import logging as _log
    _dbg = _log.getLogger("neofeed.auth")
    try:
        result = _bcrypt.checkpw(pin.encode(), pin_hash.encode())
        _dbg.info(f"checkpw ok, result={result}, hash_len={len(pin_hash)}, prefix={pin_hash[:7]}")
        return result
    except Exception as exc:
        _dbg.error(f"checkpw CRASHED: {type(exc).__name__}: {exc}  hash_len={len(pin_hash)} prefix={pin_hash[:10]!r}")
        raise
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
