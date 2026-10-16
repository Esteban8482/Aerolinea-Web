# Repository agent instructions

These instructions apply to the whole repository. Detailed project and workflow guidance is in
[`docs/AGENTS.md`](docs/AGENTS.md); read it before changing project code or documentation.

## Before changing files

- Read `README.md`, `REGLASCOMMITS.md`, the applicable `AGENTS.md` files, and the project
  clarifications relevant to the task.
- Check the Git root, branch, worktree, and existing implementation first. Preserve unrelated
  local changes.
- Treat the user request as the scope; setup work does not authorize implementing future user
  stories.
- A pending `P-XX` blocks only the affected behavior. Do not turn a proposal into a requirement;
  request a decision when needed and continue independent work.

## Project conventions

- Backend: Django and Django REST Framework; PostgreSQL is the integration database.
- Keep business rules in domain services, with migrations and tests for persisted behavior.
- Define `AUTH_USER_MODEL` before the first authentication migration. Keep business roles separate
  from Django staff and superuser privileges.
- Use the documented session and CSRF approach; do not add JWT or unrelated infrastructure.
- Keep secrets out of source, examples, logs, and commits. `.env.example` contains placeholders
  only.

## Verification and delivery

- Run the focused checks and tests applicable to the change. Distinguish SQLite unit checks from
  PostgreSQL integration or concurrency checks.
- Update directly related documentation and API contracts. Do not claim unrun CI, deployment, or
  security requirements as verified.
- Do not commit, push, or open a pull request unless explicitly asked.
