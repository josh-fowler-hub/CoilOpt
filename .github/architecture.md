# CoilOptimization — Architecture

## Overview

- Input: TOML file describing fluid, thermal load, geometry bounds, and constraints.
- Core: Mathematical model (heat transfer, pressure drop) + optimizer.
- Output: Optimized geometry (coil pitch, tube diameter, coil diameter, turns, etc.), cost metrics, and provenance.

## Major components

- CLI: parses TOML, invokes optimizer, writes output.
- Config schema: versioned TOML schema with defaults and bounds.
- Model library: modular functions for heat transfer coeffs, Nusselt correlations, pressure drop, and derived metrics.
- Optimizer: wrapper around SciPy or NLopt providing constrained optimization, multi-start, and sensitivity analysis.
- IO & validation: schema validation, unit tests, and example cases.

## Data flow

1. CLI reads TOML and validates schema.
2. Parameters are converted to internal units and fed to the model.
3. Model computes objective (e.g., maximize heat transfer). Pumping power and material cost are not modeled and are not part of the results.
4. Optimizer finds best geometry; results validated and written to disk.

## Extensibility

- Add new correlations by implementing the model interface.
- Swap optimizer backend with minimal glue code.
- Export results as JSON, TOML, or CSV for downstream analysis.

## Dependencies and tech choices

- Python 3.10+
- Use `tomli`/`tomllib` for TOML parsing.
- SciPy for optimization; optionally `nlopt` if needed for global/local mix.
- `pydantic` or `schema` for validation (optional lightweight approach preferred).

## Files of interest

- `src/coiloptimization_/main.py` — CLI entrypoint
- `src/coiloptimization_/model.py` — model math (to create)
- `src/coiloptimization_/optimize.py` — optimization wrapper (to create)
- `docs/*` — design docs and examples

## Testing

- Unit tests for each correlation and constraint (pytest)
- Integration tests using example TOML inputs

## Performance

- Keep model vectorized for multi-start sampling.
- Profile objective evaluation and cache repeated calls where safe.

## Security & Repro

- Record solver seed and input provenance in outputs.
- Fail fast on malformed inputs.
