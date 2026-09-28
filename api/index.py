import os
import time
import secrets
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import yt_dlp

# ==========================================
# TURSO DATABASE CONFIGURATION (HARDCODED)
# ==========================================
TURSO_DATABASE_URL = os.getenv(
    "TURSO_DATABASE_URL",
    "libsql://yt-downloader-rudra-raj-nandani.aws-ap-south-1.turso.io"
)
TURSO_AUTH_TOKEN = os.getenv(
    "TURSO_AUTH_TOKEN",
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTA1NTQ1MjQsImlkIjoiMDFhMGU1NWQtYTcwMS03Y2RlLTg0YjAtZjIwYzc0ZjFkMjVjIiwia2lkIjoieGRKcXV2RFNmVWtaWkp2Z0x0ZURkWFBZSjlXOWZUZTRtd1BHaUZTTWFwRSIsInJpZCI6ImI5ZWRjOTViLTc3MjctNDkzOC04N2QxLTQ0Y2EwNmYxMGQzOSJ9._McHMPlk7DFckZJKL7nkBKPZJTtNi0gnNDugbKeaxQxhXg9_gJXY4lSiqgVmjCIQ5Sv_6ZWnSTc0EMgFYCKzDg"
)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "yt_sec_794ae71a4f71a66b5dd66774")

# Locate cookies.txt if present
COOKIES_FILE = None
for p in [Path("cookies.txt"), Path("api/cookies.txt"), Path(__file__).parent / "cookies.txt"]:
    if p.exists() and p.stat().st_size > 0:
        COOKIES_FILE = str(p)
        break


# ==========================================
# TURSO HTTP CLIENT (LIB-SQL OVER HTTP)
# ==========================================
class TursoClient:
    def __init__(self, db_url: str, auth_token: str):
        clean_url = db_url.replace("libsql://", "https://").rstrip("/")
        self.endpoint = f"{clean_url}/v2/pipeline"
        self.auth_token = auth_token

    async def execute(self, sql: str, args: list = None):
        formatted_args = []
        if args:
            for a in args:
                if a is None:
                    formatted_args.append({"type": "null"})
                elif isinstance(a, int):
                    formatted_args.append({"type": "integer", "value": str(a)})
                elif isinstance(a, float):
                    formatted_args.append({"type": "float", "value": a})
                else:
                    formatted_args.append({"type": "text", "value": str(a)})

        payload = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": formatted_args}},
                {"type": "close"}
            ]
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                self.endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            )
            data = resp.json()
            results = data.get("results", [])
            if not results or results[0].get("type") != "ok":
                raise Exception(f"Turso Error: {data}")
            exec_res = results[0]["response"]["result"]
            cols = [c["name"] for c in exec_res.get("cols", [])]
            rows = []
            for r in exec_res.get("rows", []):
                row_dict = {}
                for col_name, val_obj in zip(cols, r):
                    row_dict[col_name] = val_obj.get("value")
                rows.append(row_dict)
            return rows


turso = TursoClient(TURSO_DATABASE_URL, TURSO_AUTH_TOKEN)


# ==========================================
# FASTAPI APP & SECURITY
# ==========================================
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
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:3000"
    proto = request.headers.get("x-forwarded-proto", "https")
    if not host.startswith("http"):
        return f"{proto}://{host}"
    return host


async def verify_api_key(key: str) -> bool:
    if key == ADMIN_API_KEY:
        return True
    try:
        rows = await turso.execute("SELECT is_active FROM api_keys WHERE key = ?", [key])
        if rows and str(rows[0].get("is_active")) == "1":
            return True
    except Exception:
        pass
    return False


# Root endpoint returns direct Unauthorized access
@app.get("/")
@app.get("/api")
@app.get("/api/")
def root():
    raise HTTPException(status_code=401, detail="Unauthorized access")


# ==========================================
# 100% SERVERLESS YT-DLP EXTRACTION
# ==========================================
def extract_youtube_stream(url: str, media_type: str = "video", quality: str = "best"):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
    }
    if COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "Video")
    duration = info.get("duration", 0)
    thumbnail = info.get("thumbnail")
    formats = info.get("formats", [])

    direct_url = None
    selected_quality = quality

    if media_type == "audio":
        audio_formats = [
            f for f in formats
            if f.get("url") and f.get("vcodec") == "none" and f.get("acodec") != "none"
        ]
        if audio_formats:
            audio_formats.sort(key=lambda x: x.get("tbr") or x.get("abr") or 0, reverse=True)
            direct_url = audio_formats[0]["url"]
            selected_quality = f"{int(audio_formats[0].get('abr') or 128)}k"
        elif formats:
            direct_url = formats[0].get("url")
    else:
        # Video: Filter progressive formats (has both video & audio)
        prog_formats = [
            f for f in formats
            if f.get("url") and f.get("vcodec") != "none" and f.get("acodec") != "none"
        ]
        if prog_formats:
            # Sort by resolution/height
            prog_formats.sort(key=lambda x: x.get("height") or 0, reverse=True)
            if quality != "best":
                matched = [f for f in prog_formats if str(f.get("height")) in quality]
                if matched:
                    prog_formats = matched
            direct_url = prog_formats[0]["url"]
            selected_quality = f"{prog_formats[0].get('height')}p"
        elif formats:
            direct_url = formats[-1].get("url")

    if not direct_url:
        raise HTTPException(status_code=500, detail="Could not extract direct stream URL from YouTube")

    return {
        "title": title,
        "duration": duration,
        "thumbnail": thumbnail,
        "direct_url": direct_url,
        "quality": selected_quality
    }


