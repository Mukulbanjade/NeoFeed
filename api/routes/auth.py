from __future__ import annotations

from fastapi import APIRouter, HTTPException
from passlib.hash import bcrypt
from pydantic import BaseModel

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
    if bcrypt.verify(req.pin, settings.pin_hash):
        return {"authenticated": True}
    raise HTTPException(status_code=401, detail="Invalid PIN")


@router.post("/setup")
async def setup_pin(req: PinSetup):
    """Set or change the PIN. Requires current PIN if one is already set."""
    if settings.pin_hash:
        if not req.current_pin or not bcrypt.verify(req.current_pin, settings.pin_hash):
            raise HTTPException(status_code=401, detail="Current PIN is incorrect")

    new_hash = bcrypt.hash(req.pin)
    return {
        "pin_hash": new_hash,
        "message": "Add this hash to your .env as PIN_HASH",
    }
