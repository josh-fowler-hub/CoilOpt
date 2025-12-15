# Examples

Simple single-run

```bash
coilopt docs/example_input.toml --output results/run_quick --report
```

Multi-start run

```bash
# edit docs/example_input.toml to set solver.n_starts = 4
coilopt docs/example_input.toml --output results/run_multi --report
```

Resume a run

```bash
coilopt docs/example_input.toml --output results/run_multi --resume --report
```

Inspecting output

- `results/<run_id>/result_<timestamp>.json` — machine-readable output.
- `results/<run_id>/report.md` — human report with figures in `results/<run_id>/figures/`.
- `results/<run_id>/checkpoint.json` — multi-start checkpoint enabling `--resume`.
- `results/<run_id>/run_<timestamp>.jsonl` — structured events (unless `--no-json-log` was used).
