"""Savings goals.

Goals are tracked separately from transactions: adding money to a goal records that
it was set aside, it does not change income, expenses or the balance.
"""
from datetime import date, datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response, status

from app.database import get_db
from app.deps import CurrentUser, parse_object_id
from app.schemas import ContributionIn, GoalIn, GoalOut
from app.serializers import to_utc_datetime

router = APIRouter(prefix="/api/goals", tags=["goals"])


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _months_between(start: date, end: date) -> int:
    """Calendar months from start's month to end's month, counting the current one (min 1 if end is ahead)."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    return max(months, 0) + (1 if end >= start else 0)


def goal_out(doc: dict, today: date | None = None) -> dict:
    today = today or _today()
    target = doc["target_amount"]
    saved = round(sum(c["amount"] for c in doc.get("contributions", [])), 2)
    remaining = round(max(target - saved, 0), 2)
    created = doc["created_at"].date()
    target_date = doc["target_date"].date() if doc.get("target_date") else None

    months_left = monthly_needed = None
    if saved >= target:
        goal_status = "completed"
    elif target_date is None:
        goal_status = "no_deadline"
    else:
        months_left = _months_between(today, target_date) if target_date >= today else 0
        monthly_needed = round(remaining / max(months_left, 1), 2)
        # On track = saved at least as much as an even pace from start to target date would have.
        total_days = (target_date - created).days
        elapsed = min(max((today - created).days, 0), total_days) if total_days > 0 else 1
        expected = target * (elapsed / total_days) if total_days > 0 else target
        goal_status = "on_track" if saved >= expected - 0.005 else "behind"

    contributions = sorted(doc.get("contributions", []), key=lambda c: (c["date"], c["_id"]), reverse=True)
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "target_amount": target,
        "target_date": target_date,
        "created_at": created,
        "saved": saved,
        "remaining": remaining,
        "percent": round(saved / target * 100, 1) if target else 0.0,
        "months_left": months_left,
        "monthly_needed": monthly_needed,
        "status": goal_status,
        "contributions": [
            {"id": str(c["_id"]), "amount": c["amount"], "date": c["date"].date(), "note": c.get("note", "")}
            for c in contributions
        ],
    }


async def _get_goal(goal_id: str, user: dict) -> dict:
    doc = await get_db().goals.find_one({"_id": parse_object_id(goal_id, "Goal"), "user_id": user["_id"]})
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    return doc


@router.get("", response_model=list[GoalOut])
async def list_goals(user: CurrentUser):
    cursor = get_db().goals.find({"user_id": user["_id"]}).sort("created_at", 1)
    goals = [goal_out(doc) async for doc in cursor]
    # Active goals first (closest deadline first), completed ones last.
    goals.sort(key=lambda g: (g["status"] == "completed", g["target_date"] or date.max))
    return goals


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(data: GoalIn, user: CurrentUser):
    doc = {
        "user_id": user["_id"],
        "name": data.name,
        "target_amount": data.target_amount,
        "target_date": to_utc_datetime(data.target_date) if data.target_date else None,
        "contributions": [],
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().goals.insert_one(doc)
    doc["_id"] = result.inserted_id
    return goal_out(doc)


@router.put("/{goal_id}", response_model=GoalOut)
async def update_goal(goal_id: str, data: GoalIn, user: CurrentUser):
    doc = await _get_goal(goal_id, user)
    changes = {
        "name": data.name,
        "target_amount": data.target_amount,
        "target_date": to_utc_datetime(data.target_date) if data.target_date else None,
    }
    await get_db().goals.update_one({"_id": doc["_id"]}, {"$set": changes})
    return goal_out({**doc, **changes})


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: str, user: CurrentUser):
    doc = await _get_goal(goal_id, user)
    await get_db().goals.delete_one({"_id": doc["_id"]})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{goal_id}/contributions", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def add_contribution(goal_id: str, data: ContributionIn, user: CurrentUser):
    doc = await _get_goal(goal_id, user)
    if data.amount == 0:
        raise HTTPException(422, "Amount can't be zero")
    saved = sum(c["amount"] for c in doc["contributions"])
    if saved + data.amount < -0.005:
        raise HTTPException(422, f"You can't withdraw more than the {saved:.2f} saved in this goal")
    contribution = {"_id": ObjectId(), "amount": data.amount, "date": to_utc_datetime(data.date), "note": data.note}
    updated = await get_db().goals.find_one_and_update(
        {"_id": doc["_id"]}, {"$push": {"contributions": contribution}}, return_document=True
    )
    return goal_out(updated)


@router.delete("/{goal_id}/contributions/{contribution_id}", response_model=GoalOut)
async def remove_contribution(goal_id: str, contribution_id: str, user: CurrentUser):
    doc = await _get_goal(goal_id, user)
    cid = parse_object_id(contribution_id, "Contribution")
    remaining = [c for c in doc["contributions"] if c["_id"] != cid]
    if len(remaining) == len(doc["contributions"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contribution not found")
    if sum(c["amount"] for c in remaining) < -0.005:
        raise HTTPException(422, "Removing this would leave the goal with a negative balance; remove the withdrawal first")
    updated = await get_db().goals.find_one_and_update(
        {"_id": doc["_id"]}, {"$pull": {"contributions": {"_id": cid}}}, return_document=True
    )
    return goal_out(updated)
