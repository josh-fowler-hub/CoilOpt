# Main Driver & CLI — CoilOptimization

## Purpose

Define the CLI and driver that glue the TOML parser, model, and optimizer into a reproducible runnable tool. The driver must be lightweight, dependency-minimal, and produce reproducible results with clear provenance.

## Responsibilities

- Parse CLI args and read a TOML input file.
- Validate and normalize config via `src/coiloptimization_/config.py`.
- Initialize logging, random seeds, and environment metadata.
- Create model and optimizer objects (or pass callables) based on config.
- Run optimizer and stream progress where possible.
- Post-process, validate final solution, and write results (JSON/TOML) with provenance.
- Return appropriate exit codes for scripting and CI.

## CLI interface (suggested)

- Tool entrypoint: `coilopt` (console script mapping to `src/coiloptimization_/main.py::main`).

### Positional args

- `input`: path to TOML input file (required)

### Optional args

- `-o, --output` : path to write output (default: `results/<timestamp>_result.json`)
- `-m, --method` : override solver method (e.g., `SLSQP`, `trust-constr`)
- `--maxiter` : override solver `maxiter`
- `--seed` : RNG seed for reproducibility
- `-v, --verbose` : increase logging verbosity (repeat for DEBUG)
- `--dry-run` : validate config and print resolved values, then exit
- `--no-save` : run but don't write result files
- `--profile` : run profiler around objective (for debugging/perf tuning)

### Example

```bash
coilopt examples/example_input.toml --output results/run1.json --method SLSQP --seed 42 -vv
```

## Main runtime flow (pseudo)

1. Parse CLI args.
2. Configure logging and set RNG seed.
3. Load and validate config: `cfg = load_config(path)`.
    - Note: `cfg.fluid` refers to the hot (internal) fluid (flue gas). `cfg.fluid.mass_flow_kg_s` and `cfg.process.inlet_temp_c` must be provided.
4. Build model functions: pass `model = Model(cfg)` or a set of callables.
5. Create optimizer wrapper: `opt = Optimizer(cfg.solver, model)`.
6. If `--dry-run`: print resolved config and exit.
7. Run `result = opt.run()` — this returns the full result object.
8. Post-process result: round integer variables, run `repair()` if needed, re-evaluate constraints.
9. Write outputs: `json`/`toml` with provenance (input file, timestamp, solver options, seed, start points).
10. Exit with code `0` if `result.feasible` else `2` (or configurable codes).

## Logging and progress

- Use Python `logging` with handlers:
  - Console handler with level controlled by `-v` flags.
  - Optional file handler (`--log-file`) to capture full run logs.
- Emit structured progress messages at key points: config loaded, start multi-start, each local solve completed, final result.
- For long runs, print periodic progress updates (best-so-far objective, feasibility).

## Output format and provenance

- Outputs should include:
  - `input_toml` (copy or checksum)
  - `schema_version`
  - `cfg_resolved` (normalized config)
  - `x_opt` (optimized variables)
  - `objective` and per-term breakdown (heat)
  - `constraints` evaluation at `x_opt`
  - `solver_info` (name, niter, success, message)
  - `provenance` (timestamp, seed, git commit if present, platform)
- Default file types: JSON for machine consumption, optionally TOML for human editing.

## Error handling and exit codes

- Exit `0` on success and feasible solution.
- Exit `1` on usage/config errors (missing required fields, schema mismatch).
- Exit `2` on solver failure or infeasible final result.
- Provide clear error messages and include `suggestion` fields when possible.

## Testing & CI

- Unit tests for `main.load_and_validate()` to assert correct normalization and error handling.
- Integration test: run CLI with `docs/example_input.toml` and assert output file exists and `feasible` is true for a simple case.
- Add GitHub Action workflow entry to run quick smoke test for the CLI.

## Implementation notes

- Keep `main.py` small; delegate heavy-lifting to `config.py`, `model.py`, and `optimize.py`.
- Provide a `run_config(cfg: Config, out_path: Path, dry_run: bool=False)` function that can be imported and used programmatically (for tests and notebooks).
- Expose logging configuration via an importable helper `src/coiloptimization_/logging.py`.

## Security & reproducibility

- Avoid executing arbitrary strings from TOML; restrict callable hooks to a whitelist if supported.
- Record seeds and environment metadata to reproduce runs.

---

## Next actions

- Implement `src/coiloptimization_/main.py` with `argparse`-based CLI and `run_config()` entrypoint.
- Add basic smoke tests under `tests/` to exercise CLI and `run_config()`.

## Main driver loop (detailed)

This section describes the recommended runtime loop for the driver. The goal is robustness (checkpointing, resume), clear progress reporting, and safe handling of long multi-start runs.

### Pseudocode

```py
def run_config(cfg, out_path, resume=False):
  setup_logging(cfg)
  seed_rng(cfg.solver.seed)
  cfg_resolved = load_and_validate(cfg)
  model = build_model(cfg_resolved)
  optimizer = build_optimizer(cfg_resolved.solver, model)

  # prepare start points (multi-start)
  starts = prepare_start_points(cfg_resolved, n_starts=cfg.solver.n_starts)
  best = None

  # optional checkpoint resume
  if resume:
    starts, best = load_checkpoint(out_path)

  # run local solves in parallel, but stream progress
  with ProcessPoolExecutor(max_workers=cfg.solver.max_workers) as exe:
    futures = {exe.submit(run_single_start, optimizer, s): s for s in starts}
    for fut in as_completed(futures):
      res = fut.result()
      update_best(res, best)
      write_progress_checkpoint(out_path, starts, best)
      log_progress(best)

  # post-process best: round integers, repair constraints, re-evaluate
  best = finalize_and_repair(best, model, cfg_resolved)
  save_result(out_path, cfg_resolved, best)
  return best
```

### Key behaviors

- Start-point generation: use low-discrepancy sequences (Sobol/LHS) and include a few heuristic seeds (midpoint, bounds edges).
- Streaming progress: after each local solve, log a concise update (objective, feasibility, elapsed time).
- Checkpointing: write a small checkpoint JSON after each completed local solve containing remaining starts and current best; allow `--resume` to continue.
- Resource control: limit concurrent local solves to `max_workers` and ensure each worker has a bounded memory/time budget.
- Signal handling: trap SIGINT/SIGTERM to write final checkpoint and exit cleanly.

### Functions to implement in `main.py`

- `prepare_start_points(cfg, n_starts) -> list[dict]`
- `run_single_start(optimizer, start) -> Result`
- `update_best(res, best) -> None`
- `write_progress_checkpoint(path, starts_remaining, best) -> None`
- `load_checkpoint(path) -> (starts, best)`
- `finalize_and_repair(best, model, cfg) -> Result`

### Metrics to emit during run

- Best-so-far objective (with breakdown)
- Best-so-far feasibility / constraint violations
- Number of starts completed / total
- Elapsed time and estimated time remaining (ETR)

### Testing suggestions

- Unit-test `prepare_start_points()` distribution and bounds compliance.
- Functional test: run `run_config()` with `n_starts=3`, `max_workers=1` and a fast stub-model to verify checkpointing and resume logic.
