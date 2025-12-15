import json
from pathlib import Path

from coiloptimization_ import config


def test_load_example_config(tmp_path):
    p = Path("docs/example_input.toml")
    cfg = config.load_config(p)
    assert cfg.schema_version == "0.1"
    # Either a material name is provided (and properties resolved) or numeric properties are present
    assert cfg.fluid.name is not None or (cfg.fluid.density_kg_m3 is not None and cfg.fluid.density_kg_m3 > 0)
    assert cfg.design_bounds.min_tube_od_m < cfg.design_bounds.max_tube_od_m
    assert cfg.solver.method.upper() in ("SLSQP", "TRUST-CONSTR" , "TRUST")


def test_missing_key_raises():
    bad = b"schema_version = \"0.1\"\n"
    try:
        config.load_config_bytes(bad)
        assert False, "expected ConfigError"
    except config.ConfigError as e:
        assert "fluid" in e.field
