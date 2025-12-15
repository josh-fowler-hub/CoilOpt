from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import tomli

from .types import (
    Config,
    FluidProps,
    Process,
    DesignBounds,
    Constraints,
    ExternalProps,
    Objective,
    SolverOptions,
)
from .units import normalize_units


class ConfigError(Exception):
    def __init__(self, field: str, message: str, suggestion: str | None = None):
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message
        self.suggestion = suggestion


REQUIRED_TOP_LEVEL = [
    "schema_version",
    "fluid",
    "process",
    "design_bounds",
    "constraints",
    "objective",
    "solver",
]


def load_config(path: str | Path) -> Config:
    b = Path(path).read_bytes()
    return load_config_bytes(b)


def load_config_bytes(b: bytes) -> Config:
    if isinstance(b, (bytes, bytearray)):
        raw = tomli.loads(b.decode("utf-8"))
    else:
        raw = tomli.loads(b)
    for key in REQUIRED_TOP_LEVEL:
        # allow 'internal' as an alias for 'fluid'
        if key == "fluid":
            if ("fluid" not in raw) and ("internal" not in raw):
                raise ConfigError(key, "required top-level key missing (or use 'internal')", "Add the key to the TOML file")
            continue
        if key == "process":
            # allow process data to be provided inside [internal]
            if "process" in raw:
                continue
            if "internal" in raw and any(k in raw["internal"] for k in ("inlet_temp_c", "inlet_temp", "outlet_temp_c", "outlet_temp", "heat_duty_w")):
                continue
            raise ConfigError(key, "required top-level key missing (or provide values inside [internal])", "Add a [process] table or inlet/outlet temps to [internal]")
        if key not in raw:
            raise ConfigError(key, "required top-level key missing", "Add the key to the TOML file")

    raw = normalize_units(raw)
    validated = validate_raw(raw)
    return validated


