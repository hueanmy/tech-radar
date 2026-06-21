"""GitHub Trending — dùng community RSS của mshibanami/GitHubTrendingRSS.

Hỗ trợ filter theo language (config.yaml: `languages`) và keyword (`keywords`).
Nếu ANTHROPIC_API_KEY có + analyze: true → phân tích lý do trending bằng Claude.
"""
from __future__ import annotations

import json
import os
import re

from core import Item, log
from sources import fetch_feed, filter_by_keywords

_BASE = "https://mshibanami.github.io/GitHubTrendingRSS/daily"


def fetch(cfg: dict) -> list[Item]:
    langs = cfg.get("languages") or ["all"]
    items: list[Item] = []
    for lang in langs:
        url = f"{_BASE}/{lang}.xml"
        items.extend(fetch_feed("GitHub Trending", lang, url))
    items = filter_by_keywords(items, cfg.get("keywords", []))
    if cfg.get("analyze", True):
        items = _analyze(items)
    return items


def _analyze(items: list[Item]) -> list[Item]:
    """Dùng Claude để giải thích tại sao mỗi repo đang trending (1-2 câu tiếng Việt)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or not items:
        return items
    try:
        import anthropic
    except ImportError:
        log("  ⚠ GitHub Trending: cần `pip install anthropic` để phân tích")
        return items

    try:
        client = anthropic.Anthropic(api_key=api_key)
        repos = "\n".join(
            f"{i + 1}. {it.title} — {it.summary}" for i, it in enumerate(items)
        )
        prompt = (
            "Dưới đây là các GitHub repo đang trending hôm nay. "
            "Với mỗi repo, viết 1-2 câu tiếng Việt ngắn gọn: repo làm gì và tại sao developer quan tâm. "
            "Trả lời JSON array, không giải thích thêm: "
            '[{"index": 1, "why": "..."}, ...]\n\n'
            f"{repos}"
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown code fence if present
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            raw = match.group(0)
        analyses = json.loads(raw)
        idx_map = {a["index"]: a["why"] for a in analyses if "index" in a and "why" in a}
        for i, it in enumerate(items):
            why = idx_map.get(i + 1)
            if why:
                it.summary = why
        log(f"  ✓ GitHub Trending: đã phân tích {len(idx_map)}/{len(items)} repos")
    except Exception as e:
        log(f"  ✗ GitHub Trending analyze: {e}")
    return items
