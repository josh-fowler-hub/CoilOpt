from coiloptimization_.config import load_config
from pathlib import Path


def test_load_config_without_heat_duty(tmp_path: Path):
    src = Path('test_case/example1/input.toml')
    s = src.read_text()
    # remove or comment heat_duty_w line
    s = '\n'.join([ln for ln in s.splitlines() if 'heat_duty_w' not in ln])
    cfg = load_config_bytes = None
    # write to temp file and load
    tmp = tmp_path / 'input.toml'
    tmp.write_text(s)
    cfg = load_config(tmp)
    assert cfg.process.heat_duty_w is None