def validate_raw(raw: Dict[str, Any]) -> Config:
    # schema_version
    schema_version = raw.get("schema_version")
    if not isinstance(schema_version, str):
        raise ConfigError("schema_version", "must be a string", "set schema_version = \"0.1\"")

    # fluid: Accept either explicit numeric properties or a material name (preferred).
    # Support legacy/alternate key `internal` which represents the hot/internal fluid.
    f = raw.get("fluid") if raw.get("fluid") is not None else raw.get("internal")
    if f is None:
        raise ConfigError("fluid", "missing fluid/internal specification", "Add a [fluid] or [internal] table")
    try:
        mass_flow = f.get("mass_flow_kg_s")
        if mass_flow is None:
            raise ConfigError("fluid.mass_flow_kg_s", "missing", "Provide mass flow for the hot/internal fluid")
        fluid = FluidProps(
            name=f.get("name"),
            mass_flow_kg_s=float(mass_flow),
            density_kg_m3=float(f.get("density_kg_m3")) if f.get("density_kg_m3") is not None else None,
            viscosity_pa_s=float(f.get("viscosity_pa_s")) if f.get("viscosity_pa_s") is not None else None,
            specific_heat_j_kgk=float(f.get("specific_heat_j_kgk")) if f.get("specific_heat_j_kgk") is not None else None,
            thermal_conductivity_w_mk=float(f.get("thermal_conductivity_w_mk")) if f.get("thermal_conductivity_w_mk") is not None else None,
        )
    except ConfigError:
        raise
    except Exception as e:
        raise ConfigError("fluid", "invalid fluid specification", str(e))

    # process: accept either a dedicated [process] table or values inside [internal]
    p = raw.get("process") if raw.get("process") is not None else raw.get("internal")
    if p is None:
        raise ConfigError("process", "missing process/internal temperatures", "Add [process] or inlet_temp_c in [internal]")
    # heat_duty_w is optional: prefer mass flow and temperatures as primary inputs
    try:
        heat_duty = float(p.get("heat_duty_w")) if p.get("heat_duty_w") is not None else None
        inlet_temp = p.get("inlet_temp_c")
        if inlet_temp is None:
            raise ConfigError("process.inlet_temp_c", "missing", "Provide inlet_temp_c either in [process] or [internal]")
        process = Process(
            heat_duty_w=heat_duty,
            inlet_temp_c=float(inlet_temp),
            outlet_temp_c=float(p.get("outlet_temp_c")) if p.get("outlet_temp_c") is not None else None,
        )
    except ConfigError:
        raise
    except KeyError as e:
        raise ConfigError(f"process.{e.args[0]}", "missing", "Add the missing process property")

    # design_bounds
    d = raw["design_bounds"]
    try:
        design_bounds = DesignBounds(
            min_tube_od_m=float(d["min_tube_od_m"]),
            max_tube_od_m=float(d["max_tube_od_m"]),
            min_pitch_m=float(d["min_pitch_m"]),
            max_pitch_m=float(d["max_pitch_m"]),
            min_coil_diameter_m=float(d["min_coil_diameter_m"]),
            max_coil_diameter_m=float(d["max_coil_diameter_m"]),
            min_turns=int(d["min_turns"]),
            max_turns=int(d["max_turns"]),
            min_wall_thickness_m=float(d.get("min_wall_thickness_m", 0.0005)),
            max_wall_thickness_m=float(d.get("max_wall_thickness_m", 0.005)),
        )
    except KeyError as e:
        raise ConfigError(f"design_bounds.{e.args[0]}", "missing", "Add the missing design bound")

    if design_bounds.min_tube_od_m <= 0 or design_bounds.max_tube_od_m <= 0:
        raise ConfigError("design_bounds", "tube diameters must be > 0", None)
    if design_bounds.min_tube_od_m >= design_bounds.max_tube_od_m:
        raise ConfigError(
            "design_bounds", "min_tube_od_m must be < max_tube_od_m", "Fix the bounds in TOML"
        )

    # constraints
    c = raw["constraints"]
    try:
        constraints = Constraints(
            max_pressure_drop_pa=float(c["max_pressure_drop_pa"]),
            max_surface_temp_c=float(c.get("max_surface_temp_c")) if c.get("max_surface_temp_c") is not None else None,
        )
    except KeyError as e:
        raise ConfigError(f"constraints.{e.args[0]}", "missing", "Add the missing constraint")

    # objective
    o = raw["objective"]
    try:
        obj_type = o["type"]
        weights = o.get("weights", {})
        if not isinstance(weights, dict):
            raise ConfigError("objective.weights", "must be a table/dictionary", "Use weights = { heat = 1.0, ... }")
        objective = Objective(type=obj_type, weights={k: float(v) for k, v in weights.items()})
    except KeyError as e:
        raise ConfigError(f"objective.{e.args[0]}", "missing", "Add the missing objective property")

    # solver
    s = raw["solver"]
    try:
        solver = SolverOptions(method=s.get("method", "SLSQP"), maxiter=int(s.get("maxiter", 500)), seed=s.get("seed"))
    except Exception as e:
        raise ConfigError("solver", "invalid solver options", str(e))

    # optional external (cold/bath) side
    external = None
    if raw.get("external"):
        ex = raw["external"]
        # accept alternate key names for temperature profile commonly used in examples
        temp_profile = ex.get("temperature_profile") or ex.get("Tinf_profile") or ex.get("tinf_profile")
        external = ExternalProps(
            name=ex.get("name"),
            temperature_c=float(ex.get("temperature_c")) if ex.get("temperature_c") is not None else None,
            mass_flow_kg_s=float(ex.get("mass_flow_kg_s")) if ex.get("mass_flow_kg_s") is not None else None,
            viscosity_pa_s=float(ex.get("viscosity_pa_s")) if ex.get("viscosity_pa_s") is not None else None,
            density_kg_m3=float(ex.get("density_kg_m3")) if ex.get("density_kg_m3") is not None else None,
            specific_heat_j_kgk=float(ex.get("specific_heat_j_kgk")) if ex.get("specific_heat_j_kgk") is not None else None,
            thermal_conductivity_w_mk=float(ex.get("thermal_conductivity_w_mk")) if ex.get("thermal_conductivity_w_mk") is not None else None,
            temperature_profile=temp_profile,
        )

    # material: accept either [material] table or alternate [interface] table used in some examples
    material = raw.get("material") if raw.get("material") is not None else raw.get("interface")
    # Validate material/interface presence: If user provided an explicit [interface] table,
    # require both name and wall_thickness. If only [material] is present, allow numeric keys like k_w.
    if material is not None:
        if not isinstance(material, dict):
            raise ConfigError("material", "must be a table", "Use [material] or [interface] with appropriate keys")
        # If the user supplied [interface], enforce name + wall_thickness
        if raw.get("interface") is not None:
            if material.get("name") is None:
                raise ConfigError("material.name", "missing", "Provide a material name, e.g., name = \"steel\"")
            if material.get("wall_thickness_m") is None and material.get("wall_thickness") is None:
                raise ConfigError("material.wall_thickness", "missing", "Provide wall_thickness (will be normalized to meters)")

    # optional coil geometry: entry height and direction
    coil = raw.get("coil") if raw.get("coil") is not None else None

    return Config(
        schema_version=schema_version,
        fluid=fluid,
        process=process,
        design_bounds=design_bounds,
        constraints=constraints,
        external=external,
        objective=objective,
        solver=solver,
        material=material,
        coil=coil,
    )