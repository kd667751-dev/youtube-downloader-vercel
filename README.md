# Zeno YouTube Downloader API (Vercel Edition) 🎬

A modern, high-performance YouTube Video & Audio Downloader deployed on **Vercel** (`*.vercel.app`), powered by a dedicated VPS backend running **FFmpeg**, **yt-dlp**, and an **SQLite Database**.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/kd667751-dev/youtube-downloader-vercel&env=VPS_BACKEND_URL,ADMIN_API_KEY)

---

## 🌟 Highlights
- **100% Vercel URLs:** All API endpoints and download links are served under your own Vercel domain (`https://your-project.vercel.app`).
- **No Payload Limit Issues:** Uses intelligent HTTP 302 redirects to stream large files (1080p, 4K, MP3) directly without hitting Vercel's 4.5 MB serverless limit.
- **VPS SQLite Database:** All API keys, generated temporary links, and download logs are permanently stored in the SQLite database on your VPS.
- **Temporary Signed Links:** Admin generates temporary links using the Secret API Key; users can download without requiring any API key.
- **Modern Web UI:** Includes a responsive Cyberpunk/Dark UI at root `/` for testing and downloads directly from the browser.
- **Interactive Swagger Documentation:** Available at `/docs`.

---

## 🚀 One-Click Deploy to Vercel

1. Click the **Deploy with Vercel** button above or import this repository in [Vercel Dashboard](https://vercel.com/new).
2. Configure the following Environment Variables in Vercel:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VPS_BACKEND_URL` | `https://glasgow-bacterial-volunteer-doing.trycloudflare.com` | Your VPS 24/7 backend worker URL |
| `ADMIN_API_KEY` | `yt_sec_794ae71a4f71a66b5dd66774` | Secret Admin Key for link generation |

3. Click **Deploy**! In 30 seconds, your API will be live with a free SSL `*.vercel.app` URL.

---

## 📦 API Endpoints

### 1. Generate Temporary Download Link
```http
GET /generate-link?url={VIDEO_URL}&key={ADMIN_API_KEY}&type={video|audio}&quality={best|1080p|720p}
```
**Example Response:**
```json
{
  "status": "success",
  "title": "Rick Astley - Never Gonna Give You Up",
  "type": "video",
  "quality": "best",
  "duration_seconds": 213,
  "download_url": "https://your-project.vercel.app/d/eyJ1cmwiOi...",
  "message": "Temporary link generated!"
}
```

### 2. Download File (No Key Required!)
```http
GET /d/{token}
```
Directly downloads the media file with proper filename and metadata.

### 3. Video Metadata Info
```http
GET /info?url={VIDEO_URL}&key={ADMIN_API_KEY}
```

### 4. Live VPS Database Statistics
```http
GET /db/stats?key={ADMIN_API_KEY}
```
Returns live stats from the SQLite database on the VPS:
- Total active API keys
- Total links generated
- Total downloads completed
- Recent download logs

---

## 🛠️ Architecture

```
User / Client
     │
     ▼
Vercel Edge Network (https://your-project.vercel.app)
  ├── Web UI (/)
  ├── Swagger Docs (/docs)
  └── API Gateway (/generate-link, /d/{token})
     │
     │ (Secure Tunnel)
     ▼
Ubuntu VPS Engine (This Server)
  ├── SQLite Database (/data/ytdl.db)
  ├── yt-dlp + Deno JS Challenge Solver
  ├── Hardcoded YouTube Cookies
  └── FFmpeg Video/Audio Muxer
```
