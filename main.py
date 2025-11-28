import os
from typing import Optional, List, Literal, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Depends, Header, Query

# --- Environment configuration ---

TODOIST_TOKEN = os.environ.get("TODOIST_TOKEN")
BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY")

if not TODOIST_TOKEN:
    raise RuntimeError("TODOIST_TOKEN environment variable is not set")

if not BACKEND_API_KEY:
    raise RuntimeError("BACKEND_API_KEY environment variable is not set")


# --- FastAPI application ---

app = FastAPI(
    title="Nick Todoist Backend",
    version="1.0.0",
    description="Backend API for Nick's Personal OS integrating Todoist.",
)


# --- API key verification that works with GPT Actions ---

async def verify_api_key(
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
):
    """
    Accept API key either in:
    - X-API-KEY: <key>
    - Authorization: Bearer <key>
    - Authorization: <key>
    """
    candidate: Optional[str] = None

    if x_api_key:
        candidate = x_api_key
    elif authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            candidate = parts[1]
        else:
            candidate = authorization

    if not candidate or candidate != BACKEND_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# --- Todoist helpers ---

TODOIST_BASE_URL = "https://api.todoist.com/rest/v2"


async def fetch_todoist_tasks(filter_value: Optional[str]) -> List[Dict[str, Any]]:
    """
    Fetch tasks from Todoist. If filter_value is provided and not 'all',
    we forward it to Todoist's 'filter' query parameter.
    """
    headers = {
        "Authorization": f"Bearer {TODOIST_TOKEN}",
        "Content-Type": "application/json",
    }

    params: Dict[str, Any] = {}
    if filter_value and filter_value != "all":
        # Todoist supports natural language filters like "today", "overdue", etc.
        params["filter"] = filter_value

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{TODOIST_BASE_URL}/tasks", headers=headers, params=params)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Todoist API error fetching tasks: {resp.text}",
        )

    return resp.json()


async def update_todoist_task(
    task_id: str,
    content: Optional[str] = None,
    due: Optional[str] = None,
    completed: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Update a Todoist task. Uses /tasks/{id} for content/due,
    and /tasks/{id}/close or /tasks/{id}/reopen for completion.
    """
    headers = {
        "Authorization": f"Bearer {TODOIST_TOKEN}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {}

    if content is not None:
        payload["content"] = content

    if due is not None:
        # Todoist expects due_string or structured due; we use due_string for simplicity.
        payload["due_string"] = due

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Update basic fields first, if any
        if payload:
            resp = await client.post(
                f"{TODOIST_BASE_URL}/tasks/{task_id}",
                headers=headers,
                json=payload,
            )
            if resp.status_code not in (200, 204):
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Todoist API error updating task: {resp.text}",
                )

        # Handle completion changes
        if completed is True:
            close_resp = await client.post(
                f"{TODOIST_BASE_URL}/tasks/{task_id}/close", headers=headers
            )
            if close_resp.status_code not in (200, 204):
                raise HTTPException(
                    status_code=close_resp.status_code,
                    detail=f"Todoist API error closing task: {close_resp.text}",
                )
        elif completed is False:
            reopen_resp = await client.post(
                f"{TODOIST_BASE_URL}/tasks/{task_id}/reopen", headers=headers
            )
            if reopen_resp.status_code not in (200, 204):
                raise HTTPException(
                    status_code=reopen_resp.status_code,
                    detail=f"Todoist API error reopening task: {reopen_resp.text}",
                )

        # Finally fetch and return the updated task
        get_resp = await client.get(
            f"{TODOIST_BASE_URL}/tasks/{task_id}",
            headers=headers,
        )

    if get_resp.status_code != 200:
        raise HTTPException(
            status_code=get_resp.status_code,
            detail=f"Todoist API error fetching updated task: {get_resp.text}",
        )

    return get_resp.json()


# --- Routes matching your GPT OpenAPI spec ---


@app.get(
    "/tasks",
    dependencies=[Depends(verify_api_key)],
)
async def get_tasks(
    filter: Optional[Literal["today", "overdue", "upcoming", "all"]] = Query(
        default=None,
        description="Optional filter for tasks: today, overdue, upcoming, or all.",
    ),
):
    """
    Get tasks from Todoist, optionally filtered.
    """
    tasks = await fetch_todoist_tasks(filter)
    return tasks


@app.patch(
    "/tasks/{task_id}",
    dependencies=[Depends(verify_api_key)],
)
async def update_task(task_id: str, body: Dict[str, Any]):
    """
    Update a specific Todoist task's content, due date, or completion state.
    """
    content = body.get("content")
    # Support both 'due' and 'due_string' in the incoming body
    due = body.get("due") or body.get("due_string")
    completed = body.get("completed")

    updated = await update_todoist_task(
        task_id=task_id,
        content=content,
        due=due,
        completed=completed,
    )
    return updated
