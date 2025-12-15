# Optimization Design — CoilOptimization

## Goal

Formulate and implement a constrained nonlinear optimizer to choose coil geometry x = [D_o, t, D_c, p, N, ...] that maximizes heat transfer from the hot internal gas to the external water subject to hydraulic, thermal, and geometric constraints. Pumping power and material cost are not modeled and must not be included in inputs or outputs — hot mass flow and inlet temperature are provided as inputs.

## Problem statement

- Design vector x contains continuous variables (diameters, pitch) and discrete integer variables (number of turns `N`).
- Objective examples (primary focus):
  - Maximize Q(x): heat transferred from hot gas to external fluid (primary objective).

Notes: This project focuses exclusively on maximizing overall heat transfer. Cost-based objectives are outside the scope and are not supported.

- Constraints g_i(x) <= 0 include pressure drop, maximum wall temperature, manufacturing bounds, and maximum velocity.

## Solver choices

- Primary: SciPy `optimize.minimize` with `SLSQP` or `trust-constr` for nonlinear constraints and bounds.
- Optional global/multi-start: `scipy.optimize.differential_evolution` for global sampling, `shgo`, or `nlopt` (if installed) for global/local hybrid.
- Integer handling: treat `N` as continuous during optimization then round and repair, or use mixed-integer heuristics (outer loop over plausible integer `N` values).

## Formulation details

- Transform maximization into minimization by negating the objective when using SciPy.
- Use bounds (box constraints) for each continuous design variable.
- Express constraints as functions returning non-positive values: g(x) = constraint_value - limit <= 0.
- Provide analytic gradients where possible; otherwise use `scipy`'s finite-difference Jacobians.

## Gradients & Jacobians

- Provide derivatives for geometry-related quantities analytically (areas, lengths).
- For convective correlations (Nu), provide analytic derivatives where feasible; otherwise compute finite differences but reuse cached function evaluations to limit cost.
- Allow `approx_grad=True` fallback when analytic gradients are not available.

## Multi-start and global strategy

- Use Latin Hypercube or Sobol sampling to generate `k` start points within bounds.
- Run local solver from each start in parallel (multiprocessing or joblib).
- Keep best feasible solution; optionally refine with higher-precision `trust-constr` and tighter tolerances.

## Constraint handling & feasibility

- Soft feasibility: allow penalty terms in objective for minor constraint violations during global search.
- Hard feasibility: final solution must satisfy constraints within tolerances; implement a `repair()` function to adjust variables (e.g., increase diameter) if a constraint is violated after rounding integers.

## Integer variables & rounding

- Strategy A (outer loop): loop over candidate integer `N` within bounds (coarse sampling), optimize continuous variables for each, then pick best.
- Strategy B (relax-and-round): optimize continuous relaxation, round integers, repair and re-optimize continuous variables while holding integers fixed.
- Prefer Strategy A for small integer ranges (e.g., N <= few hundreds), Strategy B for large ranges.

## Objective & constraint evaluation caching

- Cache expensive evaluations keyed by rounded design vector (or hash of floating vector with tolerance) to avoid repeated heavy model calls during multi-start and gradient approximations.
- Use LRU cache with small capacity or custom dict with TTL per optimizer run.

## Performance & parallelism

- Vectorize objective evaluation where possible to enable batched multi-start evaluation.
- Run independent local solves in parallel using `concurrent.futures.ProcessPoolExecutor` to avoid GIL issues.
- Limit concurrency to available CPU cores minus one.

## Numerical tolerances and stopping

- Default solver tolerances: `ftol=1e-6`, `xtol=1e-6` adjustable via `solver` TOML options.
- Max iterations configurable; record solver diagnostics and termination reasons in output.

## Provenance & reproducibility

- Record solver name/version, random seeds, start points, and hardware metadata in results.
- Save final and intermediate best solutions to disk as JSON/TOML for audit.

## Output

- `result` object containing: `x_opt`, `objective`, `constraints`, `feasible` flag, `solver_info` (niter, success, message), `provenance` (input file, seed, start_points).
- Utility to write outputs to `results/` with timestamped filenames.

- Integration with model

- The optimizer calls model primitives: `geometry(x)`, `fluid_props(T)` (hot gas), `external_props` (water or bath), `U_overall(...)`, `Q_from_U(...)`, and `pressure_drop(...)` (internal flow). The hot gas mass flow and inlet temperature are provided in the TOML; the optimizer computes the outlet temperature (via energy balance) or uses LMTD for single-pass designs.
- Keep optimizer code separate from model math; pass model functions as callables to the optimizer wrapper.

## Testing strategy

- Unit tests for objective and each constraint function using known analytic cases.
- Integration test: run optimizer on `docs/example_input.toml` with a reduced search budget and assert feasibility and nonzero heat transfer improvement over a baseline.

## Implementation plan (tasks)

1. Implement `src/coiloptimization_/optimize.py` with a `Optimizer` class wrapping SciPy and multi-start logic.
2. Add simple `optimize_single_start()` taking initial guess, bounds, constraints, and returning local result.
3. Add multi-start runner with parallel execution and caching.
4. Implement integer handling utilities (`enumerate_integer_candidates`, `round_and_repair`).
5. Add CLI glue to accept solver options from TOML and run optimizer.

---

If you want, I can implement the `Optimizer` skeleton in `src/coiloptimization_/optimize.py` next (with a basic `SLSQP` run and a multi-start driver). Which do you prefer I implement first: the single-start solver or the multi-start/parallel wrapper?
