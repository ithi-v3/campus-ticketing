# Campus Maintenance Desk

A ticketing system for campus maintenance complaints. Students report a problem (broken fan, leaking
tap, dead Wi-Fi), an admin hands it to a technician, the technician marks it fixed, and the student
rates the job. Tickets that nobody picks up in time are escalated automatically.

Built for BCSE302P (Database Systems Lab) as the Campus Complaint & Maintenance Ticketing System.

**Stack:** React (Vite) · Flask · PostgreSQL · SQLAlchemy · JWT + bcrypt · GitHub Actions

```
database/   SQL: schema, triggers, view, function, seed + demo data, backup script
backend/    Flask API (app/, tests/)
frontend/   React app
docs/       ER diagram
```

## Running it locally

You need Python 3.11+, Node 18+ and PostgreSQL 14+.

**1. Database**

```bash
createdb ticketing
```

**2. Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then edit DATABASE_URL and JWT_SECRET
flask --app run init-db --demo                         # creates tables, triggers, demo data
flask --app run run                                    # API on http://localhost:5000
```

Leave off `--demo` if you want an empty system (you'd then need to create the first admin by hand
in SQL). Generate a proper secret with `python -c "import secrets; print(secrets.token_hex(32))"`.

If you'd rather load the SQL yourself:
`psql ticketing -f database/01_schema.sql -f database/02_seed.sql -f database/03_demo_data.sql`

**3. Frontend**

```bash
cd frontend
npm install
npm run dev                                            # http://localhost:5173
```

In dev, Vite forwards `/api` to the Flask server, so there's nothing else to configure.

### Demo accounts

Only created by `03_demo_data.sql`. Do not load that file on a real deployment.

| Role       | Email                    | Password     |
|------------|--------------------------|--------------|
| Admin      | admin@campus.test        | Admin@123    |
| Technician | ravi.tech@campus.test    | Tech@123     |
| Technician | suresh.tech@campus.test  | Tech@123     |
| Student    | divya@campus.test        | Student@123  |
| Student    | karthik@campus.test      | Student@123  |

## Running with Docker

If you have Docker installed you can skip the Python, Node and PostgreSQL setup:

```bash
docker compose up --build
```

Open http://localhost:8080 and log in with the demo accounts above. The compose file starts
PostgreSQL (loading the schema, seed and demo data the first time), the Flask API in gunicorn, and
the React build behind nginx, which forwards `/api` to the backend. Set `JWT_SECRET` and
`DB_PASSWORD` in a `.env` file next to `docker-compose.yml` to override the dev defaults.

To start with a fresh database: `docker compose down -v` and bring it up again.

**Docker Hub.** The `docker` job in `.github/workflows/ci.yml` builds both images and pushes them
to Docker Hub on every push to `main`. Add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` (an access token
from Docker Hub account settings) under the repo's Settings, Secrets and variables, Actions. To push by hand:

```bash
docker login
docker build -t YOUR_USER/campus-ticketing-backend ./backend && docker push YOUR_USER/campus-ticketing-backend
docker build -t YOUR_USER/campus-ticketing-frontend ./frontend && docker push YOUR_USER/campus-ticketing-frontend
```

## How it works

**Roles.** One `users` table, with `role_id` pointing at `roles` (Student / Technician / Admin).
Public sign-up always creates a Student whatever the request says; admins create technicians and
other admins from the Users page.

**Ticket lifecycle.** Open → Assigned → Resolved → Closed, plus Escalated.

1. A student raises a ticket (they can pick Low, Medium or High).
2. An admin assigns it. The technician dropdown is sorted by trade match, block match, then current
   workload. Assigning is one transaction: old assignment retired, new one inserted, status set,
   notifications created, all committed together or not at all.
3. The technician marks it resolved; the student is notified and asked for a rating.
4. The rating closes the ticket. Admins can also close a ticket directly (this is the "delete":
   rows are never removed, so history survives).

**Auto-escalation.** `priority_levels.escalation_days` says how long a ticket may stay Open
(Low 5 days, Medium 3, High 2, Critical 1). A trigger only fires when a row changes, so the work is
split in two:

- `escalate_overdue_tickets()` finds Open tickets past their limit, sets them to `Escalated` and bumps
  the priority one level. The Flask app runs it every `ESCALATION_INTERVAL_MINUTES` (default 10),
  and admins can run it from the Reports page.
- `trg_auto_escalate` fires on that status change and notifies the reporter, the technician (if any)
  and all admins. `trg_log_status` writes every status change to `status_history`, recording who did it.

**Database objects**

