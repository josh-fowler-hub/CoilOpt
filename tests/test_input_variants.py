from pathlib import Path

from coiloptimization_ import config


def test_load_example_variant():
    p = Path("test_case/example1/input.toml")
    cfg = config.load_config(p)
    # internal -> fluid
    assert cfg.fluid.name == "flue_gas"
    assert cfg.fluid.mass_flow_kg_s == 0.05
    # interface -> material
    assert isinstance(cfg.material, dict)
    assert cfg.material.get("name") == "steel"
    assert cfg.material.get("wall_thickness_m") == 0.0005
    # external temp profile is captured
    assert cfg.external is not None
    assert cfg.external.name == "water"
    # profile was captured and normalized (may have been converted from Kelvin to Celsius)
    assert cfg.external.temperature_profile is not None
    assert isinstance(cfg.external.temperature_profile, str) or isinstance(cfg.external.temperature_profile, list) 
