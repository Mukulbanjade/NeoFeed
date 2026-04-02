from __future__ import annotations

from fastapi import APIRouter, Depends

from api.middleware import verify_pin
from database import supabase_client as db
from personalization.engine import preference_engine

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/")
async def get_preferences(_auth: bool = Depends(verify_pin)):
    prefs = db.get_preferences()
    return prefs or {"preference_vector": {}, "topic_weights": {}, "source_weights": {}}


@router.post("/rebuild")
async def rebuild_preferences(_auth: bool = Depends(verify_pin)):
    """Manually trigger a full preference rebuild from vote history."""
    prefs = await preference_engine.update_from_votes()
    return {"message": "Preferences rebuilt", "preferences": prefs}
