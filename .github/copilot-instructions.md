# Project: CoilOptimization — Copilot Instructions

## Purpose

- Provide build planning, architecture, and conceptual guidance for the CoilOptimization project.
- Drive development: TOML-driven input -> mathematical model -> constrained optimizer -> geometry output.

## Where to find detailed docs (planning)

- Architecture: [architecture.md](architecture.md)
- Build plan: [build_plan.md](build_plan.md)
- Modeling & concepts: [concepts.md](concepts.md)
- TOML parser design: [toml_parser.md](toml_parser.md)
- Optimizer design: [optimizer.md](optimizer.md)
- Main driver & CLI design: [main_driver.md](main_driver.md)
- CLI spec: [cli.md](cli.md)
- Example input: [example_input.toml](example_input.toml)
- Logging & Reporting: [logging_and_reporting.md](logging_and_reporting.md)
- Plotting & visualization: [plotting.md](plotting.md)

## Development priorities

- Define a clear, versioned TOML schema of inputs and constraints.
- Implement a tested mathematical model for coil heat transfer and pressure drop.
- Build a constrained optimization core (SciPy / NLopt) with modular objective/constraint functions.
- Provide a CLI that reads TOML, runs optimizer, and writes results (JSON/TOML) with provenance.

## Programming conventions

- Language: Python 3.10+.
- Type hints: use PEP 484 type annotations for public APIs.
- Style: follow Black formatting and isort for imports; use flake8 for linting rules (keep rules permissive during early development).
- Project layout: keep modules small and focused under `src/coiloptimization_/`.
- Documentation: add docstrings for all public functions/classes (numpy or Google style acceptable) and update `docs/` planning docs when behavior changes.
- Dependencies: prefer standard library and small, well-maintained packages (SciPy, tomli, pydantic optional). Declare requirements in `requirements.txt` and `pyproject.toml`.
- No heavyweight refactors in a single PR: prefer iterative changes with tests.

## Error handling and robustness

- Fail-fast on user input errors: validate TOML schema early and raise a structured `ConfigError` with `field`, `message`, and `suggestion`.
- Runtime errors: raise clear exceptions with actionable messages. Catch and convert to user-facing errors in `main.py` with appropriate exit codes.
- Exit codes: `0` success, `1` usage/config error, `2` solver/infeasible error.
- Retries and timeouts: long-running tasks (objective evals, external solvers) should accept timeout limits and be interruptible.
- Checkpointing: multi-start optimizer must write progress checkpoints and support `--resume`.

## Testing procedures

- Unit tests: write pytest tests for each model primitive (`geometry`, `reynolds`, `nusselt`, `U_overall`, `pressure_drop`). Keep tests fast and deterministic.
- Integration tests: small runs of the full pipeline using `docs/example_input.toml` with reduced search budgets.
- CLI tests: invoke `src/coiloptimization_/main.py:main` in subprocess or via `run_config()` and assert exit codes and outputs.
- CI: add GitHub Actions to run lint, unit tests, and a quick integration smoke test on push and PRs.
- Coverage: aim for high coverage on core model code; keep CI thresholds flexible initially.

## Rules for Copilot and automated edits

- Always use the repository `manage_todo_list` tool to update the project TODOs at the start of multi-step work.
- Before using tools that modify files (`apply_patch`, `create_file`), send a one-line preamble describing what you'll do next.
- Use `apply_patch` for edits and follow the project's `applyPatchInstructions` (minimal, surgical changes; preserve style).
- Create small, focused commits (one logical change per patch). Do not modify unrelated files.
- Add or update tests for any functional change. Run tests locally when possible.
- When implementing features, prefer clarity over micro-optimizations; document any assumptions.
- If a migration or large refactor is required, open an issue/PR describing the plan and wait for review.

## Pull request checklist (for contributors and Copilot)

- Small, focused changes with descriptive commit message.
- All new code covered by unit tests.
- Add or update documentation in `` or `docs/` as appropriate.
- Pass CI: lint + tests.
- Update `CHANGELOG.md` or release notes for notable changes.

## Definition of Done
- Code is well-documented, tested, and follows the project's conventions.
- All tests pass, including integration tests.
  - Ensure that the integration tests are run with the full input file and reduced search budgets.
  - All tests should be deterministic and fast.
  - All tests should be run with the same input file to ensure consistency.
  - All test output should consist of only passes. No failures or warnings.
- CI passes, including linting and coverage checks.
- Code is reviewed by at least one other team member.
- Changes are merged into the main branch.
- `CHANGELOG.md` is updated with the new changes.
- Project TODOs are updated with the new changes.
- Documentation is added or updated as needed.

## Contact and handoff

- For design questions or divergences from these guidelines, open an issue and tag maintainers.
