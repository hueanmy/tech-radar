"""Static site generator — render items into HTML.

Output structure (under ~/.tech-radar/site/):
  index.html                    # today's items
  archive/YYYY-MM-DD.html       # one page per past day (last 14 days)
  data/YYYY-MM-DD.json          # raw items for that day (for re-render)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import date, datetime
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import STATE_DIR, Item, log

REPO_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = REPO_DIR / "docs"
DATA_DIR = SITE_DIR / "data"
ARCHIVE_DIR = SITE_DIR / "archive"
VIDEO_DIR = SITE_DIR / "videos"

RETENTION_DAYS = 14
AVATAR_URL = "https://github.com/hueanmy.png"
YOUTUBE_URL = os.environ.get("TECH_RADAR_YOUTUBE_URL", "https://www.youtube.com/@hueanmy")
TIKTOK_URL = os.environ.get("TECH_RADAR_TIKTOK_URL", "https://www.tiktok.com/@hueanmy")

ICONS = {
    "Events": "📅",
    "Anthropic News": "📣",
    "Engineering Blog": "🛠️",
    "Claude Code Changelog": "🚀",
    "Anthropic Courses": "🎓",
    "AI YouTube": "📺",
    "Electron": "🖥️",
    "Apple/iOS": "🍎",
    "Playwright": "🎭",
    "GitHub Trending": "📈",
    "Security": "🛡️",
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg: #09090b;
  --bg-subtle: #0c0c0f;
  --surface: #111114;
  --surface-2: #18181c;
  --surface-3: #202024;
  --border: #1f1f24;
  --border-strong: #2d2d33;
  --text: #e4e4e7;
  --text-strong: #fafafa;
  --muted: #71717a;
  --muted-2: #a1a1aa;
  --accent: #a78bfa;
  --accent-2: #818cf8;
  --accent-soft: rgba(167, 139, 250, 0.12);
  --accent-border: rgba(167, 139, 250, 0.3);
  --success: #34d399;
  --warning: #fbbf24;
  --danger: #f87171;
  --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.4);
  --glow: 0 0 40px -10px rgba(167, 139, 250, 0.25);
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px; line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-image:
    radial-gradient(ellipse 800px 400px at 50% -100px, rgba(167, 139, 250, 0.08), transparent),
    radial-gradient(ellipse 600px 300px at 100% 400px, rgba(129, 140, 248, 0.05), transparent);
  background-attachment: fixed;
}
a { color: inherit; text-decoration: none; }
::selection { background: var(--accent-soft); color: var(--text-strong); }

.layout {
  display: grid;
  grid-template-columns: 272px minmax(0, 1fr) 340px;
  min-height: 100vh;
}

/* ── Sidebar ─────────────────────────────────────────── */
aside.sidebar {
  background: var(--bg-subtle);
  border-right: 1px solid var(--border);
  padding: 24px 0 16px;
  position: sticky; top: 0; align-self: start;
  max-height: 100vh; overflow-y: auto;
  backdrop-filter: blur(8px);
}
aside.sidebar::-webkit-scrollbar { width: 4px; }
aside.sidebar::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 4px; }

aside .brand {
  padding: 0 20px 18px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}
aside .brand-logo {
  display: flex; align-items: center; gap: 10px;
}
aside .brand-logo .logo-mark {
  width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  padding: 2px; display: grid; place-items: center;
  box-shadow: var(--glow);
}
aside .brand-logo .logo-mark img {
  width: 100%; height: 100%; border-radius: 50%;
  display: block; background: var(--bg);
}
aside .brand h1 {
  margin: 0; font-size: 15px; font-weight: 600;
  letter-spacing: -0.015em; color: var(--text-strong);
}
aside .brand .tagline {
  margin: 2px 0 0; font-size: 11px; color: var(--muted);
  letter-spacing: 0.01em;
}
aside .section-label {
  padding: 0 20px 10px; font-size: 10.5px; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--muted); font-weight: 600;
}
aside ul.nav-dates {
  list-style: none; padding: 0 10px; margin: 0;
}
aside ul.nav-dates li { margin: 1px 0; }
aside ul.nav-dates li a {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; font-size: 13px; color: var(--muted-2);
  border-radius: 7px; transition: all 0.12s ease;
  font-weight: 500;
}
aside ul.nav-dates li a:hover {
  background: var(--surface-2); color: var(--text-strong);
}
aside ul.nav-dates li a.current {
  background: var(--accent-soft); color: var(--accent);
  box-shadow: inset 0 0 0 1px var(--accent-border);
}
aside ul.nav-dates li a .badge {
  background: var(--surface-2); color: var(--muted);
  font-size: 10.5px; padding: 1px 7px; border-radius: 10px;
  font-weight: 600; min-width: 24px; text-align: center;
}
aside ul.nav-dates li a.current .badge {
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: #fff;
}

.lang-dropdown {
  position: relative; display: inline-flex; align-items: center;
}
.lang-dropdown::after {
  content: "▾"; position: absolute; right: 12px; top: 50%;
  transform: translateY(-50%); pointer-events: none;
  color: var(--muted); font-size: 10px;
}
.lang-dropdown select {
  appearance: none; -webkit-appearance: none;
  background: var(--surface-2); color: var(--text);
  border: 1px solid var(--border); border-radius: 999px;
  padding: 4px 28px 4px 14px; font: inherit;
  font-size: 12px; font-weight: 600; letter-spacing: 0.05em;
  cursor: pointer; transition: all 0.12s ease;
}
.lang-dropdown select:hover {
  color: var(--text-strong); border-color: var(--accent-border);
  background: var(--accent-soft);
}
.lang-dropdown select:focus { outline: none; border-color: var(--accent); }

/* ── Main content ────────────────────────────────────── */
main.content {
  padding: 40px 48px 80px;
  max-width: 920px;
  width: 100%;
}

.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; flex-wrap: wrap; margin-bottom: 6px;
}
.page-header h2 {
  margin: 0; font-size: 30px; font-weight: 700;
  letter-spacing: -0.025em; color: var(--text-strong);
  display: flex; align-items: center; gap: 12px;
}
.page-header h2 .pulse {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.15);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.15); }
  50% { box-shadow: 0 0 0 8px rgba(52, 211, 153, 0.05); }
}
.page-header .header-meta {
  display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.page-header .meta-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px;
  background: var(--surface-2); color: var(--muted-2);
  font-size: 12px; font-weight: 500;
  border: 1px solid var(--border);
}
.subtitle {
  color: var(--muted-2); font-size: 14px;
  margin: 8px 0 28px; padding-bottom: 22px;
  border-bottom: 1px solid var(--border);
}
.subtitle strong { color: var(--text-strong); font-weight: 600; }

/* Controls */
.controls {
  margin-bottom: 20px; display: flex; gap: 8px;
}
.controls button {
  background: var(--surface); color: var(--muted-2);
  border: 1px solid var(--border); border-radius: 8px;
  padding: 7px 14px; cursor: pointer;
  font: inherit; font-size: 12.5px; font-weight: 500;
  transition: all 0.12s ease;
  display: inline-flex; align-items: center; gap: 6px;
}
.controls button:hover {
  color: var(--text-strong); border-color: var(--border-strong);
  background: var(--surface-2);
}

/* ── Right rail (video) ──────────────────────────────── */
aside.right-rail {
  padding: 40px 28px 40px 0;
  position: sticky; top: 0; align-self: start;
  max-height: 100vh; overflow: visible;
}
.video-hero {
  position: relative;
  border-radius: 18px;
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow), 0 0 60px -20px rgba(167, 139, 250, 0.3);
  display: flex; flex-direction: column;
}
.video-hero .video-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 9 / 16;
  background: #000;
}
.video-hero video {
  width: 100%; height: 100%;
  display: block; object-fit: cover;
  cursor: pointer;
}
.video-hero .video-body { padding: 16px 18px 18px; }
.video-hero .eyebrow {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 10.5px; font-weight: 600;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--accent); margin-bottom: 8px;
}
.video-hero .eyebrow::before {
  content: ""; width: 6px; height: 6px; border-radius: 50%;
  background: var(--danger);
  box-shadow: 0 0 0 4px rgba(248, 113, 113, 0.2);
  animation: pulse 2s ease-in-out infinite;
}
.video-hero h3 {
  margin: 0 0 6px; font-size: 15px; font-weight: 700;
  color: var(--text-strong); letter-spacing: -0.01em;
}
.video-hero p {
  margin: 0 0 14px; font-size: 12.5px; color: var(--muted-2); line-height: 1.5;
}
.video-hero .socials {
  display: flex; gap: 8px;
}
.video-hero .social {
  flex: 1;
  display: inline-flex; align-items: center; justify-content: center; gap: 7px;
  padding: 9px 10px; border-radius: 10px;
  font-size: 12.5px; font-weight: 600;
  background: var(--surface-2); color: var(--text);
  border: 1px solid var(--border);
  transition: all 0.15s ease;
}
.video-hero .social:hover {
  border-color: var(--border-strong);
  transform: translateY(-1px);
}
.video-hero .social .ico {
  width: 16px; height: 16px; display: grid; place-items: center;
  flex-shrink: 0;
}
.video-hero .social.youtube:hover { border-color: #ff4444; background: rgba(255, 68, 68, 0.08); color: #fff; }
.video-hero .social.youtube .ico { color: #ff4444; }
.video-hero .social.tiktok:hover { background: rgba(250, 250, 250, 0.06); border-color: var(--text); color: #fff; }

/* ── Groups ───────────────────────────────────────────── */
details.group {
  margin-bottom: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.15s ease, box-shadow 0.2s ease;
}
details.group:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow);
}
details.group[open] {
  border-color: var(--border-strong);
  background: var(--surface);
}

details.group summary {
  cursor: pointer; padding: 14px 18px;
  display: flex; gap: 12px; align-items: center;
  list-style: none; user-select: none;
  transition: background 0.12s ease;
}
details.group summary:hover { background: var(--surface-2); }
details.group summary::-webkit-details-marker { display: none; }
details.group summary::before {
  content: ""; width: 6px; height: 6px;
  border-right: 1.5px solid var(--muted);
  border-bottom: 1.5px solid var(--muted);
  transform: rotate(-45deg); margin-left: 2px;
  transition: transform 0.15s ease;
}
details.group[open] summary::before { transform: rotate(45deg); }

details.group .source-icon {
  width: 30px; height: 30px; border-radius: 8px;
  background: var(--surface-3);
  display: grid; place-items: center;
  font-size: 15px; flex-shrink: 0;
}
details.group .source-name {
  font-size: 14.5px; font-weight: 600; color: var(--text-strong);
  letter-spacing: -0.005em;
}
details.group .count {
  margin-left: auto;
  background: var(--surface-2); color: var(--muted-2);
  font-size: 11.5px; font-weight: 600;
  padding: 3px 9px; border-radius: 10px;
  border: 1px solid var(--border);
}

ul.items { list-style: none; padding: 4px 18px 14px; margin: 0; }
ul.items li {
  padding: 11px 0;
  border-top: 1px solid var(--border);
  transition: opacity 0.12s ease;
}
ul.items li:first-child { border-top: 0; }
ul.items a.title {
  color: var(--text); font-weight: 500; line-height: 1.45;
  font-size: 14px;
  display: block;
  transition: color 0.12s ease;
}
ul.items a.title:hover { color: var(--accent); }
ul.items .date {
  color: var(--muted); font-size: 11.5px; margin-top: 4px;
  display: flex; align-items: center; gap: 6px;
}
ul.items .date::before {
  content: ""; width: 3px; height: 3px; border-radius: 50%;
  background: var(--muted); display: inline-block;
}

.empty {
  color: var(--muted-2); text-align: center; padding: 100px 20px;
  font-size: 14px;
}
.empty .emoji {
  font-size: 48px; display: block; margin-bottom: 14px;
  opacity: 0.6;
}
.empty .hint { color: var(--muted); font-size: 12.5px; margin-top: 6px; }

footer.page-footer {
  color: var(--muted); font-size: 11.5px;
  margin-top: 56px; padding-top: 18px;
  border-top: 1px solid var(--border);
  display: flex; justify-content: space-between;
}
footer.page-footer a { color: var(--muted-2); }
footer.page-footer a:hover { color: var(--accent); }

/* ── Mobile ──────────────────────────────────────────── */
@media (max-width: 1200px) {
  .layout { grid-template-columns: 272px minmax(0, 1fr); }
  aside.right-rail {
    grid-column: 1 / -1; grid-row: 2;
    position: static; max-height: none;
    padding: 0 48px 24px 48px;
  }
  .video-hero { max-width: 360px; margin: 0 auto; }
}
@media (max-width: 820px) {
  .layout { grid-template-columns: 1fr; }
  aside.right-rail { padding: 0 20px 24px; grid-row: auto; }
  aside.sidebar {
    position: static; max-height: none; padding: 16px 0 14px;
    border-right: 0; border-bottom: 1px solid var(--border);
  }
  aside .brand { border-bottom: 0; padding-bottom: 12px; margin-bottom: 10px; }
  aside .section-label { padding: 0 16px 6px; }
  aside ul.nav-dates {
    display: flex; overflow-x: auto; padding: 0 12px 4px; gap: 6px;
    scrollbar-width: none;
  }
  aside ul.nav-dates::-webkit-scrollbar { display: none; }
  aside ul.nav-dates li a {
    border: 1px solid var(--border);
    padding: 6px 12px; white-space: nowrap;
  }
  aside ul.nav-dates li a.current { box-shadow: none; border-color: var(--accent-border); }
  main.content { padding: 28px 20px 60px; }
  .page-header h2 { font-size: 24px; }
  .video-hero { max-width: 100%; }
}
"""