# ==========================================
# API ENDPOINTS (TURSO DB BACKED)
# ==========================================
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
    if not await verify_api_key(key):
        raise HTTPException(status_code=401, detail="Invalid API Key")

    try:
        stream_data = extract_youtube_stream(url, media_type=type, quality=quality or "best")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Extraction failed: {str(e)}")

    token = secrets.token_urlsafe(24)
    expires_at = int(time.time()) + expires_in
    vercel_domain = get_vercel_base_url(request)
    download_url = f"{vercel_domain}/d/{token}"

    try:
        await turso.execute(
            """
            INSERT INTO temp_links (token, video_url, title, format_type, quality, download_url, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [token, url, stream_data["title"], type, stream_data["quality"], stream_data["direct_url"], expires_at]
        )
    except Exception as e:
        # Fallback if DB insert fails
        pass

    return {
        "status": "success",
        "title": stream_data["title"],
        "type": type,
        "quality": stream_data["quality"],
        "duration_seconds": stream_data["duration"],
        "thumbnail": stream_data["thumbnail"],
        "expires_in_seconds": expires_in,
        "download_url": download_url,
        "message": "Temporary link generated! You can download directly from download_url without providing an API key."
    }


@app.get("/d/{token}")
@app.get("/api/d/{token}")
async def download_temp_link(
    request: Request,
    token: str
):
    """
    Public Vercel download endpoint (No API key required).
    Fetches direct stream from Turso DB and 302 redirects client.
    """
    try:
        rows = await turso.execute("SELECT * FROM temp_links WHERE token = ?", [token])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not rows:
        raise HTTPException(status_code=404, detail="Download link not found")

    link_data = rows[0]
    expires_at = int(link_data.get("expires_at") or 0)
    if time.time() > expires_at:
        raise HTTPException(status_code=410, detail="Download link has expired")

    direct_stream_url = link_data.get("download_url")
    if not direct_stream_url:
        raise HTTPException(status_code=404, detail="Direct stream URL not found")

    # Log the download in Turso DB
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    try:
        await turso.execute(
            """
            INSERT INTO download_logs (token, title, format_type, quality, client_ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                token,
                link_data.get("title", "Video"),
                link_data.get("format_type", "video"),
                link_data.get("quality", "best"),
                client_ip,
                user_agent
            ]
        )
    except Exception:
        pass

    return RedirectResponse(url=direct_stream_url, status_code=302)


@app.get("/info")
@app.get("/api/info")
async def get_info(
    url: str = Query(..., description="YouTube Video URL"),
    key: str = Query(..., description="Your Admin API Key")
):
    if not await verify_api_key(key):
        raise HTTPException(status_code=401, detail="Invalid API Key")

    try:
        stream_data = extract_youtube_stream(url, media_type="video", quality="best")
        return {
            "status": "success",
            "title": stream_data["title"],
            "duration_seconds": stream_data["duration"],
            "thumbnail": stream_data["thumbnail"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch info: {str(e)}")


@app.get("/db/stats")
@app.get("/api/db/stats")
async def db_stats(key: str = Query(..., description="Your Admin API Key")):
    if not await verify_api_key(key):
        raise HTTPException(status_code=401, detail="Invalid API Key")

    try:
        keys_count = await turso.execute("SELECT COUNT(*) as count FROM api_keys WHERE is_active = 1;")
        links_count = await turso.execute("SELECT COUNT(*) as count FROM temp_links;")
        downloads_count = await turso.execute("SELECT COUNT(*) as count FROM download_logs;")
        recent = await turso.execute("SELECT title, format_type, quality, client_ip, downloaded_at FROM download_logs ORDER BY id DESC LIMIT 5;")

        return {
            "status": "success",
            "database_provider": "Turso Cloud (libSQL)",
            "database_url": TURSO_DATABASE_URL,
            "total_api_keys": int(keys_count[0].get("count") or 0) if keys_count else 0,
            "total_links_generated": int(links_count[0].get("count") or 0) if links_count else 0,
            "total_downloads_completed": int(downloads_count[0].get("count") or 0) if downloads_count else 0,
            "recent_downloads": recent
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Turso DB error: {str(e)}")


# Any unauthenticated or unknown path returns direct Unauthorized access
@app.api_route("/{full_path:path}", methods=["GET", "POST", "HEAD", "OPTIONS"], include_in_schema=False)
async def catch_all(request: Request, full_path: str):
    raise HTTPException(status_code=401, detail="Unauthorized access")
