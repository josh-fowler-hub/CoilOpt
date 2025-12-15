# Interpreting `report.md`

When you run with `--report`, `CoilOpt` writes a `report.md` into the output directory (`results/<run_id>/report.md`). The report summarizes provenance, the best design, key metrics, diagnostics, and references to generated figures.

Sections you'll see
- **Provenance** — timestamp, solver options, and input file reference.
- **Run Summary** — feasibility flag and objective value.
- **Best Design** — optimized variables (tube OD, pitch, coil diameter, turns).
- **Key Metrics** — total tube length, external area, pressure drop (Pa).
- **Figures** — relative links to `figures/` (temperature profile, objective traces, sensitivities).

Notes
- The report does not include pump power or material cost — these costs are intentionally out of scope.
- If `--no-json-log` was passed, you will not find `run_<timestamp>.jsonl` in the run directory.