_DAY_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
_DAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _format_day(d: date, lang: str = "vi") -> str:
    names = _DAY_EN if lang == "en" else _DAY_VI
    return f"{names[d.weekday()]} {d.day:02d}/{d.month:02d}"


def _format_vn_day(d: date) -> str:  # kept for backwards compat
    return _format_day(d, "vi")


def _i18n(vi: str, en: str, tag: str = "span") -> str:
    return (f'<{tag} class="i18n" data-vi="{escape(vi)}" '
            f'data-en="{escape(en)}">{escape(vi)}</{tag}>')


def _count_items(d: date) -> int:
    path = DATA_DIR / f"{d.isoformat()}.json"
    if not path.exists():
        return 0
    try:
        return len(json.loads(path.read_text()))
    except Exception:
        return 0


def _render_sidebar(current_day: date, today: date, past: list[date]) -> str:
    ordered = [today] + [d for d in past if d != today]
    items_html = []
    for d in ordered[:RETENTION_DAYS]:
        is_current = d == current_day
        is_today = d == today
        if current_day == today:
            # rendering docs/index.html → archive pages are under archive/
            href = "index.html" if is_today else f"archive/{d.isoformat()}.html"
        else:
            # rendering docs/archive/*.html → archive pages are siblings
            href = "../index.html" if is_today else f"{d.isoformat()}.html"
        if is_today:
            label = _i18n("Hôm nay", "Today")
        else:
            label = _i18n(_format_day(d, "vi"), _format_day(d, "en"))
        count = _count_items(d)
        badge = f'<span class="badge">{count}</span>' if count else ""
        cls = "current" if is_current else ""
        items_html.append(
            f'<li><a class="{cls}" href="{escape(href)}">{label}{badge}</a></li>'
        )
    return f"""<aside class="sidebar">
  <div class="brand">
    <div class="brand-logo">
      <div class="logo-mark"><img src="{AVATAR_URL}" alt="logo"></div>
      <div>
        <h1>Tech Radar</h1>
        <p class="tagline">{_i18n("Hằng ngày · AI · Bảo mật", "Daily · AI · Security")}</p>
      </div>
    </div>
  </div>
  <div class="section-label">
    {_i18n(f"Lịch sử · {RETENTION_DAYS} ngày", f"History · {RETENTION_DAYS} days")}
  </div>
  <ul class="nav-dates">{"".join(items_html)}</ul>
</aside>"""


