from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import csv
import io
from pathlib import Path

from app.storage import json_store as db
from app.api.auth import require_auth

router = APIRouter()

UPLOADS_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"


class ColumnSchema(BaseModel):
    name: str
    type: str  # string, number, date, boolean
    nullable: bool
    sample_values: list[str]


class DatasetVersion(BaseModel):
    id: str
    dataset_id: str
    version_number: Optional[int] = None
    file_path: str
    row_count: int
    uploaded_at: Optional[str] = None
    created_at: Optional[str] = None


class DatasetMetrics(BaseModel):
    total_records: int
    null_rate: float
    column_count: int
    avg_value: Optional[float] = None
    anomaly_count: int


class Dataset(BaseModel):
    id: str
    user_id: str
    name: str
    created_at: str
    updated_at: Optional[str] = None
    version_count: int
    latest_row_count: Optional[int] = None


class DatasetDetail(Dataset):
    schema_info: Optional[list[ColumnSchema]] = None
    latest_version: Optional[DatasetVersion] = None


class TeamMember(BaseModel):
    user_id: str
    email: str
    name: str
    role: str  # owner, editor, viewer
    added_at: str


def infer_column_type(values: list[str]) -> str:
    """Infer column type from sample values."""
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "string"

    # Try number
    try:
        for v in non_empty[:10]:
            float(v.replace(",", ""))
        return "number"
    except ValueError:
        pass

    # Try date patterns
    date_patterns = ["-", "/", "T"]
    if any(p in non_empty[0] for p in date_patterns) and len(non_empty[0]) >= 8:
        return "date"

    # Try boolean
    bool_values = {"true", "false", "yes", "no", "1", "0"}
    if all(v.lower() in bool_values for v in non_empty[:10]):
        return "boolean"

    return "string"


def parse_csv_schema(content: bytes) -> tuple[list[ColumnSchema], int, list[dict]]:
    """Parse CSV and extract schema info."""
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    row_count = len(rows)

    if not rows:
        return [], 0, []

    schema = []
    for col in reader.fieldnames or []:
        values = [row.get(col, "") for row in rows]
        non_null = [v for v in values if v.strip()]
        col_type = infer_column_type(values)
        schema.append(ColumnSchema(
            name=col,
            type=col_type,
            nullable=len(non_null) < len(values),
            sample_values=values[:3]
        ))

    return schema, row_count, rows


def calculate_metrics(rows: list[dict], schema: list[ColumnSchema]) -> DatasetMetrics:
    """Calculate dataset metrics."""
    total_records = len(rows)
    if total_records == 0:
        return DatasetMetrics(
            total_records=0,
            null_rate=0,
            column_count=len(schema),
            anomaly_count=0
        )

    # Calculate null rate
    total_cells = total_records * len(schema)
    null_cells = sum(
        1 for row in rows for col in schema if not row.get(col.name, "").strip()
    )
    null_rate = round((null_cells / total_cells) * 100, 2) if total_cells > 0 else 0

    # Find numeric columns and calculate avg
    avg_value = None
    numeric_cols = [col for col in schema if col.type == "number"]
    if numeric_cols:
        numeric_values = []
        for row in rows:
            for col in numeric_cols:
                try:
                    val = float(row.get(col.name, "0").replace(",", ""))
                    numeric_values.append(val)
                except ValueError:
                    pass
        if numeric_values:
            avg_value = round(sum(numeric_values) / len(numeric_values), 2)

    # Simple anomaly detection (values > 2 std dev from mean)
    anomaly_count = 0
    for col in numeric_cols:
        values = []
        for row in rows:
            try:
                values.append(float(row.get(col.name, "0").replace(",", "")))
            except ValueError:
                pass
        if len(values) > 2:
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            if std_dev > 0:
                anomaly_count += sum(1 for v in values if abs(v - mean) > 2 * std_dev)

    return DatasetMetrics(
        total_records=total_records,
        null_rate=null_rate,
        column_count=len(schema),
        avg_value=avg_value,
        anomaly_count=anomaly_count
    )


