from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any
import csv
from pathlib import Path
from datetime import datetime

from app.storage import json_store as db
from app.api.auth import require_auth

router = APIRouter()


class Visualization(BaseModel):
    id: str
    title: str
    description: str
    spec: dict[str, Any]


class VisualizationResponse(BaseModel):
    dataset_id: str
    generated_at: str
    visualizations: list[Visualization]


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


def create_fallback_visualizations(schema: list[dict], sample_data: list[dict]) -> list[Visualization]:
    """Create basic visualizations when AI generation fails."""
    visualizations = []

    # Find numeric and categorical columns
    numeric_cols = [col["name"] for col in schema if col.get("type") == "number"]
    string_cols = [col["name"] for col in schema if col.get("type") == "string"]

    # Basic bar chart for first string column
    if string_cols and numeric_cols:
        visualizations.append(Visualization(
            id="bar-1",
            title=f"Distribution by {string_cols[0]}",
            description=f"Count of records grouped by {string_cols[0]}",
            spec={
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "data": {"values": sample_data[:100]},
                "mark": {"type": "bar", "cornerRadiusEnd": 4},
                "encoding": {
                    "x": {"field": string_cols[0], "type": "nominal"},
                    "y": {"aggregate": "count", "type": "quantitative"},
                    "color": {"field": string_cols[0], "type": "nominal", "legend": None}
                }
            }
        ))

    # Histogram for first numeric column
    if numeric_cols:
        visualizations.append(Visualization(
            id="hist-1",
            title=f"Distribution of {numeric_cols[0]}",
            description=f"Histogram showing the distribution of {numeric_cols[0]} values",
            spec={
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "data": {"values": sample_data[:100]},
                "mark": "bar",
                "encoding": {
                    "x": {"field": numeric_cols[0], "bin": True, "type": "quantitative"},
                    "y": {"aggregate": "count", "type": "quantitative"}
                }
            }
        ))

    # Scatter plot if we have two numeric columns
    if len(numeric_cols) >= 2:
        visualizations.append(Visualization(
            id="scatter-1",
            title=f"{numeric_cols[0]} vs {numeric_cols[1]}",
            description=f"Scatter plot comparing {numeric_cols[0]} and {numeric_cols[1]}",
            spec={
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "data": {"values": sample_data[:100]},
                "mark": {"type": "point", "filled": True, "opacity": 0.7},
                "encoding": {
                    "x": {"field": numeric_cols[0], "type": "quantitative"},
                    "y": {"field": numeric_cols[1], "type": "quantitative"}
                }
            }
        ))

    return visualizations


@router.get("/{dataset_id}")
def get_visualizations(dataset_id: str, user: dict = Depends(require_auth)) -> VisualizationResponse:
    """
    Generate AI-powered visualizations for a dataset.

    The Claude agent analyzes the data and creates appropriate Vega-Lite specifications
    based on the data types and patterns found.
    """
    from app.services.claude_agent import generate_visualizations as ai_generate_visualizations

    # Verify dataset exists and user has access
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check access
    if dataset.get("user_id") != user["id"]:
        team_member = db.find_one("team_members", lambda x:
            x.get("dataset_id") == dataset_id and x.get("user_id") == user["id"])
        if not team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get schema
    schema_data = db.find_one("schemas", lambda x: x.get("dataset_id") == dataset_id)
    schema = schema_data.get("columns", []) if schema_data else []

    # Get metrics
    metrics_list = db.find_all("metrics", lambda x: x.get("dataset_id") == dataset_id)
    metrics = metrics_list[-1] if metrics_list else {}

    # Get sample data
    sample_data = get_dataset_sample_data(dataset_id)

    # Try to generate AI-powered visualizations
    try:
        ai_visualizations = ai_generate_visualizations(
            dataset_name=dataset.get("name", "Unknown"),
            schema=schema,
            metrics=metrics,
            sample_data=sample_data
        )

        if ai_visualizations:
            visualizations = [
                Visualization(
                    id=viz.get("id", f"viz-{i}"),
                    title=viz.get("title", f"Visualization {i+1}"),
                    description=viz.get("description", ""),
                    spec=viz.get("spec", {})
                )
                for i, viz in enumerate(ai_visualizations)
            ]
        else:
            # AI returned empty, use fallback
            visualizations = create_fallback_visualizations(schema, sample_data)

    except Exception:
        # Fallback to basic visualizations if AI fails
        visualizations = create_fallback_visualizations(schema, sample_data)

    return VisualizationResponse(
        dataset_id=dataset_id,
        generated_at=datetime.now().isoformat(),
        visualizations=visualizations
    )
