# Deploying online (free tiers)

| Piece | Host | Free tier |
|---|---|---|
| Database | MongoDB Atlas | M0 cluster, 512 MB |
| API (FastAPI) | Render | Web service; sleeps after 15 min idle |
| Frontend (Vue) | Vercel | Hobby plan |

The browser only ever talks to the Vercel domain: Vercel forwards `/api/*` to Render
(`frontend/vercel.json`). The login cookie is then first-party, so it works in browsers
that block third-party cookies, and no CORS setup is needed.

Total time: about 20 minutes. You need a GitHub login; all three services let you sign in with it.

---

## 1. MongoDB Atlas: the database

1. Sign up at <https://www.mongodb.com/cloud/atlas/register>.
2. **Create a cluster** → choose **M0 (Free)**. For the region, pick the one closest to Render's Singapore
   region (e.g. AWS / Mumbai or Singapore). Create it.
3. **Database Access** → *Add New Database User* → username `expense-app`, a generated password
   (copy it), role *Read and write to any database*.
4. **Network Access** → *Add IP Address* → **Allow access from anywhere** (`0.0.0.0/0`).
   Render's free tier has no fixed IP, so this is needed; the database password still protects it.
5. **Database** → *Connect* → *Drivers* → copy the connection string. It looks like
   `mongodb+srv://expense-app:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`.
   Put your password in place of `<password>`. If the password has characters like `@ : / ? #`,
   generate a new one without them.

## 2. Render: the API

1. Sign up at <https://render.com> with GitHub and allow access to the `expense-tracker` repo.
2. **New** → **Blueprint** → pick the repo. Render reads `render.yaml` and proposes the
   `expense-tracker-api` service.
3. It asks for `MONGODB_URL`: paste the Atlas string from step 1.5. `JWT_SECRET` is generated for you.
4. **Apply**. The first build takes a few minutes.
5. When it's live, open `https://<your-service>.onrender.com/api/health`. You should see `{"status":"ok"}`.
   Note the exact URL; if `expense-tracker-api` was taken, Render adds a suffix.

## 3. Vercel: the frontend

1. If your Render URL is **not** `https://expense-tracker-api.onrender.com`, edit
   `frontend/vercel.json`, put your URL in the `/api/:path*` destination, then commit and push.
2. Sign up at <https://vercel.com> with GitHub → **Add New** → **Project** → import `expense-tracker`.
3. Set **Root Directory** to `frontend`. Vercel detects Vite (build `npm run build`, output `dist`).
   No environment variables are needed.
4. **Deploy**. Open the `https://<project>.vercel.app` URL it gives you.

## 4. Check it

1. Register an account, add a transaction and check the dashboard.
2. In the browser's devtools → *Application* → *Cookies*: `access_token` should show
   **HttpOnly**, **Secure**, path `/api`.
3. Reload the page: you should still be logged in.

Every push to `main` redeploys both (Render via `autoDeploy`, Vercel via its GitHub integration),
and GitHub Actions runs the tests on the same push.

## Free-tier things to know

- **Render sleeps after 15 minutes without requests.** The first request after that takes
  30–60 seconds while it wakes up. If the first page load shows a network error, wait a moment and reload.
  A paid instance ($7/month) stays awake.
- The login rate limit is kept in memory, so it resets when Render restarts the service. That's fine for one instance.
- Atlas M0 has 512 MB of storage, which is plenty for personal use.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Render deploy fails at startup with a MongoDB timeout | Atlas *Network Access* doesn't allow `0.0.0.0/0`, or the password in `MONGODB_URL` is wrong |
| Logging in succeeds but you're logged out on reload | `vercel.json` points at the wrong Render URL, so `/api` isn't going through Vercel |
| Every API call returns 404 on Vercel | Root Directory isn't `frontend`, so `vercel.json` wasn't picked up |
| `/api/health` works but register returns 500 | Check Render → *Logs*; usually the Atlas user lacks read/write rights |
