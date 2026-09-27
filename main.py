import os
import urllib.parse
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

# Configuration: Points to VPS backend worker & SQLite database
VPS_BACKEND_URL = os.getenv("VPS_BACKEND_URL", "https://glasgow-bacterial-volunteer-doing.trycloudflare.com").rstrip("/")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "yt_sec_794ae71a4f71a66b5dd66774")

app = FastAPI(
    title="YouTube Direct Downloader (Vercel Edition)",
    description="Vercel serverless gateway for YouTube direct video/audio downloads backed by VPS SQLite database and FFmpeg processing engine.",
    version="3.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
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
    Normalizes paths if Vercel serverless runtime passes rewritten file prefixes
    like /api/index.py, /api/main.py, /index.py, etc.
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


def render_html_ui(request: Request) -> str:
    vercel_base = get_vercel_base_url(request)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Zeno YouTube Downloader | Vercel</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            * {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
            body {{
                background: #090d16;
                color: #f1f5f9;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            .main-card {{
                background: #111827;
                border: 1px solid #1f2937;
                border-radius: 20px;
                padding: 40px;
                max-width: 680px;
                width: 100%;
                box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.7);
            }}
            .badge-vercel {{
                background: #ffffff;
                color: #000000;
                font-weight: 700;
                font-size: 12px;
                padding: 6px 14px;
                border-radius: 999px;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 18px;
            }}
            .form-control, .form-select {{
                background: #0b0f19;
                border: 1px solid #374151;
                color: #f8fafc;
                border-radius: 12px;
                padding: 12px 16px;
            }}
            .form-control:focus, .form-select:focus {{
                background: #0b0f19;
                color: #fff;
                border-color: #38bdf8;
                box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
            }}
            .btn-action {{
                background: linear-gradient(135deg, #0284c7, #2563eb);
                border: none;
                border-radius: 12px;
                padding: 14px;
                font-weight: 700;
                color: white;
                transition: transform 0.15s, opacity 0.15s;
            }}
            .btn-action:hover {{
                opacity: 0.95;
                transform: translateY(-1px);
            }}
            .code-box {{
                background: #050811;
                border: 1px solid #1f2937;
                border-radius: 10px;
                padding: 14px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 13px;
                color: #38bdf8;
                word-break: break-all;
                text-align: left;
            }}
            a {{ color: #38bdf8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="main-card">
            <div class="text-center">
                <div class="badge-vercel">
                    <svg width="14" height="14" viewBox="0 0 116 100" fill="black"><path d="M57.5 0L115 100H0L57.5 0z"/></svg>
                    Deployed on Vercel
                </div>
                <h2 class="fw-bold mb-2 text-white">🎬 YouTube Downloader API</h2>
                <p class="text-secondary small mb-4">
                    High-speed direct MP4 & MP3 downloads via Vercel URLs &bull; VPS Database &bull; FFmpeg Engine
                </p>
            </div>

            <form id="dlForm" onsubmit="handleGenerate(event)">
                <div class="mb-3">
                    <label class="form-label fw-semibold small text-secondary">YouTube Video URL</label>
                    <input type="url" id="videoUrl" class="form-control" placeholder="https://www.youtube.com/watch?v=... or Shorts" required>
                </div>

                <div class="row mb-3">
                    <div class="col-md-6 mb-2">
                        <label class="form-label fw-semibold small text-secondary">Media Format</label>
                        <select id="mediaType" class="form-select" onchange="toggleQuality()">
                            <option value="video">MP4 Video (Video + Audio)</option>
                            <option value="audio">MP3 Audio (Music / Speech)</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-2">
                        <label class="form-label fw-semibold small text-secondary">Quality</label>
                        <select id="quality" class="form-select">
                            <option value="best" selected>Best Available (Auto)</option>
                            <option value="1080p">1080p Full HD</option>
                            <option value="720p">720p HD</option>
                            <option value="480p">480p</option>
                            <option value="360p">360p</option>
                        </select>
                    </div>
                </div>

                <div class="mb-4">
                    <label class="form-label fw-semibold small text-secondary">Admin API Key</label>
                    <input type="text" id="apiKey" class="form-control" value="{ADMIN_API_KEY}" required>
                </div>

                <button type="submit" id="submitBtn" class="btn btn-action w-100 mb-3">
                    🚀 Generate Download Link
                </button>
            </form>

            <div id="resultBox" class="mt-4 d-none">
                <div class="alert alert-success border-0 bg-opacity-10 bg-success text-success p-3 rounded-3 mb-3">
                    <div class="fw-bold mb-1" id="resTitle"></div>
                    <div class="small opacity-75" id="resMeta"></div>
                </div>
                <label class="form-label fw-semibold small text-secondary">Your Vercel Download Link (No Key Required):</label>
                <div class="code-box mb-3" id="resLink"></div>
                <a href="#" id="directDownloadBtn" class="btn btn-outline-info w-100 fw-bold py-2">
                    ⬇️ Start Download
                </a>
            </div>

            <div id="errorAlert" class="alert alert-danger mt-3 d-none"></div>

            <hr class="border-secondary border-opacity-25 my-4">
            <div class="small text-secondary text-center">
                Vercel Domain: <code>{vercel_base}</code><br>
                Interactive Swagger Docs: <a href="/docs" target="_blank">/docs</a> &bull; Database Stats: <a href="/db/stats?key={ADMIN_API_KEY}" target="_blank">/db/stats</a>
            </div>
        </div>

        <script>
            function toggleQuality() {{
                const type = document.getElementById('mediaType').value;
                const q = document.getElementById('quality');
                if (type === 'audio') {{
                    q.innerHTML = `
                        <option value="320k">320 kbps (High Quality)</option>
                        <option value="192k" selected>192 kbps (Standard)</option>
                        <option value="128k">128 kbps (Compact)</option>
                    `;
                }} else {{
                    q.innerHTML = `
                        <option value="best" selected>Best Available (Auto)</option>
                        <option value="1080p">1080p Full HD</option>
                        <option value="720p">720p HD</option>
                        <option value="480p">480p</option>
                        <option value="360p">360p</option>
                    `;
                }}
            }}

            async function handleGenerate(e) {{
                e.preventDefault();
                const url = encodeURIComponent(document.getElementById('videoUrl').value.trim());
                const key = encodeURIComponent(document.getElementById('apiKey').value.trim());
                const type = document.getElementById('mediaType').value;
                const quality = document.getElementById('quality').value;
                const btn = document.getElementById('submitBtn');
                const errBox = document.getElementById('errorAlert');
                const resBox = document.getElementById('resultBox');

                errBox.classList.add('d-none');
                resBox.classList.add('d-none');
                btn.disabled = true;
                btn.innerHTML = '⏳ Processing with VPS Engine...';

                try {{
                    const res = await fetch(`/generate-link?url=${{url}}&key=${{key}}&type=${{type}}&quality=${{quality}}`);
                    const data = await res.json();

                    if (!res.ok) {{
                        throw new Error(data.detail || data.message || 'Request failed');
                    }}

                    document.getElementById('resTitle').innerText = data.title || 'Video Ready';
                    document.getElementById('resMeta').innerText = `Format: ${{data.type?.toUpperCase()}} | Quality: ${{data.quality}} | Duration: ${{data.duration_seconds}}s`;
                    document.getElementById('resLink').innerText = data.download_url;
                    document.getElementById('directDownloadBtn').href = data.download_url;
                    resBox.classList.remove('d-none');
                }} catch (err) {{
                    errBox.innerText = '❌ ' + err.message;
                    errBox.classList.remove('d-none');
                }} finally {{
                    btn.disabled = false;
                    btn.innerHTML = '🚀 Generate Download Link';
                }}
            }}
        </script>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
def index(request: Request):
    """Modern Dark UI for testing and direct browser downloads from Vercel."""
    return render_html_ui(request)


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
