# CLI Design — CoilOptimization

## Purpose

Define a clear, scriptable CLI interface and programmatic entrypoints for the CoilOptimization tool. The CLI should be suitable for interactive use, CI/scripting, and programmatic import in tests/notebooks.

## Entry points

- Console script: `coilopt` → `src/coiloptimization_/main.py:main`
- Programmatic API: `run_config(cfg: Config, out_path: Path, dry_run: bool=False)`

## Command-line arguments

### Positional

- `input` — path to TOML input file (required)

### Options

- `-o, --output <path>` — path to write result JSON/TOML (default: `results/<timestamp>_result.json`).
- `-m, --method <METHOD>` — override solver method (e.g., `SLSQP`, `trust-constr`).
- `--maxiter <N>` — override solver `maxiter`.
- `--seed <INT>` — RNG seed for reproducibility.
- `-v, --verbose` — increase logging verbosity (repeat for DEBUG).
- `--dry-run` — validate config and print resolved values, then exit.
- `--no-save` — run but do not write result files.
- `--resume` — resume from checkpoint in `--output` directory.
- `--n-starts <N>` — override multi-start count.
- `--max-workers <N>` — override parallel worker count for multi-start.
- `--log-file <path>` — write detailed run log.
- `--profile` — run an optional profiler around objective evaluations.

### Environment variables (optional)

- `COILOPT_SEED` — fallback RNG seed.
- `COILOPT_VERBOSE` — map to `-v` count.

### Subcommands (optional)

- `validate` — validate a TOML and print resolved config.
- `schema` — print the current TOML schema/version and acceptable fields.

### Example usage

```bash
coilopt examples/example_input.toml \
  --output results/run1.json --method SLSQP --seed 42 -vv

coilopt validate examples/example_input.toml
```

## Behavior and expectations

- Exit codes:
  - `0` — success, feasible solution
  - `1` — usage/config error (missing fields, bad types)
  - `2` — optimization failure or infeasible final result
- The CLI must validate input and fail fast with actionable messages.
- Default output format is JSON; include optional `--toml` to write TOML.
- By default, write a small `checkpoint.json` to the output directory during multi-start runs to allow `--resume`.

Notes on fluids

- The `fluid` table describes the hot (internal) fluid (flue gas). It must include `mass_flow_kg_s` and `inlet_temp_c` (or `process.inlet_temp_c`).
- The `external` table is optional and describes the cold/water side (bath or flowing external fluid).

## Logging & progress

- Use Python `logging` with a console handler and optional file handler.
- Support `-v` flags to control verbosity (INFO default, `-v` → DEBUG).
- Print concise progress updates: best-so-far objective, feasibility, starts completed / total, elapsed time.
- For long runs, update every completed start and optionally every N seconds.

## Programmatic API

- `main()` – parse args and call `run_config()`.
- `run_config(cfg: Config | Path, out_path: Optional[Path]=None, resume: bool=False, dry_run: bool=False)` – programmatic runner used by CLI/tests.
- `load_and_validate(path: Path) -> Config` – wrapper that returns typed and normalized `Config`.
- `build_model(cfg: Config) -> Model` – returns model object / callables.
- `build_optimizer(cfg: Config, model: Model) -> Optimizer` – returns optimizer instance.

These functions should be small and unit-testable.

## CLI implementation notes

- Use `argparse` for simplicity. Consider `click` only if we want richer subcommands.
- Keep `main.py` minimal: parse args → call `run_config()`.
- Place CLI glue in `src/coiloptimization_/main.py` and small helpers (logging config) in `src/coiloptimization_/logging.py`.
- Provide console-friendly pretty printing of the final result and a machine-readable JSON/TOML output.

## Testing

- Unit tests for `load_and_validate()` using example TOML files and malformed inputs.
- Integration test: run `coilopt` on `docs/example_input.toml` with `--n-starts=2 --max-workers=1 --no-save` (fast stubbed model) and assert exit code `0` and expected printed output.
- Test `--resume` by running a stub multi-start, killing mid-run (simulate), then resuming.

## Packaging & entry points

- Add console script entry in `pyproject.toml` / `setup.cfg`:

```toml
[project.scripts]
coilopt = "coiloptimization_.main:main"
```

## Security considerations

- Do not execute arbitrary code from the TOML. If we support callbacks, restrict to a whitelist of modules/functions.

## UX & ergonomics

- Provide helpful error messages with `suggestion` fields when a required key is missing or out of range.
- Print a short summary table at the end: `x_opt`, `objective`, main constraints, and output file path.
- Offer `--open` to open the results file after run (optional, platform dependent).
