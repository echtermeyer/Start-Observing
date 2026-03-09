from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import csv
from pathlib import Path

from app.storage import json_store as db
from app.api.auth import require_auth

router = APIRouter()


class Alert(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    severity: str  # critical, warning, info
    type: str  # threshold, anomaly, schedule, etc.
    title: str
    message: str
    created_at: str
    acknowledged: bool = False


class AlertConfig(BaseModel):
    dataset_id: str
    alert_type: str
    threshold_column: Optional[str] = None
    threshold_value: Optional[float] = None
    enabled: bool = True


class AcknowledgeRequest(BaseModel):
    acknowledged: bool


class AnalyzeAlertsRequest(BaseModel):
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


@router.get("")
def list_alerts(
    dataset_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    user: dict = Depends(require_auth)
):
    """List all alerts for the user."""
    # Get user's datasets
    user_datasets = db.find_all("datasets", lambda x: x.get("user_id") == user["id"])
    team_access = db.find_all("team_members", lambda x: x.get("user_id") == user["id"])
    accessible_dataset_ids = [d["id"] for d in user_datasets] + [t.get("dataset_id") for t in team_access]

    def filter_fn(x):
        if x.get("dataset_id") not in accessible_dataset_ids:
            return False
        if dataset_id and x.get("dataset_id") != dataset_id:
            return False
        if severity and x.get("severity") != severity:
            return False
        if acknowledged is not None and x.get("acknowledged") != acknowledged:
            return False
        return True

    alerts = db.find_all("alerts", filter_fn)
    alerts.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {"alerts": alerts}


@router.get("/{alert_id}")
def get_alert(alert_id: str, user: dict = Depends(require_auth)):
    """Get a single alert."""
    alert = db.find_by_id("alerts", alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check access via dataset
    dataset = db.find_by_id("datasets", alert.get("dataset_id"))
    if dataset and dataset.get("user_id") != user["id"]:
        team_member = db.find_one("team_members", lambda x:
            x.get("dataset_id") == alert.get("dataset_id") and x.get("user_id") == user["id"])
        if not team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    return alert


@router.patch("/{alert_id}")
def acknowledge_alert(alert_id: str, request: AcknowledgeRequest, user: dict = Depends(require_auth)):
    """Acknowledge or dismiss an alert."""
    alert = db.find_by_id("alerts", alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    updated = db.update("alerts", alert_id, {"acknowledged": request.acknowledged})
    return updated


@router.post("/configure")
def configure_alert(config: AlertConfig, user: dict = Depends(require_auth)):
    """Configure alert thresholds for a dataset."""
    dataset = db.find_by_id("datasets", config.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check ownership
    if dataset.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the owner can configure alerts")

    # Check if config exists
    existing = db.find_one("alert_configs", lambda x:
        x.get("dataset_id") == config.dataset_id and x.get("alert_type") == config.alert_type)

    if existing:
        updated = db.update("alert_configs", existing["id"], config.model_dump())
        return {"config": updated, "message": "Alert configuration updated"}
    else:
        new_config = db.insert("alert_configs", {
            "user_id": user["id"],
            **config.model_dump()
        })
        return {"config": new_config, "message": "Alert configuration created"}


@router.get("/configs/{dataset_id}")
def get_alert_configs(dataset_id: str, user: dict = Depends(require_auth)):
    """Get alert configurations for a dataset."""
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    configs = db.find_all("alert_configs", lambda x: x.get("dataset_id") == dataset_id)
    return {"configs": configs}


@router.post("/analyze")
def analyze_and_create_alerts(request: AnalyzeAlertsRequest, user: dict = Depends(require_auth)):
    """
    Use AI to analyze dataset and create appropriate alerts.

    This endpoint:
    1. Analyzes the current data for issues
    2. Creates immediate alerts for any problems found
    3. Recommends alert configurations for ongoing monitoring
    """
    from app.services.claude_agent import analyze_for_alerts

    dataset = db.find_by_id("datasets", request.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check access
    if dataset.get("user_id") != user["id"]:
        team_member = db.find_one("team_members", lambda x:
            x.get("dataset_id") == request.dataset_id and x.get("user_id") == user["id"])
        if not team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get schema
    schema_data = db.find_one("schemas", lambda x: x.get("dataset_id") == request.dataset_id)
    schema = schema_data.get("columns", []) if schema_data else []

    # Get metrics
    metrics_list = db.find_all("metrics", lambda x: x.get("dataset_id") == request.dataset_id)
    metrics = metrics_list[-1] if metrics_list else {}

    # Get sample data
    sample_data = get_dataset_sample_data(request.dataset_id)

    # Get existing alerts to avoid duplicates
    existing_alerts = db.find_all("alerts", lambda x:
        x.get("dataset_id") == request.dataset_id and not x.get("acknowledged", False))

    try:
        # Run AI analysis
        analysis = analyze_for_alerts(
            dataset_name=dataset.get("name", "Unknown"),
            schema=schema,
            metrics=metrics,
            sample_data=sample_data,
            existing_alerts=existing_alerts
        )

        created_alerts = []
        created_configs = []

        # Create immediate alerts
        if analysis.get("immediate_alerts"):
            for alert_data in analysis["immediate_alerts"]:
                alert = create_alert(
                    dataset_id=request.dataset_id,
                    severity=alert_data.get("severity", "warning"),
                    alert_type=alert_data.get("type", "analysis"),
                    title=alert_data.get("title", "Alert"),
                    message=alert_data.get("message", "")
                )
                if alert:
                    created_alerts.append(alert)

        # Create recommended configurations
        if analysis.get("recommended_configs"):
            for config_data in analysis["recommended_configs"]:
                existing_config = db.find_one("alert_configs", lambda x:
                    x.get("dataset_id") == request.dataset_id and
                    x.get("alert_type") == config_data.get("alert_type") and
                    x.get("threshold_column") == config_data.get("column"))

                if not existing_config:
                    new_config = db.insert("alert_configs", {
                        "dataset_id": request.dataset_id,
                        "user_id": user["id"],
                        "alert_type": config_data.get("alert_type", "threshold"),
                        "threshold_column": config_data.get("column"),
                        "threshold_value": config_data.get("threshold_value"),
                        "condition": config_data.get("condition"),
                        "severity": config_data.get("severity", "warning"),
                        "enabled": True,
                        "rationale": config_data.get("rationale")
                    })
                    created_configs.append(new_config)

        return {
            "message": "Alert analysis completed",
            "monitoring_summary": analysis.get("monitoring_summary", ""),
            "alerts_created": len(created_alerts),
            "configs_created": len(created_configs),
            "alerts": created_alerts,
            "configs": created_configs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert analysis failed: {str(e)}")


@router.delete("/configs/{config_id}")
def delete_alert_config(config_id: str, user: dict = Depends(require_auth)):
    """Delete an alert configuration."""
    config = db.find_by_id("alert_configs", config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Alert configuration not found")

    dataset = db.find_by_id("datasets", config.get("dataset_id"))
    if dataset and dataset.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the owner can delete alert configurations")

    db.delete("alert_configs", config_id)
    return {"message": "Alert configuration deleted"}


def create_alert(dataset_id: str, severity: str, alert_type: str, title: str, message: str):
    """Helper function to create alerts (called by other services)."""
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        return None

    alert = db.insert("alerts", {
        "dataset_id": dataset_id,
        "dataset_name": dataset.get("name", "Unknown"),
        "severity": severity,
        "type": alert_type,
        "title": title,
        "message": message,
        "acknowledged": False
    })
    return alert


def check_thresholds_for_dataset(dataset_id: str, rows: list[dict]):
    """
    Check configured thresholds against current data and create alerts.

    This is called when new data is uploaded to check existing alert configs.
    """
    configs = db.find_all("alert_configs", lambda x:
        x.get("dataset_id") == dataset_id and x.get("enabled", True))

    for config in configs:
        if config.get("alert_type") == "threshold" and config.get("threshold_column"):
            column = config["threshold_column"]
            threshold = config.get("threshold_value")

            if threshold is None:
                continue

            # Check values
            for row in rows:
                try:
                    value = float(row.get(column, "0").replace(",", ""))
                    if value < threshold:
                        create_alert(
                            dataset_id=dataset_id,
                            severity=config.get("severity", "warning"),
                            alert_type="threshold",
                            title=f"Threshold Alert: {column}",
                            message=f"Value {value} is below threshold {threshold} in column {column}"
                        )
                        break  # Only one alert per column per upload
                except ValueError:
                    pass
