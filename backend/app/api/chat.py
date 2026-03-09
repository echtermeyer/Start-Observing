from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import csv
from pathlib import Path

from app.storage import json_store as db
from app.api.auth import require_auth

router = APIRouter()


class ChatMessage(BaseModel):
    id: str
    dataset_id: str
    role: str  # user, assistant
    content: str
    created_at: str


class SendMessageRequest(BaseModel):
    dataset_id: str
    message: str


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


def generate_ai_response(message: str, dataset_id: str, user_id: str) -> str:
    """Generate an AI response using Claude based on message content and dataset."""
    from app.services.claude_agent import chat_about_data

    # Get dataset info for context
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        return "I couldn't find the dataset you're asking about."

    # Get schema
    schema_data = db.find_one("schemas", lambda x: x.get("dataset_id") == dataset_id)
    schema = schema_data.get("columns", []) if schema_data else []

    # Get metrics
    metrics_list = db.find_all("metrics", lambda x: x.get("dataset_id") == dataset_id)
    metrics = metrics_list[-1] if metrics_list else {}

    # Get sample data
    sample_data = get_dataset_sample_data(dataset_id)

    # Get chat history
    chat_history = db.find_all("chat_messages", lambda x:
        x.get("dataset_id") == dataset_id and x.get("user_id") == user_id)
    chat_history.sort(key=lambda x: x.get("created_at", ""))

    # Convert to simple format for the agent
    history = [{"role": m.get("role"), "content": m.get("content")} for m in chat_history[-10:]]

    try:
        response = chat_about_data(
            message=message,
            dataset_name=dataset.get("name", "Unknown"),
            schema=schema,
            metrics=metrics,
            sample_data=sample_data,
            history=history
        )
        return response
    except Exception as e:
        # Fallback response if Claude API fails
        return f"I'm having trouble connecting to my analysis service right now. Based on what I know, your dataset '{dataset.get('name')}' has {metrics.get('total_records', 'some')} records. Please try again in a moment."


@router.post("")
def send_message(request: SendMessageRequest, user: dict = Depends(require_auth)):
    """Send a message and get AI response."""
    dataset = db.find_by_id("datasets", request.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check access
    if dataset.get("user_id") != user["id"]:
        team_member = db.find_one("team_members", lambda x:
            x.get("dataset_id") == request.dataset_id and x.get("user_id") == user["id"])
        if not team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Save user message
    user_msg = db.insert("chat_messages", {
        "dataset_id": request.dataset_id,
        "user_id": user["id"],
        "role": "user",
        "content": request.message
    })

    # Generate AI response using Claude
    ai_response = generate_ai_response(request.message, request.dataset_id, user["id"])

    # Save AI message
    ai_msg = db.insert("chat_messages", {
        "dataset_id": request.dataset_id,
        "user_id": user["id"],
        "role": "assistant",
        "content": ai_response
    })

    return {
        "user_message": user_msg,
        "assistant_message": ai_msg
    }


@router.get("/history/{dataset_id}")
def get_chat_history(dataset_id: str, user: dict = Depends(require_auth)):
    """Get chat history for a dataset."""
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check access
    if dataset.get("user_id") != user["id"]:
        team_member = db.find_one("team_members", lambda x:
            x.get("dataset_id") == dataset_id and x.get("user_id") == user["id"])
        if not team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    messages = db.find_all("chat_messages", lambda x:
        x.get("dataset_id") == dataset_id and x.get("user_id") == user["id"])
    messages.sort(key=lambda x: x.get("created_at", ""))

    return {"messages": messages}


@router.delete("/history/{dataset_id}")
def clear_chat_history(dataset_id: str, user: dict = Depends(require_auth)):
    """Clear chat history for a dataset."""
    dataset = db.find_by_id("datasets", dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the owner can clear chat history")

    deleted = db.delete_many("chat_messages", lambda x:
        x.get("dataset_id") == dataset_id and x.get("user_id") == user["id"])

    return {"message": f"Deleted {deleted} messages"}