def _render_video(current_day: date, today: date, item_count: int) -> str:
    video_file = VIDEO_DIR / f"{current_day.isoformat()}.mp4"
    if not video_file.exists():
        return ""
    src = f"videos/{current_day.isoformat()}.mp4" if current_day == today \
        else f"../videos/{current_day.isoformat()}.mp4"
    if current_day == today:
        label = _i18n("Tóm tắt trong 45 giây", "45-second digest", tag="h3")
        desc_vi = f"{item_count} cập nhật hôm nay — click video để bật tiếng. Xem thêm trên kênh:"
        desc_en = f"{item_count} updates today — tap video to unmute. Follow the channel for more:"
    else:
        label = _i18n("Tóm tắt 45s", "45s digest", tag="h3")
        date_vi = _format_day(current_day, "vi").lower()
        date_en = _format_day(current_day, "en").lower()
        desc_vi = f"{item_count} cập nhật {date_vi} — click video để bật tiếng. Xem thêm trên kênh:"
        desc_en = f"{item_count} updates {date_en} — tap video to unmute. Follow the channel for more:"

    eyebrow = _i18n("● Tóm tắt mỗi ngày", "● Daily digest")
    desc = _i18n(desc_vi, desc_en, tag="p")

    return f"""
<section class="video-hero">
  <div class="video-body">
    <div class="eyebrow">{eyebrow}</div>
    {label}
    {desc}
    <div class="socials">
      <a class="social youtube" href="{escape(YOUTUBE_URL)}" target="_blank" rel="noopener">
        <span class="ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2C0 8.1 0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1c.5-1.9.5-5.8.5-5.8s0-3.9-.5-5.8ZM9.6 15.6V8.4l6.2 3.6-6.2 3.6Z"/></svg></span>
        YouTube
      </a>
      <a class="social tiktok" href="{escape(TIKTOK_URL)}" target="_blank" rel="noopener">
        <span class="ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19.6 6.8a5.8 5.8 0 0 1-3.4-1.1 5.8 5.8 0 0 1-2.3-3.9h-3.7v13.1a2.6 2.6 0 1 1-2.6-2.6c.3 0 .5 0 .7.1V8.6a6.4 6.4 0 0 0-.7 0 6.4 6.4 0 1 0 6.4 6.4V8.5a9.3 9.3 0 0 0 5.4 1.7V6.5a5.5 5.5 0 0 1-.1.3Z"/></svg></span>
        TikTok
      </a>
    </div>
  </div>
  <div class="video-wrap">
    <video src="{escape(src)}" autoplay muted loop playsinline preload="metadata"
           onclick="this.muted=!this.muted"></video>
  </div>
</section>"""


