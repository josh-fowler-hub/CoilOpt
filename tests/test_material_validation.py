from pathlib import Path
import pytest
from coiloptimization_ import config


def test_missing_material_name_raises(tmp_path):
    toml = '''
schema_version = "0.1"

[internal]
name = "water"
mass_flow = 1.0
inlet_temp = 300.0

[interface]
wall_thickness = 0.001

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
    p = tmp_path / 'bad1.toml'
    p.write_text(toml)
    with pytest.raises(config.ConfigError) as ei:
        config.load_config(p)
    assert 'material.name' in ei.value.field


def test_missing_material_wall_thickness_is_ok(tmp_path):
    toml = '''
schema_version = "0.1"

[internal]
name = "water"
mass_flow = 1.0
inlet_temp = 300.0

[interface]
name = "steel"

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
    p = tmp_path / 'ok.toml'
    p.write_text(toml)
    cfg = config.load_config(p)
    # material name present and no wall_thickness provided is acceptable
    assert cfg.material.get('name') == 'steel'
    assert cfg.material.get('wall_thickness_m') is None or cfg.material.get('wall_thickness') is None
