# Build Plan — CoilOptimization

## Goals

- Deliver a deterministic CLI tool that reads a TOML spec and returns optimized coil geometry.
- Provide unit-tested modeling primitives and a flexible optimizer interface.

## Phases

1. Design and schema (1 week)
    - Define TOML schema (parameters, bounds, constraints, objectives)
    - Create `example_input.toml`
2. Modeling (2 weeks)
    - Implement core correlations: Nusselt, Reynolds, pressure drop, conduction, fouling factor hooks
    - Unit tests with analytic/benchmark cases
3. Optimization core (2 weeks)
    - Build `optimize.py` with SciPy-based constrained solver
    - Add multi-start and basic sensitivity reporting
    - Tests for constraint handling and convergence
4. CLI and IO (1 week)
    - Implement `main.py` CLI: parse, validate, run, write output
    - Add verbose/debug flags and provenance output
5. Examples and validation (1 week)
    - Add example TOML files and reference outputs
    - Add integration tests that run optimizer on small cases
6. CI, packaging, docs (1 week)
    - Add GitHub Actions: lint, tests, build
    - Prepare `pyproject.toml` and `requirements.txt` updates

## Milestones

- M1: TOML schema + example inputs
- M2: Model primitives with unit tests
- M3: Working optimizer + simple example
- M4: Full CLI + CI tests

## Notes

- Keep PRs small and focused on single components.
- Prioritize correctness and reproducibility over hyper-performance on first pass.
