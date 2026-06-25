"""Lightweight API-key auth + shared rate limiter."""
import os
from fastapi import Header, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter — imported by main.py and routes
limiter = Limiter(key_func=get_remote_address)

# Optional API key. If AML_API_KEY env var is unset, auth is skipped
# (keeps local dev frictionless). Set it in production .env.
_API_KEY = os.getenv("AML_API_KEY")


async def require_api_key(x_api_key: str = Header(default=None)):
    if _API_KEY is None:
        return  # auth disabled (dev)
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
