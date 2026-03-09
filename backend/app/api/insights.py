from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import csv
import io
from pathlib import Path

from app.storage import json_store as db
from app.api.auth import require_auth

router = APIRouter()


class Insight(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    severity: str  # critical, warning, info
    title: str
    description: str
    created_at: str
    read: bool = False
    dismissed: bool = False


class InsightUpdate(BaseModel):
    read: Optional[bool] = None
    dismissed: Optional[bool] = None


class GenerateInsightsRequest(BaseModel):
    dataset_id: str


def get_dataset_sample_data(dataset_id: str) -> list[dict]:
    """Load sample data from the dataset's CSV file."""
    versions = db.find_all("versions", lambda x: x.get("dataset_id") == dataset_id)
    if not versions:
        return []

    latest_version = max(versions, key=lambda x: x.get("version_number", 0))
    file_path = latest_version.get("file_path")

    if not file_path or not Path(file_path).exists():
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception:
        return []


def generate_insights_for_dataset(dataset_id: str, user_id: str) -> list[dict]:
    """Generate AI-powered insights based on dataset analysis using Claude."""
    from app.services.claude_agent import generate_insights as ai_generate_insights

    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        return []

    # Get schema
    schema_data = db.find_one("schemas", lambda x: x.get("dataset_id") == dataset_id)
    schema = schema_data.get("columns", []) if schema_data else []

    # Get metrics
    metrics_list = db.find_all("metrics", lambda x: x.get("dataset_id") == dataset_id)
    metrics = metrics_list[-1] if metrics_list else {}

    # Get sample data
    sample_data = get_dataset_sample_data(dataset_id)

    # Get previous insights to avoid duplicates
    previous_insights = db.find_all("insights", lambda x:
        x.get("dataset_id") == dataset_id and not x.get("dismissed", False))

    # Generate insights using Claude
    try:
        ai_insights = ai_generate_insights(
            dataset_name=dataset.get("name", "Unknown"),
            schema=schema,
            metrics=metrics,
            sample_data=sample_data,
            previous_insights=previous_insights
        )
    except Exception as e:
        # Fallback if Claude API fails - create a single info insight
        ai_insights = [{
            "severity": "info",
            "title": "Analysis Pending",
            "description": f"Automated analysis is temporarily unavailable. Dataset has {metrics.get('total_records', 0)} records across {len(schema)} columns."
        }]

    # Store insights in database
    generated = []
    for insight_data in ai_insights:
        insight = db.insert("insights", {
            "dataset_id": dataset_id,
            "dataset_name": dataset.get("name", "Unknown"),
            "user_id": user_id,
            "severity": insight_data.get("severity", "info"),
            "title": insight_data.get("title", "Insight"),
            "description": insight_data.get("description", ""),
            "read": False,
            "dismissed": False
        })
        generated.append(insight)

    return generated


@router.get("")
def list_insights(
    severity: Optional[str] = Query(None),
    dataset_id: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    user: dict = Depends(require_auth)
):
    """List all insights for the user."""
    def filter_fn(x):
        if x.get("user_id") != user["id"]:
            return False
        if x.get("dismissed"):
            return False
        if severity and x.get("severity") != severity:
            return False
        if dataset_id and x.get("dataset_id") != dataset_id:
            return False
        if unread_only and x.get("read"):
            return False
        return True

    insights = db.find_all("insights", filter_fn)
    insights.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {"insights": insights}


@router.get("/{insight_id}")
def get_insight(insight_id: str, user: dict = Depends(require_auth)):
    """Get a single insight."""
    insight = db.find_by_id("insights", insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    if insight.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return insight


@router.patch("/{insight_id}")
def update_insight(insight_id: str, update: InsightUpdate, user: dict = Depends(require_auth)):
    """Mark insight as read or dismissed."""
    insight = db.find_by_id("insights", insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    if insight.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    updates = {}
    if update.read is not None:
        updates["read"] = update.read
    if update.dismissed is not None:
        updates["dismissed"] = update.dismissed

    updated = db.update("insights", insight_id, updates)
    return updated


@router.post("/generate")
def generate_insights(request: GenerateInsightsRequest, user: dict = Depends(require_auth)):
    """Trigger AI insight generation for a dataset."""
    dataset = db.find_by_id("datasets", request.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check access
    if dataset.get("user_id") != user["id"]:
        team_member = db.find_one("team_members", lambda x:
            x.get("dataset_id") == request.dataset_id and x.get("user_id") == user["id"])
        if not team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Generate new insights using Claude
    new_insights = generate_insights_for_dataset(request.dataset_id, user["id"])

    return {
        "message": f"Generated {len(new_insights)} new insights",
        "insights": new_insights
    }
