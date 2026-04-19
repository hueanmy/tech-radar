#!/usr/bin/env python3
"""Tech Radar — quét nhiều nguồn tech/AI và gửi noti gộp theo nhóm vào Slack.

State: ~/.tech-radar/seen.json
Usage:
  python radar.py             # quét + gửi Slack
  python radar.py --dry-run   # in terminal, không gửi
  python radar.py --init      # mark hết current là đã thấy (run đầu)
  python radar.py --reset     # xoá state
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core import Item, STATE_DIR, STATE_FILE, log
from config import load_config, load_dotenv
from sources import parse_published

SOURCE_MODULES = [
    "anthropic",
    "youtube",
    "electron",
    "apple",
    "playwright",
    "github_trending",
    "security",
]


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"seen": [], "last_run": None}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        log("⚠️  Could not parse state file, starting fresh")
        return {"seen": [], "last_run": None}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def fetch_all(cfg: dict) -> list[Item]:
    log("Fetching sources...")
    items: list[Item] = []
    for name in SOURCE_MODULES:
        source_cfg = (cfg.get("sources") or {}).get(name) or {}
        if source_cfg.get("enabled") is False:
            log(f"  ⊘ {name}: disabled")
            continue
        module = importlib.import_module(f"sources.{name}")
        items.extend(module.fetch(source_cfg))
    return items


def diff_new(items: list[Item], seen_ids: set[str]) -> list[Item]:
    new: list[Item] = []
    seen_now: set[str] = set()
    for item in items:
        if item.id in seen_ids or item.id in seen_now:
            continue
        seen_now.add(item.id)
        new.append(item)
    return new


def filter_today(items: list[Item]) -> list[Item]:
    """Keep only items whose published date == today in local timezone.

    Items without a parseable date are dropped — we can't prove they're today.
    """
    today = datetime.now().astimezone().date()
    kept: list[Item] = []
    for item in items:
        dt = parse_published(item.published)
        if dt is None:
            continue
        if dt.astimezone().date() == today:
            kept.append(item)
    return kept


def print_terminal(new_items: list[Item]) -> None:
    if not new_items:
        print("\n✨ Không có update mới.\n")
        return
    by_source: dict[str, list[Item]] = {}
    for item in new_items:
        by_source.setdefault(item.source, []).append(item)
    print(f"\n🔔 {len(new_items)} update mới:\n")
    for source in sorted(by_source):
        print(f"  {source}:")
        for item in by_source[source]:
            date = f" ({item.published})" if item.published else ""
            print(f"    • {item.title}{date}")
            print(f"      {item.url}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Tech Radar")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--init", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            log("State cleared.")
        else:
            log("No state to clear.")
        return 0

    cfg = load_config()
    state = load_state()
    seen_ids = set(state.get("seen", []))

    items = fetch_all(cfg)
    if not items:
        log("⚠️  No items fetched.")
        return 1

    new_items = diff_new(items, seen_ids)
    today_items = filter_today(new_items)
    log(f"Total: {len(items)} items, {len(new_items)} new, {len(today_items)} from today")
    new_items = today_items

    merged = list(dict.fromkeys(state.get("seen", []) + [i.id for i in items]))[-800:]
    state["seen"] = merged
    state["last_run"] = datetime.now(timezone.utc).isoformat()

    if args.init:
        save_state(state)
        log(f"✓ Initialized — {len(items)} items marked seen.")
        return 0

    if not new_items:
        save_state(state)
        log("✨ No new items.")
        return 0

    if args.dry_run:
        print_terminal(new_items)
    else:
        from notifiers.slack import format_slack_message, send_slack
        payload = format_slack_message(new_items)
        if not send_slack(payload):
            log("⚠️  Slack send failed — not updating state, will retry next run.")
            print_terminal(new_items)
            return 2

        from notifiers.video import build_video
        try:
            build_video(new_items)
        except Exception as e:
            log(f"  ✗ Video build failed: {e}")

        from notifiers.site import build_site
        try:
            build_site(new_items)
        except Exception as e:
            log(f"  ✗ Site build failed: {e}")

    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
