from __future__ import annotations

import bcrypt as _bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.middleware import _check_pin
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class PinRequest(BaseModel):
    pin: str


class PinSetup(BaseModel):
    pin: str
    current_pin: str = ""


@router.post("/verify")
async def verify_pin(req: PinRequest):
    if not settings.pin_hash:
        return {"authenticated": True, "message": "No PIN configured"}
    if _check_pin(req.pin, settings.pin_hash):
        return {"authenticated": True}
    raise HTTPException(status_code=401, detail="Invalid PIN")


@router.post("/setup")
async def setup_pin(req: PinSetup):
    """Set or change the PIN. Requires current PIN if one is already set."""
    if settings.pin_hash:
        if not req.current_pin or not _check_pin(req.current_pin, settings.pin_hash):
            raise HTTPException(status_code=401, detail="Current PIN is incorrect")

    new_hash = _bcrypt.hashpw(req.pin.encode(), _bcrypt.gensalt()).decode()
    return {
        "pin_hash": new_hash,
        "message": "Add this hash to your .env as PIN_HASH",
    }
