from pathlib import Path
from coiloptimization_ import config


def test_kelvin_to_celsius_conversion(tmp_path):
    toml = '''
schema_version = "0.1"

[units]
length = "meters"
temperature = "kelvin"

[internal]
name = "water"
mass_flow = 1.0
inlet_temp = 300.0
outlet_temp = 290.0

[external]
name = "water"
Tinf_profile = "300 - 10 * (z / 1.0)"

[design_bounds]
min_tube_od = 0.005
max_tube_od = 0.02
min_pitch = 0.001
max_pitch = 0.01
min_coil_diameter = 0.02
max_coil_diameter = 0.1
min_turns = 1
max_turns = 10

[constraints]
max_pressure_drop = 10000.0

[objective]
type = "maximize_heat_transfer"
weights = { heat = 1.0 }

[solver]
method = "SLSQP"
maxiter = 10
'''
    p = tmp_path / 'u.toml'
    p.write_text(toml)
    cfg = config.load_config(p)
    # inlet temp should be converted to C
    assert abs(cfg.process.inlet_temp_c - (300.0 - 273.15)) < 1e-6
    # Tinf_profile should have been wrapped and available in cfg.external.temperature_profile
    assert cfg.external.temperature_profile is not None
    assert isinstance(cfg.external.temperature_profile, str)
    assert '- 273.15' in cfg.external.temperature_profile or '300' in cfg.external.temperature_profile
