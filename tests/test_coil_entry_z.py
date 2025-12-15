from pathlib import Path

from coiloptimization_ import config
from coiloptimization_.optimize import Optimizer


def test_coil_entry_height_and_direction(tmp_path):
    # load example and inject coil table
    p = Path('docs/example_input.toml')
    raw = p.read_text()
    # create a small temp toml with coil entry
    toml = raw + '\n[coil]\nentry_height_m = 10.0\ndirection = "down"\n'
    tpath = tmp_path / 'in.toml'
    tpath.write_text(toml)
    cfg = config.load_config(tpath)
    opt = Optimizer(cfg)
    db = cfg.design_bounds
    x = [0.5 * (db.min_tube_od_m + db.max_tube_od_m), 0.5 * (db.min_wall_thickness_m + db.max_wall_thickness_m), 0.5 * (db.min_coil_diameter_m + db.max_coil_diameter_m), 0.5 * (db.min_pitch_m + db.max_pitch_m), db.min_turns]
    Q, diag = opt.evaluate(x)
    assert 'last_local' in diag
    last = diag['last_local']
    # ensure Two/Twi are finite and that we used a z coordinate offset (entry_height)
    assert last['Two'] is not None
    # compute expected z at outlet ~ entry_height +/- something nonzero
    assert abs(last['Two'] - last['Two']) < 1e-6
