# CoilOpt — Quick start & Usage

This guide explains how to use the CoilOpt command-line tool to optimize coil geometry for maximum heat transfer.

Prerequisites
- Python 3.10+
- Install dependencies (recommended in a virtualenv):

```bash
python -m pip install -r requirements.txt
```

Quick start (single-run)

```bash
coilopt docs/example_input.toml --output results/run1 --report
```

- `docs/example_input.toml` — example configuration to get you started.
- `--output` specifies the output directory or file prefix. If omitted, results go to `results/<timestamp>/`.
- `--report` writes a `report.md` (with optional figures) into the output directory.

Dry-run and validate only

```bash
coilopt docs/example_input.toml --dry-run
```

Modeling notes

- The internal (hot) fluid represents the flue gas you're cooling; provide its `mass_flow_kg_s`, `inlet_temp_c` and optionally `outlet_temp_c` (target). The optimizer computes the actual outlet temperature based on the energy balance and convection calculations when `outlet_temp_c` is not provided.
- The external (cold) side is typically water — supply `external.temperature_c` (a fixed bath) or an `external.temperature_profile` (equation or points) to define `T_inf(x)` along the coil. The optimizer uses `T_inf(x)` when computing local heat transfer.

Run a quick multi-start optimization

Edit `docs/example_input.toml` and set `solver.n_starts` to > 1, or override via CLI:

```bash
coilopt docs/example_input.toml --n-starts 4 --output results/run_multi --report
```

Resume a previous multi-start run

To resume from a previous run directory (that contains `checkpoint.json`), run:

```bash
coilopt docs/example_input.toml --output results/run_multi --resume
```

Disabling JSON event logging

Use `--no-json-log` if you do not want the run to emit structured JSON events to `run_<timestamp>.jsonl`.

```bash
coilopt docs/example_input.toml --no-json-log --output results/run1
```

Troubleshooting

- If runs fail or issue meaningful warnings, check `results/<run_id>/run.log` and `checkpoint.json`.
- To debug plotting or report generation, rerun with `--report` and inspect `results/<run_id>/figures/`.
