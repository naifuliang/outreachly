# Engineering Standards · 工程规范

This document is the single source of truth for how we build Outreachly. Every PR is held to it.

> 本文件是 Outreachly 的开发规范唯一来源,每个 PR 都按此验收。

## 1. Branching · 分支

- `main` is always releasable. Never commit directly to `main`.
- One branch per phase or feature. Naming:
  - `feat/p<N>-<slug>` — a roadmap phase (e.g. `feat/p0-scaffold`, `feat/p4-send-email`)
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

- **This is a single Claude Skill, kept deliberately small.** Reasoning (ICP, copywriting,
  classification) lives in `SKILL.md` and is done by Claude — not coded. Scripts only do
  external IO (provider APIs) and CRM (SQLite) work.
- **Python**: type hints on public functions; only dependency is `httpx` (rest is stdlib).
  Every file under `scripts/` MUST be CLI-invokable (`python scripts/<name>.py [--help|ping|run]`).
- Unified external-API access goes through `_common.request` (timeout, retry, normalized errors).
  No raw `httpx` calls scattered across scripts.
- **Optional UI** is a single static `web/index.html` (vanilla JS, no build step). No React/Vite.

## 5. Internationalization · 国际化

- The skill ships **bilingual: 中文 + English**.
- Claude replies and writes outreach in the user's language. The optional UI carries both
  locales inline (zh/en toggle) — add every new UI string to **both** in the same PR.
- **No hardcoded user-facing strings in the UI.**

## 6. Secrets · 密钥

- Never commit secrets. Keys live only in `.env` (git-ignored).
- Document every required key in `.env.example` with a comment on where to get it.

## 7. Tests · 测试

- Critical logic has tests (`tests/`, `pytest`): dedup, CRM init, env/config errors, scoring,
  status transitions.
- A phase is not "done" until its acceptance criteria pass under multi-agent verification.

## 8. Tooling note · 工具说明

- `gh` (GitHub CLI) MUST be invoked with proxy env vars stripped for this environment, e.g.
  `env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy gh ...`.
  This is scoped to the command only and never modifies global shell config.
