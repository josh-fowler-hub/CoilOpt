from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class FluidProps:
    name: Optional[str]
    mass_flow_kg_s: float
    # Material properties may be provided explicitly, but are optional when a named
    # material is used (e.g., "water", "flue_gas"). If omitted, properties will
    # be looked up from the material name in the model.
    density_kg_m3: Optional[float] = None
    viscosity_pa_s: Optional[float] = None
    specific_heat_j_kgk: Optional[float] = None
    thermal_conductivity_w_mk: Optional[float] = None


@dataclass
class Process:
    heat_duty_w: Optional[float]
    inlet_temp_c: float
    outlet_temp_c: Optional[float]


@dataclass
class DesignBounds:
    min_tube_od_m: float
    max_tube_od_m: float
    min_pitch_m: float
    max_pitch_m: float
    min_coil_diameter_m: float
    max_coil_diameter_m: float
    min_turns: int
    max_turns: int
    min_wall_thickness_m: float = 0.0005
    max_wall_thickness_m: float = 0.005


@dataclass
class Constraints:
    max_pressure_drop_pa: float
    max_surface_temp_c: Optional[float]


@dataclass
class ExternalProps:
    # Optional external (cold) fluid or bath
    name: Optional[str] = None
    temperature_c: Optional[float] = None
    mass_flow_kg_s: Optional[float] = None
    viscosity_pa_s: Optional[float] = None
    density_kg_m3: Optional[float] = None
    specific_heat_j_kgk: Optional[float] = None
    thermal_conductivity_w_mk: Optional[float] = None
    # temperature_profile: dict with either 'equation' or 'points'
    temperature_profile: Optional[dict] = None


@dataclass
class Objective:
    type: str
    weights: Dict[str, float]


@dataclass
class SolverOptions:
    method: str
    maxiter: int
    seed: Optional[int] = None
    n_starts: Optional[int] = None


@dataclass
class Config:
    schema_version: str
    fluid: FluidProps
    process: Process
    design_bounds: DesignBounds
    constraints: Constraints
    external: Optional[ExternalProps]
    material: Optional[Dict[str, float]]
    objective: Objective
    solver: SolverOptions
    coil: Optional[Dict[str, object]] = None