def run_ai_analysis_pipeline(
    dataset_id: str,
    dataset_name: str,
    schema: list[dict],
    metrics: dict,
    rows: list[dict],
    user_id: str
):
    """
    Background task: Run the full AI analysis pipeline on a new dataset.

    This generates insights, recommends alerts, and stores the analysis results.
    """
    from app.services.claude_agent import run_pipeline
    from app.api.alerts import create_alert

    try:
        # Run the full pipeline
        results = run_pipeline(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            schema=schema,
            metrics=metrics,
            sample_data=rows,
            row_count=len(rows),
            user_id=user_id
        )

        # Store insights from the analysis
        if results.get("insights"):
            for insight_data in results["insights"]:
                db.insert("insights", {
                    "dataset_id": dataset_id,
                    "dataset_name": dataset_name,
                    "user_id": user_id,
                    "severity": insight_data.get("severity", "info"),
                    "title": insight_data.get("title", "Insight"),
                    "description": insight_data.get("description", ""),
                    "read": False,
                    "dismissed": False
                })

        # Create immediate alerts if any issues found
        if results.get("alerts") and results["alerts"].get("immediate_alerts"):
            for alert_data in results["alerts"]["immediate_alerts"]:
                create_alert(
                    dataset_id=dataset_id,
                    severity=alert_data.get("severity", "warning"),
                    alert_type=alert_data.get("type", "analysis"),
                    title=alert_data.get("title", "Alert"),
                    message=alert_data.get("message", "")
                )

        # Store recommended alert configs
        if results.get("alerts") and results["alerts"].get("recommended_configs"):
            for config in results["alerts"]["recommended_configs"]:
                db.insert("alert_configs", {
                    "dataset_id": dataset_id,
                    "user_id": user_id,
                    "alert_type": config.get("alert_type", "threshold"),
                    "threshold_column": config.get("column"),
                    "threshold_value": config.get("threshold_value"),
                    "condition": config.get("condition"),
                    "severity": config.get("severity", "warning"),
                    "enabled": True,
                    "auto_generated": True
                })

        # Store the full analysis for reference
        db.insert("analysis_results", {
            "dataset_id": dataset_id,
            "user_id": user_id,
            "analysis": results.get("analysis"),
            "data_quality_score": results.get("analysis", {}).get("data_quality_score"),
            "summary": results.get("analysis", {}).get("summary")
        })

    except Exception as e:
        # Log error but don't fail - the upload itself succeeded
        db.insert("analysis_errors", {
            "dataset_id": dataset_id,
            "error": str(e),
            "stage": "pipeline"
        })


@router.get("")
def list_datasets(user: dict = Depends(require_auth)):
    datasets = db.find_all("datasets", lambda x: x.get("user_id") == user["id"])
    # Also include datasets shared with this user
    team_access = db.find_all("team_members", lambda x: x.get("user_id") == user["id"])
    shared_dataset_ids = [t.get("dataset_id") for t in team_access]
    shared_datasets = db.find_all("datasets", lambda x: x.get("id") in shared_dataset_ids)

    all_datasets = datasets + [d for d in shared_datasets if d not in datasets]
    return {"datasets": all_datasets}


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, user: dict = Depends(require_auth)):
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check access
    if dataset.get("user_id") != user["id"]:
        team_member = db.find_one("team_members", lambda x:
            x.get("dataset_id") == dataset_id and x.get("user_id") == user["id"])
        if not team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get latest version
    versions = db.find_all("versions", lambda x: x.get("dataset_id") == dataset_id)
    latest_version = max(versions, key=lambda x: x.get("version_number", 0)) if versions else None

    # Get schema
    schema_data = db.find_one("schemas", lambda x: x.get("dataset_id") == dataset_id)
    schema_info = schema_data.get("columns") if schema_data else None

    return DatasetDetail(
        id=dataset["id"],
        user_id=dataset["user_id"],
        name=dataset["name"],
        created_at=dataset["created_at"],
        updated_at=dataset.get("updated_at"),
        version_count=len(versions),
        latest_row_count=latest_version.get("row_count") if latest_version else None,
        schema_info=schema_info,
        latest_version=DatasetVersion(**latest_version) if latest_version else None
    )