LANG_JS = """
window.setLang = function(lang){
  document.documentElement.lang = lang;
  document.querySelectorAll('.i18n').forEach(function(el){
    var v = el.dataset[lang];
    if (v != null) el.textContent = v;
  });
  var sel = document.querySelector('.lang-dropdown select');
  if (sel && sel.value !== lang) sel.value = lang;
  try { localStorage.setItem('lang', lang); } catch(e){}
};
(function(){
  var saved = null;
  try { saved = localStorage.getItem('lang'); } catch(e){}
  var lang = saved || ((navigator.language || '').toLowerCase().indexOf('vi') === 0 ? 'vi' : 'en');
  window.setLang(lang);
})();
"""


def _render_page(current_day: date, today: date, past: list[date],
                 items: list[Item], title: str, subtitle: str) -> str:
    by_source: dict[str, list[Item]] = {}
    for it in items:
        by_source.setdefault(it.source, []).append(it)

    sections = []
    for source in sorted(by_source):
        icon = ICONS.get(source, "•")
        lis = []
        for it in by_source[source]:
            date_html = f'<div class="date">{escape(it.published)}</div>' if it.published else ""
            lis.append(
                f'<li><a class="title" href="{escape(it.url)}" target="_blank" rel="noopener">'
                f'{escape(it.title)}</a>{date_html}</li>'
            )
        sections.append(
            f'<details class="group" open>'
            f'<summary>'
            f'<span class="source-icon">{icon}</span>'
            f'<span class="source-name">{escape(source)}</span>'
            f'<span class="count">{len(by_source[source])}</span>'
            f'</summary>'
            f'<ul class="items">{"".join(lis)}</ul></details>'
        )

    video_block = _render_video(current_day, today, len(items))

    if sections:
        expand = _i18n("Mở tất cả", "Expand all")
        collapse = _i18n("Đóng tất cả", "Collapse all")
        controls = (
            '<div class="controls">'
            f'<button onclick="document.querySelectorAll(\'details.group\').forEach(d=>d.open=true)">{expand}</button>'
            f'<button onclick="document.querySelectorAll(\'details.group\').forEach(d=>d.open=false)">{collapse}</button>'
            '</div>'
        )
        body = controls + "".join(sections)
    else:
        body = ('<div class="empty"><span class="emoji">🌙</span>'
                f'{_i18n("Chưa có item nào trong ngày này.", "No items yet for this day.")}'
                f'<div class="hint">{_i18n("Ghé lại sau khi radar chạy tiếp.", "Check back after the next radar run.")}</div></div>')

    sidebar = _render_sidebar(current_day, today, past)
    right_rail = f'<aside class="right-rail">{video_block}</aside>' if video_block else ""

    built_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    built_label = _i18n(f"Tech Radar · build lúc {built_at}",
                        f"Tech Radar · built {built_at}")
    source_link = _i18n("nguồn ↗", "source ↗")
    live_label = _i18n(f"● Live · {datetime.now():%H:%M}",
                       f"● Live · {datetime.now():%H:%M}")

    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="cache-control" content="no-cache, must-revalidate">
