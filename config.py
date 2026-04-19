"""Config loader — parses config.yaml + .env."""
from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent
CONFIG_FILE = _PROJECT_ROOT / "config.yaml"
DOTENV_FILE = _PROJECT_ROOT / ".env"


def _parse_simple_yaml(text: str) -> dict:
    """Fallback parser nếu PyYAML chưa cài — chỉ đủ cho config.yaml."""
    import re

    def parse_value(raw: str):
        raw = raw.strip()
        if raw.lower() in ("true", "yes"): return True
        if raw.lower() in ("false", "no"): return False
        if raw.lower() in ("null", "~", ""): return None
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            if not inner: return []
            return [parse_value(x) for x in re.split(r",\s*", inner)]
        if raw.startswith(("'", '"')) and raw.endswith(raw[0]):
            return raw[1:-1]
        try: return int(raw)
        except ValueError: pass
        try: return float(raw)
        except ValueError: pass
        return raw

    root: dict = {}
    stack: list[tuple[int, dict | list]] = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        line = raw_line.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            item_str = line[2:].strip()
            if ":" in item_str and not item_str.startswith(("'", '"')):
                k, _, v = item_str.partition(":")
                d = {k.strip(): parse_value(v)}
                if isinstance(parent, list):
                    parent.append(d)
                stack.append((indent, d))
            else:
                if isinstance(parent, list):
                    parent.append(parse_value(item_str))
        elif ":" in line:
            k, _, v = line.partition(":")
            key = k.strip()
            v = v.strip()
            if not v:
                new: dict | list = {}
                if isinstance(parent, dict): parent[key] = new
                stack.append((indent, new))
            else:
                val = parse_value(v)
                if isinstance(parent, dict): parent[key] = val
    return root


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    text = CONFIG_FILE.read_text()
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        return _parse_simple_yaml(text)


def load_dotenv() -> None:
    """Nạp .env nếu có — giá trị trong shell env có priority cao hơn."""
    if not DOTENV_FILE.exists():
        return
    for line in DOTENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