@router.post("")
async def create_dataset(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(require_auth)
):
    """
    Upload a new dataset and trigger AI analysis.

    The upload returns immediately, while AI analysis runs in the background.
    This includes:
    - Generating insights about the data
    - Recommending alert configurations
    - Analyzing data quality
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # Read file content
    content = await file.read()

    # Parse CSV
    schema, row_count, rows = parse_csv_schema(content)
    if not schema:
        raise HTTPException(status_code=400, detail="Could not parse CSV file")

    # Create dataset
    dataset = db.insert("datasets", {
        "user_id": user["id"],
        "name": file.filename,
        "version_count": 1,
        "latest_row_count": row_count
    })

    # Save file
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOADS_DIR / f"{dataset['id']}_v1.csv"
    with open(file_path, "wb") as f:
        f.write(content)

    # Create version
    version = db.insert("versions", {
        "dataset_id": dataset["id"],
        "version_number": 1,
        "file_path": str(file_path),
        "row_count": row_count
    })

    # Save schema
    schema_dicts = [s.model_dump() for s in schema]
    db.insert("schemas", {
        "dataset_id": dataset["id"],
        "columns": schema_dicts
    })

    # Calculate and save metrics
    metrics = calculate_metrics(rows, schema)
    metrics_dict = metrics.model_dump()
    db.insert("metrics", {
        "dataset_id": dataset["id"],
        "version_id": version["id"],
        **metrics_dict
    })

    # Add owner to team
    db.insert("team_members", {
        "dataset_id": dataset["id"],
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": "owner"
    })

    # Trigger AI analysis pipeline in background
    if background_tasks:
        background_tasks.add_task(
            run_ai_analysis_pipeline,
            dataset_id=dataset["id"],
            dataset_name=file.filename,
            schema=schema_dicts,
            metrics=metrics_dict,
            rows=rows,
            user_id=user["id"]
        )

    return {
        "dataset": dataset,
        "version": version,
        "schema": schema,
        "metrics": metrics,
        "message": "Dataset uploaded successfully. AI analysis is running in the background."
    }


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, user: dict = Depends(require_auth)):
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the owner can delete a dataset")

    # Delete related data
    db.delete_many("versions", lambda x: x.get("dataset_id") == dataset_id)
    db.delete_many("schemas", lambda x: x.get("dataset_id") == dataset_id)
    db.delete_many("metrics", lambda x: x.get("dataset_id") == dataset_id)
    db.delete_many("team_members", lambda x: x.get("dataset_id") == dataset_id)
    db.delete_many("insights", lambda x: x.get("dataset_id") == dataset_id)
    db.delete_many("alerts", lambda x: x.get("dataset_id") == dataset_id)
    db.delete_many("chat_messages", lambda x: x.get("dataset_id") == dataset_id)
    db.delete_many("alert_configs", lambda x: x.get("dataset_id") == dataset_id)
    db.delete_many("analysis_results", lambda x: x.get("dataset_id") == dataset_id)
    db.delete("datasets", dataset_id)

    return {"message": "Dataset deleted successfully"}


@router.get("/{dataset_id}/versions")
def list_versions(dataset_id: str, user: dict = Depends(require_auth)):
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    versions = db.find_all("versions", lambda x: x.get("dataset_id") == dataset_id)
    versions.sort(key=lambda x: x.get("version_number", 0), reverse=True)
    return {"versions": versions}


@router.post("/{dataset_id}/versions")
async def upload_version(
    dataset_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(require_auth)
):
    """Upload a new version of a dataset and re-run AI analysis."""
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check access (owner or editor)
    if dataset.get("user_id") != user["id"]:
        team_member = db.find_one("team_members", lambda x:
            x.get("dataset_id") == dataset_id and
            x.get("user_id") == user["id"] and
            x.get("role") in ["owner", "editor"])
        if not team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    content = await file.read()
    schema, row_count, rows = parse_csv_schema(content)

    # Get next version number
    versions = db.find_all("versions", lambda x: x.get("dataset_id") == dataset_id)
    next_version = max((v.get("version_number", 0) for v in versions), default=0) + 1

    # Save file
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOADS_DIR / f"{dataset_id}_v{next_version}.csv"
    with open(file_path, "wb") as f:
        f.write(content)

    # Create version
    version = db.insert("versions", {
        "dataset_id": dataset_id,
        "version_number": next_version,
        "file_path": str(file_path),
        "row_count": row_count
    })

    # Update dataset
    db.update("datasets", dataset_id, {
        "version_count": next_version,
        "latest_row_count": row_count
    })

    # Update schema
    schema_dicts = [s.model_dump() for s in schema]
    existing_schema = db.find_one("schemas", lambda x: x.get("dataset_id") == dataset_id)
    if existing_schema:
        db.update("schemas", existing_schema["id"], {"columns": schema_dicts})
    else:
        db.insert("schemas", {"dataset_id": dataset_id, "columns": schema_dicts})

    # Update metrics
    metrics = calculate_metrics(rows, schema)
    metrics_dict = metrics.model_dump()
    db.insert("metrics", {
        "dataset_id": dataset_id,
        "version_id": version["id"],
        **metrics_dict
    })

    # Re-run AI analysis for new version
    if background_tasks:
        background_tasks.add_task(
            run_ai_analysis_pipeline,
            dataset_id=dataset_id,
            dataset_name=dataset.get("name", file.filename),
            schema=schema_dicts,
            metrics=metrics_dict,
            rows=rows,
            user_id=user["id"]
        )

    return {
        "version": version,
        "schema": schema,
        "metrics": metrics,
        "message": "New version uploaded. AI analysis is running in the background."
    }


@router.get("/{dataset_id}/schema")
def get_schema(dataset_id: str, user: dict = Depends(require_auth)):
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    schema_data = db.find_one("schemas", lambda x: x.get("dataset_id") == dataset_id)
    if not schema_data:
        raise HTTPException(status_code=404, detail="Schema not found")

    return {"schema": schema_data.get("columns", [])}


@router.get("/{dataset_id}/metrics")
def get_metrics(dataset_id: str, user: dict = Depends(require_auth)):
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get latest metrics
    metrics_list = db.find_all("metrics", lambda x: x.get("dataset_id") == dataset_id)
    if not metrics_list:
        raise HTTPException(status_code=404, detail="Metrics not found")

    latest_metrics = metrics_list[-1]  # Most recent

    # Calculate change from previous version if exists
    changes = {}
    if len(metrics_list) > 1:
        prev_metrics = metrics_list[-2]
        if prev_metrics.get("total_records"):
            changes["total_records_change"] = round(
                ((latest_metrics.get("total_records", 0) - prev_metrics.get("total_records", 0))
                 / prev_metrics.get("total_records", 1)) * 100, 1
            )
        if prev_metrics.get("avg_value"):
            changes["avg_value_change"] = round(
                ((latest_metrics.get("avg_value", 0) - prev_metrics.get("avg_value", 0))
                 / prev_metrics.get("avg_value", 1)) * 100, 1
            )
        changes["null_rate_change"] = round(
            latest_metrics.get("null_rate", 0) - prev_metrics.get("null_rate", 0), 2
        )
        changes["anomaly_change"] = (
            latest_metrics.get("anomaly_count", 0) - prev_metrics.get("anomaly_count", 0)
        )

    return {"metrics": latest_metrics, "changes": changes}


@router.get("/{dataset_id}/analysis")
def get_analysis(dataset_id: str, user: dict = Depends(require_auth)):
    """Get the AI analysis results for a dataset."""
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check access
    if dataset.get("user_id") != user["id"]:
        team_member = db.find_one("team_members", lambda x:
            x.get("dataset_id") == dataset_id and x.get("user_id") == user["id"])
        if not team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get latest analysis
    analysis_results = db.find_all("analysis_results", lambda x: x.get("dataset_id") == dataset_id)
    if not analysis_results:
        return {"analysis": None, "message": "No analysis available yet. It may still be processing."}

    latest = analysis_results[-1]
    return {"analysis": latest}


# Team endpoints

@router.get("/{dataset_id}/team")
def list_team(dataset_id: str, user: dict = Depends(require_auth)):
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    team = db.find_all("team_members", lambda x: x.get("dataset_id") == dataset_id)
    return {"team": team}


class AddTeamMemberRequest(BaseModel):
    email: str
    role: str = "viewer"


@router.post("/{dataset_id}/team")
def add_team_member(dataset_id: str, request: AddTeamMemberRequest, user: dict = Depends(require_auth)):
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Only owner can add team members
    if dataset.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the owner can manage team members")

    # Find user by email
    new_user = db.find_one("users", lambda x: x.get("email") == request.email)
    if not new_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already a member
    existing = db.find_one("team_members", lambda x:
        x.get("dataset_id") == dataset_id and x.get("user_id") == new_user["id"])
    if existing:
        raise HTTPException(status_code=400, detail="User is already a team member")

    member = db.insert("team_members", {
        "dataset_id": dataset_id,
        "user_id": new_user["id"],
        "email": new_user["email"],
        "name": new_user["name"],
        "role": request.role
    })

    return {"member": member}


class UpdateTeamMemberRequest(BaseModel):
    role: str


@router.patch("/{dataset_id}/team/{member_user_id}")
def update_team_member(dataset_id: str, member_user_id: str, request: UpdateTeamMemberRequest, user: dict = Depends(require_auth)):
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the owner can manage team members")

    member = db.find_one("team_members", lambda x:
        x.get("dataset_id") == dataset_id and x.get("user_id") == member_user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    if member.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot change owner's role")

    updated = db.update("team_members", member["id"], {"role": request.role})
    return {"member": updated}


@router.delete("/{dataset_id}/team/{member_user_id}")
def remove_team_member(dataset_id: str, member_user_id: str, user: dict = Depends(require_auth)):
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the owner can manage team members")

    member = db.find_one("team_members", lambda x:
        x.get("dataset_id") == dataset_id and x.get("user_id") == member_user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    if member.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the owner")

    db.delete("team_members", member["id"])
    return {"message": "Team member removed"}
