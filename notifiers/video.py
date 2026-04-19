"""Daily TikTok-style video generator.

Renders today's items into a vertical 1080x1920 page, records a ~30s scroll
video via Playwright, converts to mp4 via ffmpeg, and writes a matching
caption file. Output lands in ~/tech-radar/videos/ by default — pick up the
mp4 + txt and upload manually.

Skips silently if playwright or ffmpeg are missing.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import Item, log

REPO_DIR = Path(__file__).resolve().parent.parent
SITE_VIDEO_DIR = REPO_DIR / "docs" / "videos"

OUTPUT_DIR = Path(
    os.environ.get("TECH_RADAR_VIDEO_DIR") or (Path.home() / "tech-radar" / "videos")
).expanduser()

W, H = 1080, 1920
DURATION_MS = 45_000
HOLD_MS = 4_000                       # hold at hook + outro
SCROLL_MS = DURATION_MS - 2 * HOLD_MS  # 37s of scroll — slower, easier to read
MAX_CARDS = 10                         # keep scroll comfortable

SITE_URL = os.environ.get("TECH_RADAR_SITE_URL") or "hueanmy.github.io/tech-radar"

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

TAGS_BY_SOURCE = {
    "Security": ["cybersecurity", "infosec"],
    "Anthropic News": ["claude", "anthropic"],
    "Engineering Blog": ["claude", "anthropic"],
    "Claude Code Changelog": ["claudecode", "ai"],
    "Anthropic Courses": ["ai", "learning"],
    "AI YouTube": ["ai", "llm"],
    "Electron": ["electron", "desktop"],
    "Apple/iOS": ["ios", "swift"],
    "Playwright": ["playwright", "testing"],
    "GitHub Trending": ["opensource", "github"],
    "Events": ["anthropic", "events"],
}
UNIVERSAL_TAGS = ["tech", "coding", "devlife", "fyp", "techradar"]


def _group(items: list[Item]) -> dict[str, list[Item]]:
    by: dict[str, list[Item]] = {}
    for it in items:
        by.setdefault(it.source, []).append(it)
    return by


def _pick_cards(items: list[Item]) -> list[Item]:
    """Spread picks across sources so the video doesn't drown in one category."""
    by = _group(items)
    rounds: list[Item] = []
    sources = sorted(by.keys())
    while len(rounds) < MAX_CARDS and any(by[s] for s in sources):
        for s in sources:
            if by[s] and len(rounds) < MAX_CARDS:
                rounds.append(by[s].pop(0))
    return rounds


def _hook_title(total: int) -> str:
    if total >= 10:
        return f"{total} TECH UPDATES\nHÔM NAY 🔥"
    if total >= 5:
        return f"{total} UPDATE CÔNG NGHỆ\nMỚI HÔM NAY"
    return f"HÔM NAY CÓ {total}\nTIN CÔNG NGHỆ"


