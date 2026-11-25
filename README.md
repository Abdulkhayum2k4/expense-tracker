# Personal Expense Tracker

Register, log in, and track income, expenses and monthly budgets per category, with charts.

| Layer | Technology |
|---|---|
| Frontend | Vue 3 (Composition API) + Vite, Vue Router, Tailwind CSS v4, Chart.js (vue-chartjs), axios |
| Backend | Python + FastAPI, PyMongo async driver |
| Database | MongoDB |
| Auth | JWT (PyJWT), passwords hashed with pwdlib + Argon2 |

## Project layout

```
backend/
  app/
    main.py            FastAPI app, CORS, router registration
    config.py          settings read from backend/.env
    database.py        Mongo connection + indexes
    security.py        Argon2 hashing, JWT create/verify
    deps.py            current-user dependency (Bearer token)
    schemas.py         Pydantic request/response models
    serializers.py     Mongo document -> API response helpers
    routers/           auth, categories, transactions, budgets, analytics
  postman_collection.json
frontend/
  src/
    api/client.js      axios instance + one function per endpoint
    stores/auth.js     token + user, persisted in localStorage
    router/index.js    routes and the login guard
    views/             Login, Register, Dashboard, Transactions, Budgets, Categories
    components/        nav, modal, transaction form, budget bar, charts
```

## Running it locally

You need **Python 3.11+**, **Node 20+**, and a **MongoDB** server: either
[MongoDB Community Server](https://www.mongodb.com/try/download/community) on your machine
or a free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster.

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

Edit `backend/.env`: set `MONGODB_URL`, and set `JWT_SECRET` to a random value:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Start the API:

```bash
fastapi dev app/main.py         # or: uvicorn app.main:app --reload
```

The API runs at http://localhost:8000. Interactive docs are at http://localhost:8000/docs.
Click **Authorize** there and paste a token from `/api/auth/login`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. In development, Vite forwards `/api` to `http://localhost:8000`, so no CORS setup is needed.
To change the currency (default INR), copy `frontend/.env.example` to `frontend/.env.local` and edit `VITE_CURRENCY` / `VITE_LOCALE`.

### 3. Postman

Import `backend/postman_collection.json`. Run **Auth → Register** (or **Login**) first. The token is saved
automatically and sent with every other request.

## API

All routes except register, login and health need `Authorization: Bearer <token>`.
Every query is scoped to the logged-in user.

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | `{name, email, password}` → token + user. Seeds default categories. |
| POST | `/api/auth/login` | `{email, password}` → token + user |
| GET | `/api/auth/me` | current user |
| GET/POST | `/api/categories` | `?type=expense\|income` |
| PUT/DELETE | `/api/categories/{id}` | a rename carries over to transactions and budgets; delete is refused while transactions use it |
| GET/POST | `/api/transactions` | filters: `type, category, start_date, end_date, search, page, page_size` |
| GET/PUT/DELETE | `/api/transactions/{id}` | |
| GET/POST | `/api/budgets` | `?month=&year=` (defaults to the current month). Each budget includes `spent`, `remaining`, `percent_used` |
| PUT/DELETE | `/api/budgets/{id}` | |
| GET | `/api/analytics/summary` | `?month=&year=`: dashboard data: income, expense, savings and savings rate, total balance (all transactions to the end of that month), per-category breakdown, 5 latest transactions |
| GET | `/api/analytics/trend` | `?year=`: income and expense for each month |
| GET | `/api/analytics/breakdown` | `?year=&month=`: category totals for a month, or for the whole year when `month` is omitted |
| GET | `/api/analytics/compare` | `?month=&year=`: spending per category against the previous month |

## Features

| Module | What it does |
|---|---|
| Dashboard | Total balance, this month's income, expenses and savings (with savings rate), category chart, budget progress, yearly trend, recent transactions |
| Transactions | Add, edit, delete and view income and expenses, with search, filters and paging |
| Categories | Default set on sign-up (Food, Transport, Shopping, Bills, Salary…); add, rename, delete |
| Analytics | Year totals and averages, monthly income vs spending, net savings per month, category breakdown for a month or year, month-over-month change per category |
| Budgets | Monthly limit per expense category with spent / remaining / % used, and copying last month's budgets |

## Data model

Four collections, matching the design: `users`, `transactions`, `categories`, `budgets`.

- `user_id` fields hold the user's ObjectId.
- Transaction `date` is stored as a BSON date at midnight UTC. The API sends and receives `YYYY-MM-DD`.
- Transactions and budgets refer to categories **by name**, as in the original design. That's why renaming a category updates them too.
- Indexes: unique `users.email`; unique `(user_id, type, name)` on categories; unique `(user_id, year, month, category)` on budgets;
  `(user_id, date)` and `(user_id, category)` on transactions.