| Object | What it is |
|---|---|
| 10 tables | roles, users, categories, locations, priority_levels, tickets, ticket_assignments, status_history, feedback, notifications |
| `vw_ticket_summary` | tickets joined with reporter, category, location, priority, current technician, rating; behind every dashboard |
| `sp_resolution_report(technician_id)` | tickets handled, open load, average hours to resolve and average rating per technician (NULL = everyone). A function rather than a `PROCEDURE`, because Postgres procedures can't return rows. |
| `trg_ticket_timestamps`, `trg_log_status`, `trg_auto_escalate` | timestamps, history log, escalation notices |
| Indexes | on `tickets(status)`, `tickets(category_id)`, `tickets(location_id)`, `ticket_assignments(technician_id, ticket_id)`, plus a partial unique index allowing one current assignment per ticket |

Schema is in 3NF; escalation rules live in `priority_levels` instead of being copied onto tickets.

ER diagram: [docs/er-diagram.md](docs/er-diagram.md).

## Security

- Passwords are hashed with bcrypt (cost 12). Plain text is never stored or logged.
- All queries go through SQLAlchemy bound parameters. The few raw `text()` queries use named
  parameters, and the only things interpolated into SQL (sort column, filter columns) come from
  fixed whitelists.
- JWT secret and database URL come from environment variables (`.env`, git-ignored).
- Every endpoint checks the role server-side; a student asking for another student's ticket gets a 404.
- Tokens expire after 8 hours. Logout drops the token client-side (tokens are stateless).

## API

All routes are under `/api` and need `Authorization: Bearer <token>` except sign-up and login.

| Method & path | Who | Does |
|---|---|---|
| POST `/auth/signup`, `/auth/login` | anyone | Returns token + user |
| GET `/auth/me`, POST `/auth/logout` | any | |
| GET `/lookups` | any | Categories, locations, priorities |
| POST `/tickets` | Student | Raise a ticket |
| GET `/tickets/mine` | any | Tickets I raised |
| GET `/tickets/assigned` | Technician | Tickets assigned to me |
| GET `/tickets` | Admin | All tickets. List routes take `q`, `status`, `category_id`, `priority_id`, `sort`, `page`, `per_page` |
| GET `/tickets/:id` | reporter, assignee, admin | Detail + history + feedback |
| PATCH `/tickets/:id` | Student (own, unassigned: edit) · Technician (own: resolve) · Admin | |
| DELETE `/tickets/:id` | Admin | Soft delete (sets Closed) |
| GET `/technicians?ticket_id=` | Admin | Technicians ranked for that ticket |
| POST `/tickets/:id/assign` | Admin | `{technician_id}` |
| POST `/tickets/:id/feedback` | Student (own, Resolved) | `{rating, comments}` |
| GET `/reports/summary`, `/reports/technicians` | Admin | Analytics |
| GET `/reports/me` | Technician | My own numbers |
| POST `/reports/escalate` | Admin | Run the overdue sweep now |
| GET/POST `/users`, PATCH `/users/:id` | Admin | User management |
| GET `/notifications`, POST `/notifications/:id/read`, `/notifications/read-all` | any | |

Errors come back as `{"error": "message"}` with a sensible status code.

## Tests

The tests run against a real PostgreSQL database because the triggers and view are part of what
they check. Create an empty database with `test` in its name; it is wiped on each run.

```bash
createdb ticketing_test
cd backend
TEST_DATABASE_URL=postgresql://localhost/ticketing_test pytest -q
```

## Backup and recovery

```bash
pg_dump -Fc ticketing > backup.dump                       # backup
pg_restore --clean --if-exists -d ticketing backup.dump   # restore
```

`database/backup.sh` wraps the dump with a timestamp and keeps the last 14 files; run it from cron
for scheduled backups.

## Deploying

**Backend + database on Render**

1. Create a PostgreSQL instance and copy its internal connection URL.
2. Create a Web Service from this repo with the root directory left at the repo root.
   - Build command: `pip install -r backend/requirements.txt`
   - Start command: `cd backend && gunicorn run:app`
   - Environment: `DATABASE_URL`, `JWT_SECRET`, `FRONTEND_ORIGIN` (your Vercel URL), optionally `ESCALATION_INTERVAL_MINUTES`.
3. Once, from the Render shell: `cd backend && flask --app run init-db` (add `--demo` only for a demo).

**Frontend on Vercel**

Import the repo, set the root directory to `frontend`, and add `VITE_API_URL` pointing at the Render
service. `vercel.json` already rewrites all paths to `index.html` for the router.

## Git workflow

`main` is stable, `dev` is where work happens, and features go through branches and pull requests
into `dev`. GitHub Actions runs the backend tests and a frontend build on pushes and PRs to both
branches (`.github/workflows/ci.yml`).

## Not included

Payments, spare-parts inventory and a native mobile app were out of scope. The UI is
responsive, but it's a web app only.
