from pathlib import Path

from coiloptimization_ import config, model
from coiloptimization_.optimize import Optimizer


def test_properties_evaluated_at_film_temperature():
    cfg = config.load_config(Path("docs/example_input.toml"))
    opt = Optimizer(cfg)

    # use a simple midpoint design vector
    db = cfg.design_bounds
    x = [0.5 * (db.min_tube_od_m + db.max_tube_od_m),
         0.5 * (db.min_wall_thickness_m + db.max_wall_thickness_m),
         0.5 * (db.min_coil_diameter_m + db.max_coil_diameter_m),
         0.5 * (db.min_pitch_m + db.max_pitch_m),
         db.min_turns]

    Q, diag = opt.evaluate(x)
    assert isinstance(diag, dict)
    assert "last_local" in diag
    last = diag["last_local"]
    assert "Twi" in last and "Two" in last
    assert "rho_i" in last and "rho_o" in last

    # outlet bulk temperature used for film calculation
    Tout = diag["Tout"]
    Tfilm_i = 0.5 * (Tout + last["Twi"])
    # fluid lookup at film temperature should match stored rho_i
    rho_expected = model.get_fluid_properties(cfg.fluid.name, Tfilm_i)[0]
    assert abs(rho_expected - last["rho_i"]) / (rho_expected + 1e-12) < 1e-6
