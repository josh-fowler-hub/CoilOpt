# Input TOML — CoilOptimization

This document describes the expected input TOML format consumed by the CLI and parser (`src/coiloptimization_/config.py`). Use `docs/example_input.toml` as a canonical example.

## Top-level

- `schema_version` (string, required): schema version of the TOML. Start with `"0.1"`.

The following top-level tables are expected (all required): `fluid`, `process`, `design_bounds`, `constraints`, `objective`, `solver`.

## `fluid` (table) — HOT / internal fluid

- `name` (string, optional): friendly name (e.g., "flue_gas").
- `inlet_temp_c` (float, optional): inlet temperature of the hot gas in °C.
- `mass_flow_kg_s` (float, required): mass flow in kg/s (hot/internal fluid mass flow is required and used to compute energy balance).
- `name` (string, optional): material name (e.g., `"water"`, `"flue_gas"`). When provided, fluid properties are looked up automatically.
- `viscosity_pa_s` (float, optional): dynamic viscosity in Pa·s (override lookup when provided).
- `density_kg_m3` (float, optional): density in kg/m³ (override lookup when provided).
- `specific_heat_j_kgk` (float, optional): specific heat in J/(kg·K) (override lookup when provided).
- `thermal_conductivity_w_mk` (float, optional): thermal conductivity in W/(m·K) (override lookup when provided).

Notes: The `fluid` table describes the hot (internal) fluid (typically the flue gas). Provide the `mass_flow_kg_s` and `inlet_temp_c` (required). Optionally provide `outlet_temp_c` as a target — otherwise the solver computes the outlet temperature from the energy balance. All properties are treated as constants in the first implementation. Future versions may support temperature-dependent properties or references to a fluid database.

## `external` (table, optional) — COLD / external fluid

- If the external side is a flowing water stream, provide an `external` table with the same property keys as `fluid` (e.g., `temperature_c`, `mass_flow_kg_s`, `viscosity_pa_s`, `density_kg_m3`, `specific_heat_j_kgk`, `thermal_conductivity_w_mk`).
- Alternatively, specify `external.temperature_profile` as either an `equation` or `points` (see `profiles` docs) to define `T_inf(x)` along the coil. If the coil is immersed in a large bath, `external.temperature_c` (fixed bath temperature) is sufficient.

## `process` (table)

- `heat_duty_w` (float, optional): target heat duty in watts (optional). Prefer supplying mass flow and temperatures — the code computes Q from energy balance if not provided.
- `inlet_temp_c` (float, required): inlet temperature of the hot side in °C.
- `outlet_temp_c` (float, optional): desired outlet temperature for the hot side in °C (if specified, used for LMTD calculations).

## `design_bounds` (table)

Provide bounds for continuous and integer design variables:

- `min_tube_od_m`, `max_tube_od_m` (float, m) — outer diameter bounds of the tube.
- `min_pitch_m`, `max_pitch_m` (float, m) — helix pitch bounds.
- `min_coil_diameter_m`, `max_coil_diameter_m` (float, m) — coil (helix) diameter bounds.
- `min_turns`, `max_turns` (int) — integer bounds for number of turns.
- `min_wall_thickness_m`, `max_wall_thickness_m` (float, m) — optional bounds for tube wall thickness. Defaults provided if omitted.

## `constraints` (table)

- `max_pressure_drop_pa` (float, Pa, required): maximum allowable pressure drop.
- `max_surface_temp_c` (float, °C, optional): maximum allowable tube surface temperature.

## `objective` (table)

- `type` (string, required): objective type. Options: `"maximize_heat_transfer"`.

Notes: The tool focuses on maximizing overall heat transfer. Cost-based objectives (pumping power, material cost) are not supported and should not appear in inputs or outputs.

## `solver` (table)

- `method` (string, optional): local solver method, e.g., `"SLSQP"` (default) or `"trust-constr"`.
- `maxiter` (int, optional): maximum iterations for the solver (default: 500).
- `seed` (int, optional): random seed used by multi-start or global sampling.
- `n_starts` (int, optional): number of multi-start seeds when running global/multi-start strategies.
- `max_workers` (int, optional): maximum parallel workers for multi-start runs.

## Validation & Error Handling

- All required keys are validated at load-time. The parser raises a `ConfigError` with `field`, `message`, and `suggestion` to help users fix inputs.
- Units are assumed to be SI (meters, seconds, kilograms, degrees Celsius, Pascal, Watts). Future releases may accept units with suffixes.
- `material` (table, optional): supply coil material properties. You may provide either numeric values (e.g., `k_w = 15.0`) or a `name = "steel"` to use a built-in material lookup that supplies `k_w` and other properties.

## Example

See `docs/example_input.toml` for a working example that follows the schema. Use it as a starting point and tweak bounds and constraints for your design problem.

## Extending the schema

- Add new optional parameters using clear names and document them in this file.
- When changing `schema_version`, provide a migration function in `src/coiloptimization_/migrations/` and update `docs/toml_input.md` with the migration notes.
