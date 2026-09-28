import os
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

# Configuration: Points to VPS backend worker & SQLite database
VPS_BACKEND_URL = os.getenv("VPS_BACKEND_URL", "https://glasgow-bacterial-volunteer-doing.trycloudflare.com").rstrip("/")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "yt_sec_794ae71a4f71a66b5dd66774")

# Disable automatic docs and openapi for security & stealth
app = FastAPI(
    title="YouTube API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def path_normalization_middleware(request: Request, call_next):
    """
    Normalizes paths if Vercel passes rewritten file prefixes like /api/index.py
    """
    path = request.scope.get("path", "")
    for prefix in ["/api/index.py", "/api/main.py", "/index.py", "/main.py"]:
        if path.startswith(prefix):
            new_path = path[len(prefix):]
            if not new_path.startswith("/"):
                new_path = "/" + new_path
            request.scope["path"] = new_path
            break
    return await call_next(request)


def get_vercel_base_url(request: Request) -> str:
    """Detects public Vercel domain e.g. https://your-app.vercel.app"""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:3000"
    proto = request.headers.get("x-forwarded-proto", "https")
    if not host.startswith("http"):
        return f"{proto}://{host}"
    return host


# Root endpoint returns direct Unauthorized access
@app.get("/")
@app.get("/api")
@app.get("/api/")
def root():
    raise HTTPException(status_code=401, detail="Unauthorized access")


async def execute_generate_link(
    request: Request,
    url: str,
    key: str,
    type: str = "video",
    quality: Optional[str] = "best",
    expires_in: int = 3600
):
    vercel_domain = get_vercel_base_url(request)
    target_url = f"{VPS_BACKEND_URL}/generate-link"
    
    params = {
        "url": url,
        "key": key,
        "type": type,
        "quality": quality or "best",
        "expires_in": expires_in,
        "domain": vercel_domain,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.get(target_url, params=params)
            data = resp.json()
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=data.get("detail", str(data)))
            return data
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect to VPS Backend: {str(e)}")


@app.get("/generate-link")
@app.get("/api/generate-link")
async def generate_link(
    request: Request,
    url: str = Query(..., description="YouTube Video or Shorts URL"),
    key: str = Query(..., description="Your Admin API Key"),
    type: str = Query("video", pattern="^(video|audio)$"),
    quality: Optional[str] = Query("best"),
    expires_in: int = Query(3600, ge=60, le=86400)
):
    return await execute_generate_link(request, url, key, type, quality, expires_in)


@app.get("/d/{token}")
@app.get("/api/d/{token}")
async def download_temp_link(
    request: Request,
    token: str
):
    """
    Public Vercel download endpoint (No API key required).
    Redirects (HTTP 302) to the VPS stream to initiate immediate file download
    without hitting Vercel's 4.5MB payload limit.
    """
    redirect_target = f"{VPS_BACKEND_URL}/d/{token}"
    return RedirectResponse(url=redirect_target, status_code=302)


async def execute_get_info(url: str, key: str):
    target_url = f"{VPS_BACKEND_URL}/info"
    params = {"url": url, "key": key}
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.get(target_url, params=params)
            data = resp.json()
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=data.get("detail", str(data)))
            return data
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect to VPS Backend: {str(e)}")


@app.get("/info")
@app.get("/api/info")
async def get_info(
    url: str = Query(..., description="YouTube Video URL"),
    key: str = Query(..., description="Your Admin API Key")
):
    return await execute_get_info(url, key)


async def execute_db_stats(key: str):
    target_url = f"{VPS_BACKEND_URL}/db/stats"
    params = {"key": key}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(target_url, params=params)
            data = resp.json()
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=data.get("detail", str(data)))
            return data
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect to VPS Backend: {str(e)}")


@app.get("/db/stats")
@app.get("/api/db/stats")
async def db_stats(key: str = Query(..., description="Your Admin API Key")):
    return await execute_db_stats(key)


# Any unauthenticated or unknown path returns direct Unauthorized access
@app.api_route("/{full_path:path}", methods=["GET", "POST", "HEAD", "OPTIONS"], include_in_schema=False)
async def catch_all(request: Request, full_path: str):
    raise HTTPException(status_code=401, detail="Unauthorized access")
