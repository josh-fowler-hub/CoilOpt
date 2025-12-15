from pathlib import Path
from coiloptimization_ import config


def test_length_and_mass_units(tmp_path):
    toml = '''
schema_version = "0.1"

[units]
length = "cm"
mass = "g"
time = "min"

[internal]
name = "water"
mass_flow = 60000.0
inlet_temp = 300.0
outlet_temp = 290.0

[design_bounds]
min_tube_od = 0.5
max_tube_od = 2.0
min_pitch = 0.1
max_pitch = 1.0
min_coil_diameter = 2.0
max_coil_diameter = 10.0
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
    p = tmp_path / 'u2.toml'
    p.write_text(toml)
    cfg = config.load_config(p)
    # length: min_tube_od=0.5 cm -> 0.005 m
    assert abs(cfg.design_bounds.min_tube_od_m - 0.005) < 1e-8
    # mass_flow: 60000 g/min -> 1 kg/s
    assert abs(cfg.fluid.mass_flow_kg_s - 1.0) < 1e-9
