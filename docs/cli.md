# CLI Reference

Usage: `coilopt <input.toml> [options]`

Options
- `-o, --output <path>` — write result JSON and report to this output directory (default: `results/<timestamp>/`).
- `-m, --method <METHOD>` — solver method (e.g., `SLSQP`).
- `--maxiter <N>` — override solver max iterations.
- `--seed <INT>` — RNG seed for multi-start sampling.
- `-v, --verbose` — repeat to increase verbosity (INFO/DEBUG).
- `--dry-run` — validate config and print resolved values; do not run optimizer.
- `--no-save` — do not write result files (useful for quick tests).
- `--resume` — resume a multi-start run from `checkpoint.json` in the `--output` dir.
- `--n-starts <N>` — override number of multi-start seeds.
- `--max-workers <N>` — override parallel worker count (future feature).
- `--log-file <path>` — write detailed run log to file.
- `--no-json-log` — disable JSON-line events (no `run_<timestamp>.jsonl` will be written).
- `--report` — generate `report.md` with optional figures after run.

Examples

```bash
coilopt docs/example_input.toml --n-starts 4 --output results/run1 --report
coilopt docs/example_input.toml --dry-run
coilopt docs/example_input.toml --no-json-log --output results/run1
```
