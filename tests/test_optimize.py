from pathlib import Path
import numpy as np

from coiloptimization_.config import load_config
from coiloptimization_.optimize import Optimizer


def test_optimizer_single_start_smoke():
    cfg = load_config(Path("docs/example_input.toml"))
    opt = Optimizer(cfg)
    # initial guess: midpoint values from config
    db = cfg.design_bounds
    x0 = np.array([
        0.5 * (db.min_tube_od_m + db.max_tube_od_m),
        0.5 * (db.min_wall_thickness_m + db.max_wall_thickness_m),
        0.5 * (db.min_coil_diameter_m + db.max_coil_diameter_m),
        0.5 * (db.min_pitch_m + db.max_pitch_m),
        db.min_turns,
    ])
    bounds = [
        (db.min_tube_od_m, db.max_tube_od_m),
        (db.min_wall_thickness_m, db.max_wall_thickness_m),
        (db.min_coil_diameter_m, db.max_coil_diameter_m),
        (db.min_pitch_m, db.max_pitch_m),
        (db.min_turns, db.max_turns),
    ]
    res = opt.optimize_single_start(x0, bounds, maxiter=5)
    assert res.objective is not None
    assert isinstance(res.success, bool)
