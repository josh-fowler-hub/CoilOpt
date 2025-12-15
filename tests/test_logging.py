from pathlib import Path
import logging

from coiloptimization_ import logging as coil_logging


def test_configure_and_write_json_event(tmp_path: Path):
    out = coil_logging.configure_logging(out_dir=tmp_path, level=logging.DEBUG, jsonl=True)
    assert "out_dir" in out
    if "jsonl" in out:
        jsonl = Path(out["jsonl"])
        assert jsonl.exists()
        coil_logging.write_json_event(jsonl, "test_event", {"foo": "bar"})
        content = jsonl.read_text()
        assert "test_event" in content
