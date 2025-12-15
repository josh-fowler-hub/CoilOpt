from pathlib import Path

import numpy as np
import json

from coiloptimization_.optimize import Optimizer
from coiloptimization_ import config as config_module


def test_multi_start_writes_checkpoint(tmp_path: Path):
    cfg = config_module.load_config(Path('docs/example_input.toml'))
    opt = Optimizer(cfg)
    # simple bounds matching earlier run_config default x vector: D_o, t, D_c, p, N
    db = cfg.design_bounds
    bounds = [
        (db.min_tube_od_m, db.max_tube_od_m),
        (db.min_wall_thickness_m, db.max_wall_thickness_m),
        (db.min_coil_diameter_m, db.max_coil_diameter_m),
        (db.min_pitch_m, db.max_pitch_m),
        (db.min_turns, min(db.max_turns, db.min_turns + 10)),
    ]
    out = opt.run_multi_start(bounds, n_starts=2, out_dir=tmp_path, seed=42)
    # checkpoint should exist
    cp = Path(out['checkpoint'])
    assert cp.exists()
    data = cp.read_text()
    assert 'completed' in data
    # events file should exist
    ev = Path(out['events'])
    assert ev.exists()
    txt = ev.read_text()
    assert 'local_solve_complete' in txt


def test_multi_start_no_json(tmp_path: Path):
    cfg = config_module.load_config(Path('docs/example_input.toml'))
    opt = Optimizer(cfg)
    db = cfg.design_bounds
    bounds = [
        (db.min_tube_od_m, db.max_tube_od_m),
        (db.min_wall_thickness_m, db.max_wall_thickness_m),
        (db.min_coil_diameter_m, db.max_coil_diameter_m),
        (db.min_pitch_m, db.max_pitch_m),
        (db.min_turns, min(db.max_turns, db.min_turns + 10)),
    ]
    out = opt.run_multi_start(bounds, n_starts=2, out_dir=tmp_path, seed=42, jsonl=False)
    ev = out['events']
    assert not ev  # empty string when jsonl disabled


def test_resume_continues_remaining(tmp_path: Path):
    cfg = config_module.load_config(Path('docs/example_input.toml'))
    opt = Optimizer(cfg)
    db = cfg.design_bounds
    bounds = [
        (db.min_tube_od_m, db.max_tube_od_m),
        (db.min_wall_thickness_m, db.max_wall_thickness_m),
        (db.min_coil_diameter_m, db.max_coil_diameter_m),
        (db.min_pitch_m, db.max_pitch_m),
        (db.min_turns, min(db.max_turns, db.min_turns + 10)),
    ]
    # pre-generate planned_starts using same RNG logic
    rng = np.random.RandomState(42)
    planned = []
    for _ in range(3):
        x0 = np.array([rng.uniform(a, b) for (a, b) in bounds], dtype=float)
        x0[-1] = int(round(x0[-1]))
        planned.append(x0.tolist())

    checkpoint = tmp_path / 'checkpoint.json'
    cp = {'timestamp': 'now', 'planned_starts': planned, 'completed': 1, 'starts': [ {'index': 0, 'x': planned[0], 'objective': 100.0, 'success': True} ] }
    checkpoint.write_text(json.dumps(cp))

    out = opt.run_multi_start(bounds, n_starts=3, out_dir=tmp_path, seed=42, jsonl=False, resume=True)
    cp2 = json.loads(checkpoint.read_text())
    assert cp2['completed'] == 3
    # at least two starts (one pre-existing + at least one resumed) should be present
    assert len(cp2['starts']) >= 2


def test_retry_backoff_on_failure(tmp_path: Path):
    cfg = config_module.load_config(Path('docs/example_input.toml'))
    opt = Optimizer(cfg)
    db = cfg.design_bounds
    bounds = [
        (db.min_tube_od_m, db.max_tube_od_m),
        (db.min_wall_thickness_m, db.max_wall_thickness_m),
        (db.min_coil_diameter_m, db.max_coil_diameter_m),
        (db.min_pitch_m, db.max_pitch_m),
        (db.min_turns, min(db.max_turns, db.min_turns + 10)),
    ]

    # construct planned_starts where first start is invalid (D_i<=0) causing immediate failure
    rng = np.random.RandomState(123)
    bad = [0.005, 0.003, 0.05, 0.02, 3]  # t too large -> D_i negative
    good = []
    x0 = np.array([rng.uniform(a, b) for (a, b) in bounds], dtype=float)
    x0[-1] = int(round(x0[-1]))
    good.append(x0.tolist())
    planned = [bad, good[0]]

    checkpoint = tmp_path / 'checkpoint.json'
    cp = {'timestamp': 'now', 'planned_starts': planned, 'completed': 0, 'starts': []}
    checkpoint.write_text(json.dumps(cp))

    out = opt.run_multi_start(bounds, n_starts=2, out_dir=tmp_path, seed=42, jsonl=False, resume=True, max_retries=2, backoff_base=0)
    cp2 = json.loads(checkpoint.read_text())
    # ensure completed and that the first start recorded retries > 0
    assert cp2['completed'] == 2
    assert 'retries' in cp2['starts'][0]
    assert cp2['starts'][0]['retries'] >= 1