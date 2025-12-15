from pathlib import Path

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


def test_generate_report_minimal(tmp_path: Path):
    cfg = make_min_config()
    result = {
        "provenance": {"timestamp": "2025-12-15T12:00:00Z"},
        "feasible": True,
        "objective": {"Q_w": 1234.0},
        "x": {"D_o_m": 0.01, "pitch_m": 0.01, "D_c_m": 0.1, "N": 10},
        "solver_info": {"method": "SLSQP"},
    }
    rpt = generate_report(result, cfg, tmp_path, include_figures=False)
    assert rpt.exists()
    text = rpt.read_text()
    assert "Optimization Report" in text
    assert "Best Design" in text or "Best Design:" in text
    # pump power should not appear unless present in the result
    assert "pump" not in text.lower()
