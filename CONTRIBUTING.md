# Engineering Standards · 工程规范

This document is the single source of truth for how we build Outreachly. Every PR is held to it.

> 本文件是 Outreachly 的开发规范唯一来源,每个 PR 都按此验收。

## 1. Branching · 分支

- `main` is always releasable. Never commit directly to `main`.
- One branch per phase or feature. Naming:
  - `feat/p<N>-<slug>` — a roadmap phase (e.g. `feat/p0-scaffold`, `feat/p3-maps-discovery`)
  - `feat/<slug>` — a feature
  - `fix/<slug>`, `chore/<slug>`, `docs/<slug>`, `test/<slug>`
- Rebase or merge `main` in before opening a PR; keep branches short-lived.

## 2. Commits · 提交

[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

type: feat | fix | chore | docs | test | refactor | perf | ci
```

Examples: `feat(icp): generate ICP from product description`, `fix(crm): dedup by email`.
Keep subjects imperative and < 72 chars. Reference issues/criteria in the body.

## 3. Pull Requests · 合并请求

- **One PR per phase** (or per feature within a phase).
- PR description MUST list the acceptance criteria from `docs/PLAN.md` for that phase, with a
  checkbox per item and how it was verified.
- **Multi-agent acceptance is mandatory before merge.** Each acceptance criterion is checked by
  an independent verification agent; results are posted to the PR. A PR merges only when all
  criteria pass (or the human approves a documented exception).
- Human-in-the-loop: the repo owner makes the final merge call and any flagged product decisions.

## 4. Code style · 代码风格

- **Backend (Python)**: `ruff` (lint) + `black` (format), type hints on public functions.
  Every script under `backend/app/scripts/` MUST be CLI-invokable (`python -m app.scripts.<name>`).
- **Frontend (TypeScript/React)**: `eslint` + `prettier`. Function components + hooks.
- Unified external-API access goes through `app/core/api_client.py` (timeout, retry, rate-limit,
  normalized errors). No raw `requests`/`httpx` calls scattered in scripts.

## 5. Internationalization · 国际化

- The product ships **bilingual: 中文 + English**.
- **No hardcoded user-facing strings.** Frontend strings live in `frontend/src/i18n/{zh,en}`.
  Backend user-facing messages/errors go through `app/i18n`.
- Every new user-facing string is added to **both** locales in the same PR.

## 6. Secrets · 密钥

- Never commit secrets. Keys live only in `.env` (git-ignored).
- Document every required key in `.env.example` with a comment on where to get it.

## 7. Tests · 测试

- Critical logic has tests (`backend/tests/`, `pytest`): dedup, state machine, ICP scoring,
  email-verification filtering, API-client retry/error normalization.
- A phase is not "done" until its acceptance criteria pass under multi-agent verification.

## 8. Tooling note · 工具说明

- `gh` (GitHub CLI) MUST be invoked with proxy env vars stripped for this environment, e.g.
  `env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy gh ...`.
  This is scoped to the command only and never modifies global shell config.
