import os
import requests
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List

TODOIST_TOKEN = os.getenv("TODOIST_TOKEN")
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY")

if not TODOIST_TOKEN:
    raise RuntimeError("TODOIST_TOKEN is not set")

TODOIST_BASE_URL = "https://api.todoist.com/rest/v2"

app = FastAPI(title="Nick Todoist Backend")

class UpdateTask(BaseModel):
    content: Optional[str] = None
    priority: Optional[int] = None
    labels: Optional[List[str]] = None
    due_date: Optional[str] = None

def require_api_key(x_api_key: str = Header(None)):
    if BACKEND_API_KEY and x_api_key != BACKEND_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

def todoist_headers():
    return {
        "Authorization": f"Bearer {TODOIST_TOKEN}",
        "Content-Type": "application/json",
    }

@app.get("/tasks")
def get_tasks(filter: Optional[str] = None, x_api_key: str = Header(None)):
    require_api_key(x_api_key)
    params = {"filter": filter} if filter else {}
    resp = requests.get(f"{TODOIST_BASE_URL}/tasks", headers=todoist_headers(), params=params)
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()

@app.patch("/tasks/{task_id}")
def update_task(task_id: str, body: UpdateTask, x_api_key: str = Header(None)):
    require_api_key(x_api_key)
    payload = {k: v for k, v in body.dict().items() if v is not None}
    resp = requests.post(f"{TODOIST_BASE_URL}/tasks/{task_id}", headers=todoist_headers(), json=payload)
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)
    return {"status": "ok"}
