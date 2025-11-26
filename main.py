from fastapi import Header, HTTPException, Depends
import os

API_KEY = os.environ.get("BACKEND_API_KEY")


async def verify_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    """
    Accept API key either in:
    - X-API-KEY: <key>
    - Authorization: Bearer <key>
    - Authorization: <key>
    """
    candidate = None

    if x_api_key:
        candidate = x_api_key
    elif authorization:
        # Handle "Bearer <key>" or just "<key>"
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            candidate = parts[1]
        else:
            candidate = authorization

    if not candidate or not API_KEY or candidate != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
