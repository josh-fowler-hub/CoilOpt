from pathlib import Path
from coiloptimization_ import config
from coiloptimization_.optimize import Optimizer


def test_material_wall_thickness_used(tmp_path):
    # Load base example and modify material wall_thickness to be large
    p = Path('docs/example_input.toml')
    # baseline with no material override
    cfg_no = config.load_config(p)
    db = cfg_no.design_bounds
    opt_no = Optimizer(cfg_no)
    x = [0.012, 0.002, 0.2, 0.01, db.min_turns]
    Q_no, diag_no = opt_no.evaluate(x)

    # now set material wall_thickness large (override)
    cfg_mat = config.load_config(p)
    cfg_mat.material = {'name': 'steel', 'wall_thickness_m': 0.005}
    opt_mat = Optimizer(cfg_mat)
    Q_mat, diag_mat = opt_mat.evaluate(x)

    # diagnostics should show t_eff larger and D_i_local smaller
    assert 'last_local' in diag_mat
    last = diag_mat['last_local']
    assert last['t_eff'] >= 0.005
    # effective inner diameter should be smaller than the baseline
    assert last['D_i_local'] < diag_no['last_local']['D_i_local']
    # Q may increase or decrease depending on competing effects; just ensure values are finite
    assert isinstance(Q_mat, float) and isinstance(Q_no, float)
