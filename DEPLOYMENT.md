# Deployment Guide: Vercel (Frontend) + Railway (Backend)

This project is split into:

- **Frontend**: Next.js app in `frontend/` → deploy to **Vercel**
- **Backend**: FastAPI app (run from repo root) → deploy to **Railway**

Deploy the backend first so you have its URL for the frontend.

---

## 1. Deploy backend to Railway

1. **Create a Railway project** at [railway.app](https://railway.app) and connect this Git repo.

2. **Add a new service** from the repo. Railway will detect Python. Configure:
   - **Root Directory**: leave empty (repo root).
   - **Install Command** (in Service → **Settings** → **Build**): **You must set this**, or the default will only install the root `requirements.txt` and **uvicorn will not be installed** (leading to `uvicorn: not found` and 502 Bad Gateway). Set:
     ```bash
     pip install -r requirements-backend.txt
     ```
     If there is no Install Command field, add a **Variable** instead: `RAILPACK_INSTALL_COMMAND` = `pip install -r requirements-backend.txt`, then redeploy.
   - **Start Command**: already set in `railway.json`:
     ```bash
     uvicorn api.main:app --host 0.0.0.0 --port $PORT
     ```
     Railway sets `PORT` automatically.

3. **Environment variables** (Service → Variables): add all keys your backend needs (same as `.env` locally), plus CORS:
   - From `.env.example`: `SERPER_API_KEY`, `ATLAS_CLOUD_API`, `OPENROUTER_API_KEY`, and optionally `JINA_READER_API_KEY`.
   - **CORS** (required for the Vercel frontend to call the API):
     ```bash
     CORS_ORIGINS=https://your-app.vercel.app,https://your-app-*.vercel.app
     ```
     Replace with your real Vercel URL(s). You can add this after deploying the frontend and then redeploy the backend.

4. **Domain**: In Railway, open your service → **Settings** → **Networking** → **Generate Domain**. Copy the URL (e.g. `https://your-service.up.railway.app`). You will use this as `NEXT_PUBLIC_API_URL` in Vercel.

5. **Deploy**: Push to your connected branch or trigger a deploy. Check **Deployments** and **Logs** to confirm the app starts and `/api/health` returns `{"status":"healthy"}`.

---

## 2. Deploy frontend to Vercel

1. **Create a Vercel project** at [vercel.com](https://vercel.com) and import this Git repo.

2. **Root Directory**: In Project Settings → **General** → **Root Directory**, set to **`frontend`**. This makes Vercel build and run the Next.js app from that folder.

3. **Environment variable** (Project Settings → **Environment Variables**):
   - **Name**: `NEXT_PUBLIC_API_URL`
   - **Value**: your Railway backend URL (e.g. `https://your-service.up.railway.app`)
   - Apply to Production (and Preview if you want preview deployments to use the same API).

4. **Deploy**: Save and redeploy. The frontend will call the backend at `NEXT_PUBLIC_API_URL`.

---

## 3. Connect frontend and backend

1. **Backend CORS**: In Railway, ensure `CORS_ORIGINS` includes your Vercel URLs, for example:
   ```bash
   CORS_ORIGINS=https://your-project.vercel.app,https://your-project-*.vercel.app
   ```
   Use the exact production and preview hostnames Vercel shows.

2. **Frontend API URL**: Ensure `NEXT_PUBLIC_API_URL` in Vercel points to the Railway URL (no trailing slash).

3. **Test**: Open the Vercel app, create a run or open the runs list. If you see “Could not reach the API”, check CORS and `NEXT_PUBLIC_API_URL`, and that the backend is up and `/api/health` is reachable in the browser.

---

## Files added for deployment

| File | Purpose |
|------|--------|
| `Procfile` | Declares `web` process for Railway/Heroku (uvicorn with `$PORT`). |
| `railway.json` | Railway start command so the API runs on Railway’s `PORT`. |
| `requirements-backend.txt` | Single file to install all backend deps: `pip install -r requirements-backend.txt`. |
| `api/main.py` | CORS reads `CORS_ORIGINS` from env so production frontend origin is allowed. |
| `.env.example` | Documented `CORS_ORIGINS` and `NEXT_PUBLIC_API_URL` for deployment. |

---

## Optional: Run backend locally with same port behavior as Railway

```bash
# From repo root
pip install -r requirements-backend.txt
$env:PORT=8000; uvicorn api.main:app --host 0.0.0.0 --port 8000   # Windows PowerShell
# Or
PORT=8000 uvicorn api.main:app --host 0.0.0.0 --port 8000          # Linux/macOS
```

Frontend locally: in `frontend/.env.local` set `NEXT_PUBLIC_API_URL=http://localhost:8000` (or leave unset to use that default).
