# Logging & Reporting

## Purpose

Provide a clear, machine-friendly and human-readable logging system and a lightweight reporting pipeline so optimization runs are reproducible, auditable, and easy to share.

Goals:

- Human-readable console output for interactive runs.
- Structured logs (JSON) for programmatic ingestion and CI.
- Periodic progress and checkpoint logging for long multi-start runs.
- A Markdown report generator (with optional figures) summarizing final results, diagnostics and provenance.

## Design principles

- Minimal dependencies: use Python stdlib `logging` and small optional helpers (e.g., `python-json-logger`) only when available.
- Dual-format: human console + structured file (plain text and JSON lines).
- Small, testable helper functions: `configure_logging()`, `log_progress()`, `write_checkpoint()`, `generate_report()`.
- Keep logs and reports alongside results in the `results/` output directory with timestamps.

## Logging: levels and formats

- `DEBUG`: very verbose internal state — used for deep troubleshooting.
- `INFO`: high-level progress, start/finish of major phases, best-so-far updates.
- `WARNING`: recoverable or unexpected conditions (e.g., solver non-convergence but fallback succeeded).
- `ERROR`: unrecoverable failures; include stack traces in saved logs.
- `CRITICAL`: fatal errors that terminate the run.

Format recommendations:

- Console: human-friendly compact format with time, level, and short message (colors optional).
- File (plain text): same as console but full timestamp and module name.
- Structured file (JSON lines): one JSON object per event including: `timestamp`, `level`, `logger`, `event`, `run_id`, `x_best` (optional), `objective`, `constraints`, `elapsed_s`, and `extra` dict for arbitrary metadata.

Example JSON event fields:

```json
{
  "timestamp": "2025-12-15T12:34:56Z",
  "level": "INFO",
  "event": "local_solve_complete",
  "run_id": "2025-12-15T12-00-00_abc123",
  "start_index": 7,
  "objective": -4321.5,
  "feasible": true,
  "constraints": {"max_pressure_drop_pa": 560.2},
  "elapsed_s": 12.4
}
```

## Handlers and rotation

- Console handler: controlled by `-v` flag mapping to `INFO`/`DEBUG`.
- File handler (plain text): optional `--log-file` path; default `results/<run_id>/run.log`.
- JSON-lines handler: `results/<run_id>/run.jsonl` for structured events.
- Use `logging.handlers.RotatingFileHandler` or `TimedRotatingFileHandler` for long-running services; for single-run CLI, a single file per run is sufficient.

## Progress & checkpoint logging

- Emit a concise progress event after each local solve (for multi-start) including:
  - start index & total starts
  - best-so-far objective and feasibility flag
  - time elapsed and ETA estimate (simple linear extrapolation)
- Write a small `checkpoint.json` to the output dir after each completed start containing:
  - list of remaining starts (or index), best solution so far, RNG seed, and timestamp.
- Checkpoints enable `--resume` behavior in the CLI.

## Report generation (post-run)

- Default report: `results/<run_id>/report.md` with sections:
  - Title & provenance (input TOML checksum, schema_version, git commit if available, timestamp, seed).
  - Run summary (method, n_starts, time, success flag).
  - Best design: `x_opt` table, objective value, constraints evaluation.
  - Key metrics: total tube length, external area, pressure drop.
  - Diagnostics: solver messages, number of restarts, convergence info.
  - Plots (optional): objective vs start index, constraint violations histogram, temperature profile along coil for `x_opt` (PNG files in same folder).
  - Repro instructions: command-line used and suggested next steps.

Implementation notes:

- Keep the report generator independent from plotting libraries; only import `matplotlib` when generating figures. If `matplotlib` is unavailable, generate the markdown without embedded figures and note this in the report.
- Save figures as PNG into the run output dir and reference them in the markdown using relative paths.

## Integrations & utilities

- `src/coiloptimization_/logging.py` (recommended): exports `configure_logging(out_dir, level, jsonl=True, file=None)` and convenience wrappers `get_logger(name)`.
- `src/coiloptimization_/reporting.py` (recommended): exports `generate_report(result, cfg, out_dir, include_figures=True)`.
- CLI flags:
  - `--log-file <path>`: override default log file path.
  - `--no-json-log`: disable JSON-line logging.
  - `--report` or `--no-report`: control generation of `report.md`.

## Checkpoints and resume behavior

- Checkpoint file (`checkpoint.json`) should include enough state to resume the multi-start: remaining start seeds/indices and best-so-far. Keep checkpoints small and write atomically (write temp file then move).

## Testing & validation

- Unit tests for `configure_logging()` that:
  - create logs in a temporary dir and assert both plain text and JSON-lines files are created.
  - validate that progress events contain required fields.
- Integration test for `generate_report()` that runs a very small optimization (n_starts=2, fast stub model) and asserts `report.md` exists and contains the key sections.

## Retention & housekeeping

- Recommend a retention policy outside the tool (CI or user): keep last N runs or prune by date. The tool should not auto-delete results by default.

## Security and privacy

- Avoid logging secrets or large binary payloads. If user-provided inputs may contain sensitive text, do not include raw toml contents in JSON logs — prefer checksums and truncated previews.

## Example usage

Run with defaults and get logs + report:

```bash
coilopt examples/example_input.toml --output results/run1 --log-file results/run1/run.log
```

Create a run with JSON events disabled and no report:

```bash
coilopt examples/example_input.toml --output results/run2 --no-json-log --no-report
```

## Next implementation tasks

- Add `src/coiloptimization_/logging.py` helper (configure handlers, JSON events).
- Add `src/coiloptimization_/reporting.py` to render `report.md` and optional figures.
- Wire CLI flags to control logging/reporting behavior.

## Appendix: Minimal JSON event schema

- `event`: short string code (e.g., `start_run`, `local_solve_complete`, `checkpoint`, `end_run`).
- `run_id`: unique run identifier.
- `payload`: arbitrary object with event-specific fields.

- Keep schema small and stable; add fields as `extra` when needed.
