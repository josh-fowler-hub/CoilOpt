# CoilOpt

CoilOpt is a lightweight CLI tool to optimize coil geometry to maximize overall heat transfer (Q) subject to hydraulic and thermal constraints.

## Quick links

- Quick start and usage: `docs/usage.md`
- CLI reference: `docs/cli.md`
- Example inputs: `docs/example_input.toml`
- Report format: `docs/report.md`

## Input TOML

See `docs/toml_input.md` for the full schema and `docs/example_input.toml` for a canonical example input file.

## Overview

CoilOpt reads a small TOML configuration describing the hot/internal fluid, external boundary conditions, design bounds, and solver options. It runs a constrained optimization (SciPy) to choose coil geometry variables (tube outer diameter, wall thickness, coil diameter, pitch, turns) that maximize the total heat transferred from the hot fluid to the external fluid while satisfying pressure-drop and maximum surface temperature constraints.

## Quick start

Install deps:

```bash
python -m pip install -r requirements.txt
```

Run a quick single-pass optimization (writes results to `results/<timestamp>/` by default):

```bash
coilopt docs/example_input.toml --output results/run_quick --report
```

Run a multi-start optimization (set `solver.n_starts` in the TOML or override on the CLI):

```bash
coilopt docs/example_input.toml --n-starts 4 --output results/run_multi --report
```

Resume a previously interrupted multi-start run (must point to the same `--output` dir containing `checkpoint.json`):

```bash
coilopt docs/example_input.toml --output results/run_multi --resume --report
```

## Running tests

Run the unit/integration tests with:

```bash
pytest -q
```

## Contributing

Contributions welcome — please open issues or PRs for bugs, features, or documentation improvements. See `.github/copilot-instructions.md` for development conventions used in this repository.
