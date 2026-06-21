"""Tiny backend i18n helper for user-facing messages (中文 / English).

Backend strings shown to users (API responses, CLI output) go through `t()`. Add every new
key to BOTH locales (see CONTRIBUTING.md §5).
"""

from __future__ import annotations

from app.core.config import settings

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "db.initialized": "Database initialized at {path} ({tables} tables).",
        "ping.ok": "{provider}: connected.",
        "ping.missing_key": "{provider}: missing key — {detail}",
        "ping.failed": "{provider}: connection failed — {detail}",
        "icp.invalid": "Invalid ICP: {detail}",
        "lead.deduped": "Duplicate lead skipped (key: {key}).",
    },
    "zh": {
        "db.initialized": "数据库已初始化:{path}(共 {tables} 张表)。",
        "ping.ok": "{provider}:连接成功。",
        "ping.missing_key": "{provider}:缺少密钥 —— {detail}",
        "ping.failed": "{provider}:连接失败 —— {detail}",
        "icp.invalid": "画像不合法:{detail}",
        "lead.deduped": "跳过重复线索(去重键:{key})。",
    },
}

SUPPORTED_LOCALES = tuple(MESSAGES.keys())


def t(key: str, *, locale: str | None = None, **kwargs) -> str:
    """Translate `key` into `locale` (defaults to settings.default_locale), formatting kwargs."""
    loc = (locale or settings.default_locale or "en").lower()
    if loc not in MESSAGES:
        loc = "en"
    template = MESSAGES[loc].get(key) or MESSAGES["en"].get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
