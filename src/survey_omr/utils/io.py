from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


def ensure_dir(path: Path) -> Path:
    """Create a directory (and parents) if missing, then return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def file_sha1(path: Path, chunk_size: int = 2**20) -> str:
    """Compute SHA1 hash for a file."""
    sha = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file as dict."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write YAML with UTF-8 encoding."""
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def dump_json(path: Path, data: Any, indent: int = 2) -> None:
    """Write JSON to file."""
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append a JSON line entry."""
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
