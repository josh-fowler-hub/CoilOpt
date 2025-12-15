from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def configure_logging(out_dir: Optional[Path] = None, level: int = logging.INFO, jsonl: bool = True, file: Optional[Path] = None) -> Dict[str, Any]:
    """Configure root logging handlers.

    - Console handler (human readable)
    - Optional file handler (plain text)
    - Optional JSON-lines file for structured events
    Returns a dict with paths created.
    """
    out = {}
    logger = logging.getLogger()
    logger.setLevel(level)

    # simple console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)

    if out_dir is None and file is None:
        return out

    if out_dir is None:
        out_dir = file.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out["out_dir"] = str(out_dir)

    if file is not None:
        fh = logging.FileHandler(file)
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(fh)
        out["log_file"] = str(file)

    if jsonl:
        jsonl_path = out_dir / f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
        # create an empty file if not exists
        jsonl_path.write_text("")
        out["jsonl"] = str(jsonl_path)

    return out


def write_json_event(path: Path, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
    payload = payload or {}
    entry = {"timestamp": _iso_ts(), "event": event, "payload": payload}
    with path.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name)
