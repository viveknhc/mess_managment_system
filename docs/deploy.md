# Deploying Mess Manager (free tier)

| Part | Host | What it does |
|---|---|---|
| Database | **Neon** (free Postgres) | Stores all data permanently |
| Backend API | **Render** (free web service) | Runs Django from `backend/` using `render.yaml` + `backend/build.sh` |
| Frontend | **Vercel** (free) | Serves the React app from `frontend/` using `frontend/vercel.json` |

Sign up for all three with your GitHub account. Total time: about 20 minutes. Free-tier limits change from time to time, so check each site's pricing page.

---

## 1. Database: Neon

1. Go to **neon.tech** → sign up → **Create project**.
   - Name: `mess-manager`
   - Postgres version: 15 or newer
   - Region: **Asia Pacific (Singapore)**
2. On the project dashboard click **Connect**, untick **Connection pooling** (use the *direct* connection) and copy the connection string. It looks like:
   ```
   postgresql://neondb_owner:xxxx@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
   Keep it private. This is your `DATABASE_URL`.

## 2. Backend: Render

1. Go to **render.com** → sign up with GitHub → allow access to the `mess_managment_system` repo.
2. **New +** → **Blueprint** → pick the repo. Render reads `render.yaml` and shows a service called `mess-manager-api`.
3. Fill in the values it asks for:
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Neon connection string from step 1 |
   | `SUPERADMIN_PASSWORD` | a strong password of your choice (platform admin login) |
   | `CORS_ALLOWED_ORIGINS` | `https://example.com` for now. You'll replace it in step 4 |
4. Click **Apply**. The first build takes 3–5 minutes. It installs packages, creates the tables, creates the `superadmin` user and loads the demo data (`SEED_DEMO=1`).
5. When it shows **Live**, copy the URL at the top, e.g. `https://mess-manager-api.onrender.com`.
   Check it in a browser: `https://<your-render-url>/api/v1/pricing/` should show `[]`.

## 3. Frontend: Vercel

1. Go to **vercel.com** → sign up with GitHub → **Add New… → Project** → import `mess_managment_system`.
2. Settings:
   - **Root Directory:** `frontend` (click *Edit* and choose it)
   - Framework preset: **Vite** (auto-detected)
   - **Environment Variables:** `VITE_API_BASE_URL` = `https://<your-render-url>/api/v1`
3. Click **Deploy**. After about a minute you get a URL like `https://mess-managment-system.vercel.app`.

## 4. Connect them

Back in **Render** → `mess-manager-api` → **Environment** → set
`CORS_ALLOWED_ORIGINS` = your Vercel URL (e.g. `https://mess-managment-system.vercel.app`, no trailing slash) → **Save changes**. Render redeploys automatically.

## 5. Try it

Open your Vercel URL and log in:
- Platform admin: `superadmin` / the password you set
- Demo business: the usernames printed by `seed_data` (`owner`, `manager`, `delivery1`, `kitchen1`, `customer1`–`customer5`)

Django admin is at `https://<your-render-url>/admin/` (log in as `superadmin`).

---

## Updating

Push to `main`. **Render and Vercel both redeploy automatically.** Database migrations run during the Render build.

## Free-tier limitations (good to know)

- **The backend sleeps** after ~15 minutes without traffic. The first request after that takes 30–60 seconds while it wakes up; open the site a minute before a demo.
- **Demo logins are public.** The demo passwords (`owner123` etc.) are in the public repo's seed script, so anyone who finds the site can log into the demo business. That's fine for a demo. For real use, set `SEED_DEMO` to `0` before the first deploy (or use a fresh database) and sign up a real business instead.
- **Logo uploads don't persist.** Render's free disk is wiped on every deploy/restart and uploaded files aren't served in production. A file storage service (e.g. Cloudinary or S3) is needed for that.
- **Background jobs don't run.** There's no Celery/Redis on the free plan, so the daily trial-expiry and past-due checks don't run automatically. Everything else works.
- **Online billing is off.** Razorpay keys aren't set, so SaaS plans without a Razorpay Plan ID activate instantly (dev mode).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Frontend loads, login says "Invalid username or password" for every user | Backend asleep or URL wrong. Open `https://<render-url>/api/v1/pricing/` and wait for `[]`, then check Vercel's `VITE_API_BASE_URL` (must end in `/api/v1`, then redeploy Vercel). |
| Browser console shows a **CORS** error | `CORS_ALLOWED_ORIGINS` on Render must exactly match the Vercel URL (https, no trailing slash). |
| Refreshing a page like `/app/customers` gives 404 | Vercel Root Directory must be `frontend` so `vercel.json` is used. |
| Render build fails at `migrate` | `DATABASE_URL` is wrong or missing `?sslmode=require`. |
| Render says Python version not found | Change `PYTHON_VERSION` in Render → Environment to a 3.12.x version Render lists. |
