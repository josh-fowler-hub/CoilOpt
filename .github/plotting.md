# Plotting & Figures for Reports

This document describes the set of plots we want produced for each optimization run and guidance for generating them in `src/coiloptimization_/reporting.py`.

## Goals

- Provide quick visual diagnostics of optimizer progress and final design performance.
- Produce publication-ready PNG figures stored in `results/<run_id>/figures/` and referenced from `report.md`.
- Keep plotting optional (gracefully degrade if `matplotlib` is unavailable).

## Figure list (recommended filenames)

- `objective_vs_start.png` — best objective (or objective per-start) vs multi-start index.
- `objective_vs_iter.png` — objective trace vs optimizer iteration for the final local run (or best run).
- `constraint_violations_hist.png` — histogram of constraint violation magnitudes across evaluated candidates/starts.
- `temp_profile_x.png` — temperature profile along coil length (hot bulk, outer fluid T_inf, inner/outer wall temps) for `x_opt`.
- `local_q_vs_x.png` — local heat flux (W/m2) vs axial coordinate for `x_opt` and optionally multiple candidate designs.
- `cumulative_Q_vs_x.png` — cumulative heat transferred along coil length for `x_opt`.
- `pressure_drop_vs_x.png` — pressure-drop accumulation or single-value bar for `x_opt` (plus breakdown if available).
- `sensitivity_oneway.png` — one-way sensitivity (tornado) for a short list of important inputs (e.g., `D_o`, `p`, `N`).
- `pareto_front.png` — reserved for multi-objective sweeps when additional objectives are explicitly supported. (Not used in the current single-objective heat-transfer optimization.)
- `design_schematic.png` — simple 2D schematic of coil geometry (coil diameter, tube OD, pitch, turns) annotated with key numbers.

## Plot detail & intent

- `objective_vs_start.png`: scatter + line of best-so-far objective after each completed start; annotate best final value and run_id. Useful to show multi-start overhead.
- `objective_vs_iter.png`: line plot of objective value per iteration for the final refined run (smooth with markers). If many iterations, downsample or plot log-scale for time.
- `constraint_violations_hist.png`: show counts and magnitudes for constraint violations (negative = slack, positive = violation) so users can see which constraints are active.
- `temp_profile_x.png`: plot three (or more) curves on same axis: hot-fluid bulk T(x), outer-fluid T_inf(x) (profile), and wall inner/outer T(x). Use twin-axis to annotate local `U(x)` or `q''(x)` if helpful.
- `local_q_vs_x.png` & `cumulative_Q_vs_x.png`: show where heat is being transferred; can reveal diminishing returns along coil length.
- `sensitivity_oneway.png`: for each parameter, run +/- delta (e.g., 5–10%) and plot relative change in objective; order bars by magnitude.
- `pareto_front.png`: color points by feasibility and annotate extremes; useful when offering alternate designs to users.
- `design_schematic.png`: generate a labeled matplotlib drawing (circles/lines) or simple SVG showing `D_c`, `D_o`, `p`, `N` and total length `L`.

## Implementation guidance

- Use `matplotlib` as primary plotting library; optionally use `seaborn` for nicer histograms if available.
- Encapsulate each figure as a function in `src/coiloptimization_/reporting.py` that accepts `result` and `cfg` and writes a PNG to `figures/`.
- Each plotting function should:
  - Create the `figures/` directory if needed.
  - Use `fig.savefig(path, dpi=150, bbox_inches='tight')`.
  - Return the relative path used so `report.md` can embed the image.
- Add a small wrapper `safe_plot(fn, *args, **kwargs)` that catches `ImportError` or plotting failures and logs a warning instead of failing the run.

## Data inputs to figures

- `result` object should contain at minimum:
  - `x_opt` (design variables) and `x_history` (if available)
  - `objective_history` or `start_results` with per-start objectives
  - `y_grid` (axial coordinate), `T_hot_x`, `T_inf_x`, `T_wall_inner_x`, `T_wall_outer_x`, `q_x`, `cum_Q_x` for `x_opt` (these can be computed by `model.solve_energy_balance_with_local()` when generating figures)
  - `constraints_evaluations` and `pressure_drop` for `x_opt`

## File naming, sizes, and DPI

- Default output folder: `results/<run_id>/figures/`.
- PNG size: `figsize=(6.5, 4)` inches, `dpi=150` (suitable for reports and slides).
- Filenames should be short, lowercase, and descriptive as listed above.

## Report embedding & markdown

- In `report.md` include figures using relative links:

  ![Temperature profile](figures/temp_profile_x.png)

- Include a short caption under each figure describing what it shows and any key numeric callouts.

## Testing & validation

- Unit test: generate figures for a trivial/stub `result` and assert that the PNG files were created and non-empty.
- Integration test: run `run_config()` with `--no-save` disabled and `n_starts=2` on a fast stub model and assert `report.md` references generated figure filenames.

## Optional: interactive debugging

- Provide a small helper `reporting.preview_figures(result, cfg)` that opens figures in an interactive backend for local debugging (only when `DISPLAY` available).

## Export API sketch (in `reporting.py`)

```py
def generate_all_figures(result, cfg, out_dir):
    figures = []
    figures.append(plot_objective_vs_start(result, cfg, out_dir))
    figures.append(plot_temp_profile(result, cfg, out_dir))
    ...
    return figures
```

## Notes

- Keep plotting modular from heavy compute — compute arrays in `model` and pass purely numerical arrays to plotting functions.
- Favor reproducibility: include `run_id` and timestamp in saved figure metadata (PNG text chunk or file naming) when possible.
