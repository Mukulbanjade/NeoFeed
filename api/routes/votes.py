from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.middleware import verify_pin
from database import supabase_client as db
from database.models import Vote, VoteType
from personalization.engine import preference_engine

router = APIRouter(prefix="/votes", tags=["votes"])


class VoteRequest(BaseModel):
    article_id: str | None = None
    cluster_id: str | None = None
    vote: VoteType


@router.post("/")
async def cast_vote(req: VoteRequest, _auth: bool = Depends(verify_pin)):
    if not req.article_id and not req.cluster_id:
        return {"error": "Must provide article_id or cluster_id"}

    vote = Vote(
        article_id=req.article_id,
        cluster_id=req.cluster_id,
        vote=req.vote,
    )
    result = db.insert_vote(vote)

    # Trigger async preference update
    await preference_engine.update_from_votes()

    return {"vote": result, "message": "Vote recorded and preferences updated"}


@router.get("/")
async def list_votes(
    limit: int = 100,
    _auth: bool = Depends(verify_pin),
):
    votes = db.get_votes(limit=limit)
    return {"votes": votes, "count": len(votes)}
