# Tech Radar

Quét nhiều nguồn tech/AI → gom theo nhóm → gửi Slack.

## Cấu trúc

```
tech-radar/
├── radar.py                 # entry point
├── core.py                  # Item dataclass, paths, log
├── config.py                # load config.yaml + .env
├── config.yaml              # bật/tắt source, keyword filter
├── .env                     # local overrides (secrets in ~/.zshrc)
├── sources/
│   ├── __init__.py          # http_get, parse_feed, filter_by_keywords
│   ├── anthropic.py         # News, Engineering, Changelog, Courses, Events
│   ├── youtube.py           # AI YouTube channels (RSS)
│   ├── electron.py          # Electron blog + releases
│   ├── apple.py             # Apple Dev News + Swift blog
│   ├── playwright.py        # Playwright releases
│   └── github_trending.py   # GitHub trending (community RSS)
└── notifiers/
    └── slack.py             # webhook / bot DM
```

## Nguồn hiện tại

| Group                 | Source(s)                                               |
| --------------------- | ------------------------------------------------------- |
| Anthropic News        | RSS Olshansk                                            |
| Engineering Blog      | RSS Olshansk                                            |
| Claude Code Changelog | RSS Olshansk                                            |
| Anthropic Courses     | `anthropics/courses` commits.atom                       |
| Events                | scrape anthropic.com/events                             |
| AI YouTube            | Fireship, AI Explained, Matt Wolfe, Matthew Berman, 2MP |
| Electron              | blog RSS + GitHub releases                              |
| Apple/iOS             | Dev News RSS + Swift.org blog                           |
| Playwright            | GitHub releases                                         |
| GitHub Trending       | mshibanami/GitHubTrendingRSS (lọc keyword AI)           |

## Chạy

```bash
python3 radar.py --dry-run    # preview, không gửi
python3 radar.py --init       # mark all current = seen (lần đầu)
python3 radar.py              # gửi Slack các item mới
python3 radar.py --reset      # xoá state
```

## Config

Mở `config.yaml` để:
- Tắt nguồn không cần: `sources.<name>.enabled: false`
- Đổi YouTube channels: sửa `sources.youtube.channels`
- Filter keyword: `sources.<name>.keywords: [ai, llm, ...]`
- GitHub trending language: `sources.github_trending.languages: [typescript, rust]`

## Secrets

Đang đặt trong `~/.zshrc` với prefix `CLAUDE_WATCHER_SLACK_*`:
- `CLAUDE_WATCHER_SLACK_WEBHOOK_URL`
- `CLAUDE_WATCHER_SLACK_BOT_TOKEN`
- `CLAUDE_WATCHER_SLACK_USER_ID`
- `CLAUDE_WATCHER_SLACK_CHANNEL`

`.env` chỉ dùng khi muốn override — shell env luôn thắng.

## State

`~/.tech-radar/seen.json` — list URL đã báo. Log ở `~/.tech-radar/radar.log`.

## Dependencies

```bash
pip3 install requests beautifulsoup4 lxml
# tuỳ chọn:
pip3 install pyyaml   # nếu thiếu, có fallback parser tối giản
```
