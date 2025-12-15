from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

from coiloptimization_.reporting import generate_all_figures
from coiloptimization_.reporting import generate_report
from coiloptimization_.types import Config, FluidProps, Process, DesignBounds, Constraints, ExternalProps, Objective, SolverOptions


def make_min_config() -> Config:
    return Config(
        schema_version="0.1",
        fluid=FluidProps(name="water", mass_flow_kg_s=0.1, density_kg_m3=1000.0, viscosity_pa_s=1e-3, specific_heat_j_kgk=4182.0, thermal_conductivity_w_mk=0.6),
        process=Process(heat_duty_w=1000.0, inlet_temp_c=60.0, outlet_temp_c=40.0),
        design_bounds=DesignBounds(min_tube_od_m=0.005, max_tube_od_m=0.02, min_pitch_m=0.001, max_pitch_m=0.05, min_coil_diameter_m=0.02, max_coil_diameter_m=1.0, min_turns=1, max_turns=100),
        constraints=Constraints(max_pressure_drop_pa=10000.0, max_surface_temp_c=150.0),
        external=ExternalProps(temperature_c=20.0),
        material=None,
        objective=Objective(type="maximize_heat_transfer", weights={"heat": 1.0}),
        solver=SolverOptions(method="SLSQP", maxiter=100, seed=42),
    )


def test_generate_all_figures(tmp_path: Path):
    cfg = make_min_config()
    y = np.linspace(0, 1, 50).tolist()
    q = (1000.0 * np.exp(-5 * np.array(y))).tolist()
    cum = np.cumsum(np.array(q) * (y[1] - y[0])).tolist()
    result = {
        "start_results": [ {"objective": 1000.0}, {"objective": 1200.0}, {"objective": 1180.0} ],
        "objective_history": [900.0, 950.0, 1000.0, 1100.0],
        "constraint_violations": [0.0, -0.1, 0.0, 0.5],
        "y_grid": y,
        "T_hot_x": (60.0 - 20.0 * np.array(y)).tolist(),
        "T_inf_x": (20.0 * np.ones_like(y)).tolist(),
        "T_wall_inner_x": (50.0 * np.ones_like(y)).tolist(),
        "q_x": q,
        "cum_Q_x": cum,
        "pressure_drop": 123.4,
        "pressure_drop_profile": (np.linspace(0, 100, len(y))).tolist(),
        "sensitivity": {"D_o": 5.0, "p": -2.0},
        "x": {"D_o_m": 0.01, "D_c_m": 0.1, "pitch_m": 0.02, "N": 10},
        "provenance": {"timestamp": "2025-12-15T12:00:00Z"},
        "feasible": True,
        "objective": {"Q_w": 1234.0},
        "solver_info": {"method": "SLSQP"},
    }

    figs = generate_all_figures(result, cfg, tmp_path)
    # ensure at least temp profile and a couple others are generated
    assert any('temp_profile_x.png' in f for f in figs)
    for f in figs:
        p = tmp_path / f
        assert p.exists() and p.stat().st_size > 0

    # Also ensure generate_report happily includes figure references
    rpt = generate_report(result, cfg, tmp_path, include_figures=True)
    txt = rpt.read_text()
    assert 'Figures' in txt