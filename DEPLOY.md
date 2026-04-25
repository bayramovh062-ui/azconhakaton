# Deploying AZMarine

Two pieces, deployed separately:

| Component | Where             | Why                                         |
| --------- | ----------------- | ------------------------------------------- |
| Frontend  | **Vercel**        | Static SPA, fast global CDN                 |
| Backend   | **Render** (free) | Persistent FastAPI + **WebSocket** support  |

> ⚠️ **Vercel cannot host the backend.** Vercel's serverless functions don't support long-lived WebSockets or background asyncio tasks (the AIS simulator + JIT broadcaster). Render's free web service does.

---

## 1) Backend — Render

1. Go to https://dashboard.render.com/blueprints → **New Blueprint Instance**.
2. Connect the repo `Niz09090/holberton_hakaton`.
3. Render reads `render.yaml` and creates **`azmarine-api`** automatically.
4. Wait ~3–5 min for the first build (it runs `bootstrap_rich.py` so the DB is seeded).
5. Note the public URL, e.g. `https://azmarine-api.onrender.com`.

Sanity check:

```bash
curl https://azmarine-api.onrender.com/        # {"service":"AZMarine",...}
curl https://azmarine-api.onrender.com/health  # {"status":"healthy"}
```

> Free dyno sleeps after 15 min of idle. First request after a sleep takes ~30 s to wake. That's fine for a demo.

---

## 2) Frontend — Vercel

### Settings → General

| Field                | Value           |
| -------------------- | --------------- |
| **Root Directory**   | `frontend`      |
| Framework Preset     | Vite            |
| Build Command        | `npm run build` |
| Output Directory     | `dist`          |
| Install Command      | `npm install`   |

Vercel auto-detects most of this once Root Directory is set; `frontend/vercel.json` provides the SPA rewrite (`/(.*) → /index.html`) so React Router routes work on hard refresh.

### Settings → Environment Variables

Add to **Production**, **Preview**, **Development**:

| Key             | Value                                              |
| --------------- | -------------------------------------------------- |
| `VITE_API_BASE` | `https://azmarine-api.onrender.com`                |
| `VITE_WS_URL`   | `wss://azmarine-api.onrender.com/ws/fleet`         |

After saving, **Deployments → Redeploy**.

---

## 3) Why the previous deploy showed `404 NOT_FOUND`

The error `fra1::…` page is Vercel's "no route matched". Causes (any of these):

1. **Root directory wasn't `frontend/`** — Vercel scanned the repo root, found no `package.json`, didn't build anything → every URL 404s.
2. **No SPA rewrite** — even with a successful build, going to `/login` server-side returns 404 because there's no static file at `/login`. Fixed by `frontend/vercel.json`.
3. **No env vars** — the SPA loads, but every API call goes to `http://127.0.0.1:8765` (the dev default in `frontend/src/config.js`), which obviously won't work from a browser on `*.vercel.app`. Fixed by setting `VITE_API_BASE` and `VITE_WS_URL`.

---

## 4) After both are deployed

Open your Vercel URL → log in with any demo account from the README. The browser connects:

- HTTPS REST → `https://azmarine-api.onrender.com/auth/login`
- WSS realtime → `wss://azmarine-api.onrender.com/ws/fleet`

Both work over TLS, so no mixed-content blocking.

---

## 5) Custom domain (optional)

- **Vercel** → add CNAME `app.azmarine.io → cname.vercel-dns.com`.
- **Render** → add `api.azmarine.io` to the service; Render issues a TLS cert automatically.
- Then update Vercel env vars to use `https://api.azmarine.io` / `wss://api.azmarine.io/ws/fleet`.
