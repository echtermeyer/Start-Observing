from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.storage import json_store as db
from app.api.auth import require_auth

router = APIRouter()


class Settings(BaseModel):
    email_notifications: bool = True
    notification_frequency: str = "daily"  # realtime, daily, weekly
    critical_alerts_only: bool = False


class NotificationSettings(BaseModel):
    email_notifications: bool = True
    notification_frequency: str = "daily"
    critical_alerts_only: bool = False


class DatasetSettings(BaseModel):
    dataset_id: str
    update_frequency: str = "daily"  # realtime, hourly, daily, weekly, manual
    email_alerts: bool = True
    weekly_digest: bool = False


@router.get("")
def get_settings(user: dict = Depends(require_auth)):
    """Get user settings."""
    settings = db.find_one("settings", lambda x: x.get("user_id") == user["id"])
    if not settings:
        # Create default settings
        settings = db.insert("settings", {
            "user_id": user["id"],
            "email_notifications": True,
            "notification_frequency": "daily",
            "critical_alerts_only": False
        })
    return settings


@router.put("")
def update_settings(new_settings: Settings, user: dict = Depends(require_auth)):
    """Update user settings."""
    settings = db.find_one("settings", lambda x: x.get("user_id") == user["id"])
    if settings:
        updated = db.update("settings", settings["id"], new_settings.model_dump())
    else:
        updated = db.insert("settings", {
            "user_id": user["id"],
            **new_settings.model_dump()
        })
    return updated


@router.get("/notifications")
def get_notification_settings(user: dict = Depends(require_auth)):
    """Get notification preferences."""
    settings = db.find_one("settings", lambda x: x.get("user_id") == user["id"])
    if not settings:
        return NotificationSettings()
    return NotificationSettings(
        email_notifications=settings.get("email_notifications", True),
        notification_frequency=settings.get("notification_frequency", "daily"),
        critical_alerts_only=settings.get("critical_alerts_only", False)
    )


@router.put("/notifications")
def update_notification_settings(notifications: NotificationSettings, user: dict = Depends(require_auth)):
    """Update notification preferences."""
    settings = db.find_one("settings", lambda x: x.get("user_id") == user["id"])
    updates = notifications.model_dump()

    if settings:
        updated = db.update("settings", settings["id"], updates)
    else:
        updated = db.insert("settings", {
            "user_id": user["id"],
            **updates
        })
    return updated


@router.get("/datasets/{dataset_id}")
def get_dataset_settings(dataset_id: str, user: dict = Depends(require_auth)):
    """Get settings for a specific dataset."""
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    settings = db.find_one("dataset_settings", lambda x:
        x.get("dataset_id") == dataset_id and x.get("user_id") == user["id"])

    if not settings:
        return DatasetSettings(dataset_id=dataset_id)

    return DatasetSettings(
        dataset_id=dataset_id,
        update_frequency=settings.get("update_frequency", "daily"),
        email_alerts=settings.get("email_alerts", True),
        weekly_digest=settings.get("weekly_digest", False)
    )


@router.put("/datasets/{dataset_id}")
def update_dataset_settings(dataset_id: str, new_settings: DatasetSettings, user: dict = Depends(require_auth)):
    """Update settings for a specific dataset."""
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    existing = db.find_one("dataset_settings", lambda x:
        x.get("dataset_id") == dataset_id and x.get("user_id") == user["id"])

    data = new_settings.model_dump()
    data["user_id"] = user["id"]

    if existing:
        updated = db.update("dataset_settings", existing["id"], data)
    else:
        updated = db.insert("dataset_settings", data)

    return updated
