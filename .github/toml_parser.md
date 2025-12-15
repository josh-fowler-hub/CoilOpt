# TOML Parser — Design and Plan

## Purpose

- Read user-provided TOML input, validate it against a versioned schema, normalize units, and emit a typed `Config` object consumed by the model and optimizer.

## Principles

- Fail-fast with clear, actionable error messages for invalid inputs.
- Keep parsing and validation deterministic and testable.
- Preserve provenance: include the original TOML, schema version, and any defaults applied in output.
- Make the parser simple and dependency-light (prefer `tomli` for Python 3.10 compatibility, use `tomllib` when running on 3.11+ if available).

## Parser responsibilities

- Read file or stream and parse TOML into native Python structures.
- Validate required top-level sections: `fluid` (hot/internal fluid), `process`, `design_bounds`, `constraints`, `objective`, `solver`.
- Support an optional `external` table to describe the external (cold) fluid and boundary conditions (e.g., `temperature_c`, `mass_flow_kg_s`, `viscosity_pa_s`, `density_kg_m3`, `specific_heat_j_kgk`, `thermal_conductivity_w_mk`).
- Validate types and ranges for required keys; apply defaults for optional keys.
- Convert units to SI internally (helper module `units.py`).
- Enforce `schema_version` compatibility and provide migration hooks.
- Emit a typed `Config` object (preferably a `pydantic.BaseModel` or `dataclass`) with:
  - `fluid`: hot (internal) fluid properties
  - `external`: optional external (cold) fluid or boundary conditions
  - `process`: heat duty and temperatures
  - `design_bounds`: bounds for each design variable
  - `constraints`: inequality constraints and limits
  - `objective`: objective type and weights
  - `solver`: solver options and seed

## Suggested libraries and types

- `tomli` (read-only TOML; Python 3.10 compatibility)
- `pydantic` (for validation and typed models) OR lightweight `dataclasses` + manual checks if minimizing deps
- `numpy` optional for numeric helpers in validation

## Parsing flow (high-level)

1. Read bytes from file/stream.
2. Parse TOML into a dict via `tomli.loads`.
3. Check for `schema_version` and bail with clear message if missing or unsupported.
4. Normalize keys to canonical names (snake_case) and apply defaults.
5. Validate each section and key (types, ranges).
6. Run unit normalization on numeric fields.
7. Construct and return `Config` typed object.

## Validation rules and examples

- `fluid.mass_flow_kg_s` (hot/internal fluid) must be > 0 and is required for energy-balance-based objective evaluation.
- If provided, `external` properties are validated similarly to `fluid` and used to compute external convection or assume a fixed bath temperature if only `temperature_c` is provided.
- Support optional `external.temperature_profile` with either:
  - `equation` (string): an expression in variable `x` (coordinate in meters along coil length) that evaluates to temperature in °C. Supported functions: `sin, cos, exp, log, sqrt` etc.
  - `points` (array of tables): list of `{ x_m = <float>, temp_c = <float> }` pairs to be linearly interpolated along `x`.
- `design_bounds.min_tube_od_m` must be < `max_tube_od_m`.
- `constraints.max_pressure_drop_pa` must be non-negative.
- `objective.type` must be one of the pre-defined options.

## Error handling

- Use structured exceptions: `ConfigError` with `field`, `message`, and `suggestion`.
- For schema version mismatch: include migration hints and reference to `docs/example_input.toml`.
- Provide CLI-friendly exit codes for common failures.

## API surface

- `load_config(path: str) -> Config`
- `load_config_bytes(b: bytes) -> Config`
- `validate_config(raw: dict) -> Config` (explicit validation entrypoint)
- `dump_resolved_config(cfg: Config, path: str)` — write resolved values & provenance

## Implementation notes

- Put parser code in `src/coiloptimization_/config.py` (or `io.py`) and the typed models in `src/coiloptimization_/types.py`.
- Keep unit conversions isolated in `src/coiloptimization_/units.py`.
- Add a small wrapper in `src/coiloptimization_/main.py` to call `load_config()` and pass `Config` to optimizer.

## Testing

- Unit tests for parse -> validate -> Config conversion with:
  - Minimal valid config
  - Missing required fields
  - Invalid ranges and types
  - Schema version mismatch
- Integration test: run CLI with `docs/example_input.toml` and assert that `Config` fields match expected normalized values.

## Examples and docs

- Place `docs/example_input.toml` as canonical example for users.
- Document `schema_version` lifecycle and how to extend schema in `docs/toml_parser.md`.

## Migration and extensibility

- If schema changes, add a `migrations/` module with functions `migrate_v0_1_to_v0_2(raw: dict) -> dict`.
- Use `schema_version` in the TOML to select migration path.

## Pseudo-code example

```py
# src/coiloptimization_/config.py (sketch)
# from tomli import loads
# from pydantic import BaseModel

def load_config_bytes(b: bytes) -> Config:
    raw = tomli.loads(b)
    if 'schema_version' not in raw:
        raise ConfigError('schema_version missing')
    raw = migrate_if_needed(raw)
    validated = validate_raw(raw)
    normalized = units.normalize(validated)
    return Config.parse_obj(normalized)
```
