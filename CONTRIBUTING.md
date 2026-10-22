# Contributing

## Branches

- `main` is stable and is what gets deployed.
- `dev` is where work comes together.
- New work goes on a short-lived branch off `dev`, named by area, for example
  `db/sample-queries`, `docs/screenshots` or `fix/login-port`.

## Workflow

1. `git checkout dev && git pull`
2. `git checkout -b <area>/<short-name>`
3. Make small commits with messages that say what changed ("Add sample SQL queries", not "update").
4. Push the branch and open a pull request into `dev`.
5. Someone else on the team reviews and merges it.
6. When `dev` is in good shape, open a pull request from `dev` into `main`.

## Before opening a pull request

- Backend: `cd backend && pytest -q` (needs `TEST_DATABASE_URL`, see the README).
- Frontend: `cd frontend && npm run build`.
- Never commit `.env` files or credentials. `.gitignore` already excludes them.