<link rel="icon" type="image/png" href="{AVATAR_URL}">
<link rel="apple-touch-icon" href="{AVATAR_URL}">
<title>Tech Radar</title>
<style>{CSS}</style>
</head>
<body>
<div class="layout">
{sidebar}
<main class="content">
  <div class="page-header">
    <h2>{"<span class='pulse'></span>" if current_day == today else ""}{title}</h2>
    <div class="header-meta">
      <div class="meta-badge">{live_label}</div>
      <label class="lang-dropdown" aria-label="Language">
        <select onchange="setLang(this.value)">
          <option value="vi">🇻🇳 VI</option>
          <option value="en">🇺🇸 EN</option>
        </select>
      </label>
    </div>
  </div>
  <div class="subtitle">{subtitle}</div>
  {body}
  <footer class="page-footer">
    <span>{built_label}</span>
    <a href="https://github.com/hueanmy/tech-radar" target="_blank">{source_link}</a>
  </footer>
</main>
{right_rail}
</div>
<script>{LANG_JS}</script>
</body>
</html>"""


def _save_today_data(items: list[Item], day: date) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{day.isoformat()}.json"
    existing: list[dict] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except Exception:
            existing = []
    seen_ids = {e.get("url", "").rstrip("/") for e in existing}
    for it in items:
        if it.id not in seen_ids:
            existing.append(asdict(it))
    path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))


def _load_day(day: date) -> list[Item]:
    path = DATA_DIR / f"{day.isoformat()}.json"
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text())
        return [Item(**r) for r in raw]
    except Exception:
        return []


def _archive_days(exclude: date) -> list[date]:
    if not DATA_DIR.exists():
        return []
    days = []
    for p in DATA_DIR.glob("*.json"):
        try:
            d = date.fromisoformat(p.stem)
            if d != exclude:
                days.append(d)
        except ValueError:
            pass
    return sorted(days, reverse=True)


def _cleanup_old(today: date, past: list[date]) -> list[date]:
    """Delete data + archive + video files older than RETENTION_DAYS. Return kept past days."""
    keep = past[:RETENTION_DAYS]
    drop = past[RETENTION_DAYS:]
    for d in drop:
        (DATA_DIR / f"{d.isoformat()}.json").unlink(missing_ok=True)
        (ARCHIVE_DIR / f"{d.isoformat()}.html").unlink(missing_ok=True)
        (VIDEO_DIR / f"{d.isoformat()}.mp4").unlink(missing_ok=True)
    if drop:
        log(f"  ✓ Retention: dropped {len(drop)} day(s) older than {RETENTION_DAYS}d")
    return keep


def build_site(today_items: list[Item]) -> Path:
    today = datetime.now().astimezone().date()
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    if today_items:
        _save_today_data(today_items, today)

    past_all = _archive_days(exclude=today)
    past = _cleanup_old(today, past_all)

    # Rebuild every archive page (sidebar state changes when a new day arrives)
    for d in past:
        day_items = _load_day(d)
        if not day_items:
            continue
        title = _i18n(_format_day(d, "vi"), _format_day(d, "en"))
        subtitle = (f"<strong>{len(day_items)}</strong> "
                    f"{_i18n(f'item · {d.isoformat()}', f'items · {d.isoformat()}')}")
        html = _render_page(
            current_day=d, today=today, past=past,
            items=day_items,
            title=title,
            subtitle=subtitle,
        )
        (ARCHIVE_DIR / f"{d.isoformat()}.html").write_text(html)

    index_items = _load_day(today)
    now_hm = datetime.now().strftime("%H:%M")
    title = _i18n("Hôm nay", "Today")
    subtitle = (f"<strong>{len(index_items)}</strong> "
                f"{_i18n(f'item · {today.isoformat()} · cập nhật {now_hm}', f'items · {today.isoformat()} · updated {now_hm}')}")
    index_html = _render_page(
        current_day=today, today=today, past=past,
        items=index_items,
        title=title,
        subtitle=subtitle,
    )
    index_path = SITE_DIR / "index.html"
    index_path.write_text(index_html)

    log(f"  ✓ Site rebuilt: {index_path}")
    _git_sync()
    return index_path


def _git_sync() -> None:
    """Commit docs/ + push to GitHub Pages repo. No-op if not a git repo."""
    if os.environ.get("TECH_RADAR_NO_PUSH"):
        log("  ⊘ Git sync skipped (TECH_RADAR_NO_PUSH set)")
        return
    if not (REPO_DIR / ".git").exists():
        return
    try:
        status = subprocess.run(
            ["git", "-C", str(REPO_DIR), "status", "--porcelain", "docs"],
            capture_output=True, text=True, timeout=10,
        )
        if not status.stdout.strip():
            return
        msg = f"Site update {datetime.now():%Y-%m-%d %H:%M}"
        subprocess.run(["git", "-C", str(REPO_DIR), "add", "docs"], check=True, timeout=10)
        subprocess.run(
            ["git", "-C", str(REPO_DIR), "commit", "-m", msg],
            check=True, timeout=10, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(REPO_DIR), "push", "--quiet"],
            check=True, timeout=30, capture_output=True,
        )
        log(f"  ✓ Site pushed to GitHub Pages")
    except subprocess.CalledProcessError as e:
        log(f"  ✗ Git sync failed: {e.stderr.decode() if e.stderr else e}")
    except Exception as e:
        log(f"  ✗ Git sync error: {e}")
