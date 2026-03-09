"""
Simple JSON file-based storage for development.
Each collection is stored as a separate JSON file.
"""
import json
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import uuid
import hashlib


DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_file_path(collection: str) -> Path:
    return DATA_DIR / f"{collection}.json"


def _load_collection(collection: str) -> list[dict]:
    _ensure_data_dir()
    file_path = _get_file_path(collection)
    if not file_path.exists():
        return []
    with open(file_path, "r") as f:
        return json.load(f)


def _save_collection(collection: str, data: list[dict]):
    _ensure_data_dir()
    file_path = _get_file_path(collection)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def generate_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


# Generic CRUD operations

def find_all(collection: str, filter_fn: Optional[callable] = None) -> list[dict]:
    data = _load_collection(collection)
    if filter_fn:
        return [item for item in data if filter_fn(item)]
    return data


def find_one(collection: str, filter_fn: callable) -> Optional[dict]:
    data = _load_collection(collection)
    for item in data:
        if filter_fn(item):
            return item
    return None


def find_by_id(collection: str, id: str) -> Optional[dict]:
    return find_one(collection, lambda x: x.get("id") == id)


def insert(collection: str, item: dict) -> dict:
    data = _load_collection(collection)
    if "id" not in item:
        item["id"] = generate_id()
    if "created_at" not in item:
        item["created_at"] = now_iso()
    data.append(item)
    _save_collection(collection, data)
    return item


def update(collection: str, id: str, updates: dict) -> Optional[dict]:
    data = _load_collection(collection)
    for i, item in enumerate(data):
        if item.get("id") == id:
            item.update(updates)
            item["updated_at"] = now_iso()
            data[i] = item
            _save_collection(collection, data)
            return item
    return None


def delete(collection: str, id: str) -> bool:
    data = _load_collection(collection)
    original_len = len(data)
    data = [item for item in data if item.get("id") != id]
    if len(data) < original_len:
        _save_collection(collection, data)
        return True
    return False


def delete_many(collection: str, filter_fn: callable) -> int:
    data = _load_collection(collection)
    original_len = len(data)
    data = [item for item in data if not filter_fn(item)]
    deleted_count = original_len - len(data)
    if deleted_count > 0:
        _save_collection(collection, data)
    return deleted_count


def count(collection: str, filter_fn: Optional[callable] = None) -> int:
    return len(find_all(collection, filter_fn))


# Seed data initialization

def init_default_data():
    """Initialize default data if collections are empty."""
    # Create default user if none exists
    users = find_all("users")
    if not users:
        # Hash the password the same way auth.py does
        password_hash = hashlib.sha256("demo123".encode()).hexdigest()
        insert("users", {
            "id": "user-1",
            "email": "demo@startobserving.ai",
            "name": "Demo User",
            "password_hash": password_hash,
            "created_at": now_iso()
        })

    # Create default settings for demo user
    settings = find_all("settings")
    if not settings:
        insert("settings", {
            "id": "settings-1",
            "user_id": "user-1",
            "email_notifications": True,
            "notification_frequency": "daily",
            "critical_alerts_only": False,
            "created_at": now_iso()
        })

    # Create default dataset if none exists
    datasets = find_all("datasets")
    if not datasets:
        _create_sample_dataset()


def _create_sample_dataset():
    """Create a sample inventory dataset with schema, metrics, and insights."""
    dataset_id = "demo-dataset-1"

    # Create dataset
    insert("datasets", {
        "id": dataset_id,
        "user_id": "user-1",
        "name": "inventory.csv",
        "version_count": 1,
        "latest_row_count": 40
    })

    # Create version
    insert("versions", {
        "id": "demo-version-1",
        "dataset_id": dataset_id,
        "version_number": 1,
        "file_path": "/sample_data/inventory.csv",
        "row_count": 40,
        "uploaded_at": now_iso()
    })

    # Create schema
    insert("schemas", {
        "id": "demo-schema-1",
        "dataset_id": dataset_id,
        "columns": [
            {"name": "sku", "type": "string", "nullable": False, "sample_values": ["SKU-001", "SKU-002", "SKU-003"]},
            {"name": "product_name", "type": "string", "nullable": False, "sample_values": ["Wireless Mouse", "USB-C Cable", "Keyboard"]},
            {"name": "category", "type": "string", "nullable": False, "sample_values": ["Electronics", "Office", "Furniture"]},
            {"name": "quantity", "type": "number", "nullable": False, "sample_values": ["145", "89", "34"]},
            {"name": "price", "type": "number", "nullable": False, "sample_values": ["29.99", "14.99", "89.99"]},
            {"name": "cost", "type": "number", "nullable": False, "sample_values": ["12.50", "4.20", "45.00"]},
            {"name": "last_restocked", "type": "date", "nullable": False, "sample_values": ["2024-01-15", "2024-01-18", "2024-01-10"]},
            {"name": "supplier", "type": "string", "nullable": False, "sample_values": ["TechSupply Co", "OfficePro Inc", "PaperWorld"]}
        ]
    })

    # Create metrics
    insert("metrics", {
        "id": "demo-metrics-1",
        "dataset_id": dataset_id,
        "version_id": "demo-version-1",
        "total_records": 40,
        "null_rate": 0.0,
        "column_count": 8,
        "avg_value": 52.34,
        "anomaly_count": 3
    })

    # Create team member (owner)
    insert("team_members", {
        "id": "demo-team-1",
        "dataset_id": dataset_id,
        "user_id": "user-1",
        "email": "demo@startobserving.ai",
        "name": "Demo User",
        "role": "owner"
    })

    # Create sample insights
    insert("insights", {
        "id": "demo-insight-1",
        "dataset_id": dataset_id,
        "dataset_name": "inventory",
        "user_id": "user-1",
        "severity": "critical",
        "title": "Low Stock Alert",
        "description": "Ergonomic Chair (SKU-008) has only 8 units remaining. At current sales velocity, stock will be depleted in approximately 5 days.",
        "read": False,
        "dismissed": False
    })

    insert("insights", {
        "id": "demo-insight-2",
        "dataset_id": dataset_id,
        "dataset_name": "inventory",
        "user_id": "user-1",
        "severity": "warning",
        "title": "Restock Recommended",
        "description": "6 products in the Electronics category are below 50 units. Consider placing a bulk order with TechSupply Co.",
        "read": False,
        "dismissed": False
    })

    insert("insights", {
        "id": "demo-insight-3",
        "dataset_id": dataset_id,
        "dataset_name": "inventory",
        "user_id": "user-1",
        "severity": "info",
        "title": "Inventory Health",
        "description": "Overall inventory value is $47,832. Office supplies category has the highest turnover rate with 15% weekly movement.",
        "read": False,
        "dismissed": False
    })

    # Create sample alerts
    insert("alerts", {
        "id": "demo-alert-1",
        "dataset_id": dataset_id,
        "dataset_name": "inventory",
        "severity": "critical",
        "type": "threshold",
        "title": "Stock Below Threshold",
        "message": "Filing Cabinet (SKU-021) dropped below minimum threshold of 10 units",
        "acknowledged": False
    })

    insert("alerts", {
        "id": "demo-alert-2",
        "dataset_id": dataset_id,
        "dataset_name": "inventory",
        "severity": "warning",
        "type": "anomaly",
        "title": "Unusual Pattern",
        "message": "Standing Desk restocking frequency is 40% below historical average",
        "acknowledged": False
    })
