# YouTube Downloader API (100% Serverless + Turso DB) 🎬

A private, 100% serverless YouTube Video & Audio Downloader API running on **Vercel** (`*.vercel.app`) and powered by **Turso Cloud Database (libSQL)**.

**Zero VPS required! No tunnels, no daemons, zero server maintenance.**

---

## 🌟 Highlights
- **100% Serverless on Vercel:** Runs entirely on Vercel Python runtime using `yt-dlp`.
- **Turso Cloud Database:** All API keys, temporary links, and download logs are permanently stored in Turso (edge libSQL/SQLite).
- **Stealth & Protected:** Root `/` and unauthenticated paths return `401 Unauthorized access`.
- **100% Vercel URLs:** Generated download links are served under your own Vercel domain (`https://your-project.vercel.app/d/{token}`).
- **Direct High-Speed CDN Streaming:** Users download directly via smart 302 redirects with zero server bandwidth bottlenecks.

---

## 🚀 Environment Variables (Already Pre-Configured)

| Variable | Description |
| :--- | :--- |
| `TURSO_DATABASE_URL` | Your Turso DB URL (`libsql://...`) |
| `TURSO_AUTH_TOKEN` | Your Turso JWT Auth Token |
| `ADMIN_API_KEY` | Secret Admin Key for link generation (`yt_sec_...`) |

---

## 📦 API Endpoints

### 1. Generate Temporary Download Link
```http
GET /generate-link?url={VIDEO_URL}&key={ADMIN_API_KEY}&type={video|audio}&quality={best|720p|360p}
```

### 2. Download File (Public - No Key Required!)
```http
GET /d/{token}
```
Directly downloads the media file with high speed and proper filename.

### 3. Video Metadata Info
```http
GET /info?url={VIDEO_URL}&key={ADMIN_API_KEY}
```

### 4. Database Statistics (Admin Only - Live Turso DB)
```http
GET /db/stats?key={ADMIN_API_KEY}
```