def _render_html(items: list[Item]) -> str:
    by = _group(items)
    total = len(items)
    cards = _pick_cards(items)
    overflow = total - len(cards)

    chips = "".join(
        f'<span class="chip">{ICONS.get(s, "•")} {escape(s)} · {len(by[s])}</span>'
        for s in sorted(by)
    )

    card_html = []
    for i, it in enumerate(cards, 1):
        icon = ICONS.get(it.source, "•")
        card_html.append(f"""
        <article class="card">
          <header>
            <span class="badge">{icon} {escape(it.source)}</span>
            <span class="idx">#{i:02d}</span>
          </header>
          <h3>{escape(it.title)}</h3>
        </article>""")

    if overflow > 0:
        card_html.append(f"""
        <article class="card card--more">
          <h3>+{overflow} tin khác 👀</h3>
          <p class="small">xem full trên site ↓</p>
        </article>""")

    date_str = datetime.now().strftime("%d/%m/%Y")

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {W}px; background: #09090b; color: #fafafa;
    font-family: -apple-system, 'SF Pro Display', BlinkMacSystemFont, 'Segoe UI', sans-serif;
    overflow-x: hidden; }}
  body {{
    background-image:
      radial-gradient(ellipse 900px 500px at 50% 0%, rgba(167, 139, 250, 0.25), transparent),
      radial-gradient(ellipse 700px 400px at 0% 60%, rgba(99, 102, 241, 0.15), transparent),
      radial-gradient(ellipse 700px 400px at 100% 100%, rgba(236, 72, 153, 0.12), transparent);
  }}

  .screen {{ width: {W}px; min-height: {H}px; padding: 120px 72px;
    display: flex; flex-direction: column; justify-content: center; }}

  /* ── Hook ────────────────────────────── */
  .hook {{ text-align: center; }}
  .hook .date {{
    font-size: 32px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #a78bfa; margin-bottom: 48px;
  }}
  .hook h1 {{
    font-size: 140px; font-weight: 900; line-height: 0.95;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #fafafa 0%, #a78bfa 50%, #818cf8 100%);
    -webkit-background-clip: text; background-clip: text;
    color: transparent; white-space: pre-line;
    text-shadow: 0 0 80px rgba(167, 139, 250, 0.3);
  }}
  .hook .chips {{
    margin-top: 56px; display: flex; flex-wrap: wrap; gap: 12px;
    justify-content: center;
  }}
  .chip {{
    padding: 14px 24px; font-size: 28px; font-weight: 600;
    background: rgba(167, 139, 250, 0.12);
    border: 1px solid rgba(167, 139, 250, 0.4);
    border-radius: 999px; color: #e4e4e7;
  }}

  /* ── Cards ───────────────────────────── */
  .cards {{ padding: 100px 64px; display: flex; flex-direction: column; gap: 40px; }}
  .card {{
    background: linear-gradient(180deg, #18181c 0%, #111114 100%);
    border: 1px solid #2d2d33;
    border-radius: 32px; padding: 48px 52px;
    box-shadow: 0 30px 80px -20px rgba(0,0,0,0.6);
    min-height: 400px; display: flex; flex-direction: column;
  }}
  .card header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 32px;
  }}
  .card .badge {{
    padding: 10px 22px; border-radius: 12px;
    background: rgba(167, 139, 250, 0.15);
    color: #c4b5fd; font-size: 30px; font-weight: 700;
    letter-spacing: -0.005em;
  }}
  .card .idx {{
    font-size: 28px; font-weight: 700; color: #52525b;
    letter-spacing: 0.05em;
  }}
  .card h3 {{
    font-size: 64px; font-weight: 800; line-height: 1.1;
    letter-spacing: -0.02em; color: #fafafa;
    display: -webkit-box; -webkit-line-clamp: 5;
    -webkit-box-orient: vertical; overflow: hidden;
  }}
  .card--more {{ text-align: center; justify-content: center; align-items: center;
    background: linear-gradient(135deg, rgba(167, 139, 250, 0.2), rgba(129, 140, 248, 0.15));
    border-color: rgba(167, 139, 250, 0.5); }}
  .card--more h3 {{ font-size: 88px; -webkit-line-clamp: 2; }}
  .small {{ margin-top: 20px; color: #a1a1aa; font-size: 30px; }}

  /* ── Outro ───────────────────────────── */
  .outro {{ text-align: center; padding-top: 160px; padding-bottom: 200px; }}
  .outro .hook-line {{
    font-size: 68px; font-weight: 900; line-height: 1.1;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #fafafa 0%, #a78bfa 100%);
    -webkit-background-clip: text; background-clip: text;
    color: transparent; margin-bottom: 48px;
  }}
  .outro .cta-label {{
    font-size: 32px; font-weight: 600; color: #a78bfa;
    letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 24px;
  }}
  .outro .cta-url {{
    font-size: 58px; font-weight: 800; letter-spacing: -0.015em;
    color: #fafafa; line-height: 1.15;
    padding: 28px 40px; border-radius: 24px;
    background: rgba(167, 139, 250, 0.12);
    border: 2px solid rgba(167, 139, 250, 0.5);
    display: inline-block;
  }}
  .outro .follow {{
    margin-top: 56px; font-size: 38px; font-weight: 600;
    color: #e4e4e7; letter-spacing: -0.005em;
  }}
  .outro .arrow {{ font-size: 96px; margin-top: 32px; animation: bounce 1.2s infinite; }}
  @keyframes bounce {{ 0%,100% {{transform: translateY(0);}} 50% {{transform: translateY(-20px);}} }}

</style></head>
<body>
  <section class="screen hook">
    <div>
      <div class="date">{escape(date_str)}</div>
      <h1>{_hook_title(total)}</h1>
      <div class="chips">{chips}</div>
    </div>
  </section>
  <section class="cards">
    {''.join(card_html)}
  </section>
  <section class="screen outro">
    <div>
      <div class="hook-line">Cập nhật tin công nghệ<br>mỗi ngày ⚡</div>
      <div class="cta-label">Truy cập ngay</div>
      <div class="cta-url">{escape(SITE_URL)}</div>
      <div class="follow">AI mạnh quá, theo dõi để không bỏ lỡ hàng ngày nha 🔥</div>
      <div class="arrow">⬇️</div>
    </div>
  </section>
</body></html>"""


def _build_caption(items: list[Item]) -> str:
    by = _group(items)
    total = len(items)
    date_str = datetime.now().strftime("%Y-%m-%d")

    lines = [f"🔥 {total} update công nghệ hôm nay · {date_str}", ""]
    for source in sorted(by):
        icon = ICONS.get(source, "•")
        lines.append(f"{icon} {source} ({len(by[source])})")
        for it in by[source][:2]:
            title = it.title if len(it.title) <= 80 else it.title[:77] + "…"
            lines.append(f"  • {title}")
    lines += ["", f"📖 Full list: {SITE_URL}", ""]

    tags = list(UNIVERSAL_TAGS)
    for s in by:
        tags.extend(TAGS_BY_SOURCE.get(s, []))
    seen = set()
    ordered = [t for t in tags if not (t in seen or seen.add(t))]
    lines.append(" ".join(f"#{t}" for t in ordered))

    return "\n".join(lines)


_SCROLL_SCRIPT = f"""
(() => {{
  const HOLD = {HOLD_MS};
  const SCROLL = {SCROLL_MS};
  const DURATION = {DURATION_MS};
  const distance = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
  const ease = t => t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2) / 2;
  const start = performance.now();
  function frame(now) {{
    const t = now - start;
    if (t < HOLD) window.scrollTo(0, 0);
    else if (t < HOLD + SCROLL) {{
      const p = ease((t - HOLD) / SCROLL);
      window.scrollTo(0, distance * p);
    }} else {{
      window.scrollTo(0, distance);
    }}
    if (t < DURATION) requestAnimationFrame(frame);
  }}
  requestAnimationFrame(frame);
}})();
"""


def _record(html: str, out_mp4: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("  ⊘ Video: playwright not installed (pip install playwright && playwright install chromium)")
        return False

    if not shutil.which("ffmpeg"):
        log("  ⊘ Video: ffmpeg not found (brew install ffmpeg)")
        return False

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        html_path = tdp / "story.html"
        html_path.write_text(html, encoding="utf-8")
        video_dir = tdp / "rec"
        video_dir.mkdir()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            context = browser.new_context(
                viewport={"width": W, "height": H},
                device_scale_factor=1,
                record_video_dir=str(video_dir),
                record_video_size={"width": W, "height": H},
            )
            page = context.new_page()
            page.goto(html_path.as_uri())
            page.wait_for_load_state("networkidle")
            page.evaluate(_SCROLL_SCRIPT)
            page.wait_for_timeout(DURATION_MS + 400)
            context.close()
            browser.close()

        webm_files = list(video_dir.glob("*.webm"))
        if not webm_files:
            log("  ✗ Video: no recording produced")
            return False
        webm = webm_files[0]

        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(webm),
            "-t", f"{DURATION_MS/1000:.2f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            log(f"  ✗ ffmpeg failed: {res.stderr.strip()[:400]}")
            return False

    return True


def build_video(items: list[Item]) -> Path | None:
    if not items:
        return None

    day = datetime.now().strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mp4_path = OUTPUT_DIR / f"{day}.mp4"
    txt_path = OUTPUT_DIR / f"{day}.txt"

    html = _render_html(items)
    if not _record(html, mp4_path):
        return None

    txt_path.write_text(_build_caption(items), encoding="utf-8")

    SITE_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    site_mp4 = SITE_VIDEO_DIR / f"{day}.mp4"
    shutil.copyfile(mp4_path, site_mp4)

    log(f"  ✓ Video: {mp4_path}")
    log(f"  ✓ Caption: {txt_path}")
    log(f"  ✓ Site video: {site_mp4}")
    return mp4_path
