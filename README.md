# YouTube Downloader API (Vercel Gateway) 🎬

A private, high-performance YouTube Video & Audio Downloader API deployed on **Vercel** (`*.vercel.app`), powered by a dedicated VPS backend running **FFmpeg**, **yt-dlp**, and an **SQLite Database**.

---

## 🌟 Highlights
- **100% Vercel URLs:** All generated download links are served under your own Vercel domain (`https://your-project.vercel.app/d/{token}`).
- **Stealth & Protected:** Root `/` and unauthenticated paths return `401 Unauthorized access`. No public frontend or Swagger UI.
- **No Payload Limit Issues:** Uses intelligent HTTP 302 redirects to stream large files (1080p, 4K, MP3) directly from the VPS without hitting Vercel's 4.5 MB serverless limit.
- **VPS SQLite Database:** All API keys, generated temporary links, and download logs are permanently stored in the SQLite database on your VPS.
- **Temporary Signed Links:** Admin generates temporary links using the Secret API Key; users can download without requiring any API key.

---

## 🚀 Environment Variables

| Variable | Description |
| :--- | :--- |
| `VPS_BACKEND_URL` | Your VPS 24/7 backend worker URL |
| `ADMIN_API_KEY` | Secret Admin Key for link generation |

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
  "title": "Sample Video Title",
  "type": "video",
  "quality": "best",
  "duration_seconds": 213,
  "download_url": "https://your-project.vercel.app/d/eyJ1cmwiOi...",
  "message": "Temporary link generated!"
}
```

### 2. Download File (Public - No Key Required!)
```http
GET /d/{token}
```
Directly downloads the media file with original audio/video and proper filename.

### 3. Video Metadata Info
```http
GET /info?url={VIDEO_URL}&key={ADMIN_API_KEY}
```

### 4. Database Statistics (Admin Only)
```http
GET /db/stats?key={ADMIN_API_KEY}
```
