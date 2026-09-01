# AGENTS.md

## Project Specifications

- This repo is a personal skills collection; Python and Poetry are for local development and testing only.
- Dependency files (`pyproject.toml`, `poetry.lock`) are local-only and never published.
- Follow existing project conventions.
- Related implementation plans should be stored under `docs/plans/`.

## Git Publishing Scope

This repository publishes only deeply developed and tested skills plus their documentation. Before staging, committing, or pushing:

- The publish allowlist is `skills/`, `docs/`, `.gitignore`, `README.md`, and `LICENSE`.
- Do not stage or push generated learning outputs, `.learn-loop/` state, test outputs or fixtures, caches, virtual environments, temporary files, or any other path outside that allowlist.
- Never use `git add .` or `git add -A` for a publish; stage explicit allowlisted paths only.
- Inspect `git status --short` and `git diff --cached --name-only`; every staged path must be allowlisted, then run `git diff --cached --check` before committing.
- If a requested change needs a path outside the allowlist, stop and ask before expanding the scope.
- `AGENTS.md` and `CLAUDE.md` are existing governance files; when this rule is changed, update both together and do not stage unrelated changes to them.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
