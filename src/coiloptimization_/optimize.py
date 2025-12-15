"""Optimizer wrapper for CoilOptimization.

Provides a single-start SLSQP optimizer and a simple multi-start runner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple
import math

import numpy as np
from scipy.optimize import minimize

from . import model, profiles
from . import logging as coil_logging
import json
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class OptimizeResult:
    x: Dict[str, float]
    objective: float
    success: bool
    message: str
    solver_info: Dict


class Optimizer:
    def __init__(self, cfg):
        self.cfg = cfg

    def design_vector_to_dict(self, x: np.ndarray) -> Dict:
        # x = [D_o, t, D_c, p, N]
        return dict(D_o=float(x[0]), t=float(x[1]), D_c=float(x[2]), p=float(x[3]), N=int(round(x[4])))

    def evaluate(self, x: np.ndarray) -> Tuple[float, Dict]:
        """Evaluate objective and diagnostics for design vector x.

        Returns (Q, diagnostics)
        """
        d = self.design_vector_to_dict(x)
        cfg = self.cfg
        # basic feasibility checks
        D_o = d["D_o"]
        t = d["t"]
        D_i = D_o - 2.0 * t
        if D_i <= 0 or t <= 0:
            return -1e6, {"feasible": False, "reason": "invalid geometry"}

        N = d["N"]
        L = model.total_length(N, d["D_c"], d["p"])

        # external temperature profile
        if cfg.external and cfg.external.temperature_profile:
            tp = cfg.external.temperature_profile
            if tp.get("equation"):
                Tinf = profiles.make_profile_from_equation(tp["equation"])
            elif tp.get("points"):
                Tinf = profiles.make_profile_from_points(tp["points"])
            else:
                # allow direct string profile as equation
                Tinf = profiles.make_profile_from_equation(tp)
        else:
            # bath or fixed external temperature; create a two-arg callable for compatibility
            T_bath = cfg.external.temperature_c if cfg.external and cfg.external.temperature_c is not None else cfg.process.inlet_temp_c - 50.0
            Tinf = lambda x, z=None: T_bath

        # material conductivity: prefer material name lookup when available
        if cfg.material and isinstance(cfg.material, dict) and cfg.material.get("name"):
            mat = model.get_material_properties(cfg.material.get("name"), cfg.process.inlet_temp_c)
            k_w = mat.get("k_w", cfg.material.get("k_w", 15.0))
        else:
            k_w = cfg.material.get("k_w", 15.0) if cfg.material else 15.0

        # local calculation closure
        def compute_local(x_pos: float, Th_local: float):
            # determine effective wall thickness: respect material minimum if provided
            t_eff = t
            if cfg.material and isinstance(cfg.material, dict) and cfg.material.get("wall_thickness_m") is not None:
                t_eff = max(t, float(cfg.material.get("wall_thickness_m")))
            D_i_local = D_o - 2.0 * t_eff
            # compute vertical coordinate (z) along coil from axial x position
            ell_turn = model.turn_length(d['D_c'], d['p'])
            rise_per_length = d['p'] / ell_turn if ell_turn > 0 else 0.0
            direction = cfg.coil.get('direction', 'up') if cfg.coil else 'up'
            sign = 1.0 if direction.lower().startswith('u') else -1.0
            entry_height = float(cfg.coil.get('entry_height_m', 0.0)) if cfg.coil else 0.0
            z_pos = entry_height + sign * (rise_per_length * x_pos)
            # Tinf: prefer profile that accepts (x, z); fallback to x if profile expects single coord
            try:
                Tinf_loc = Tinf(x_pos, z_pos)
            except TypeError:
                Tinf_loc = Tinf(z_pos)

            # initialize wall temps as bulk/bath guesses
            Twi = Th_local
            Two = Tinf_loc

            # iterate to evaluate fluid properties at film temperatures (T_film = 0.5*(bulk + wall))
            for _ in range(3):
                # internal film temperature
                Tfilm_i = 0.5 * (Th_local + Twi)
                if cfg.fluid.name:
                    rho_i, cp_i, mu_i, k_i, Pr_i = model.get_fluid_properties(cfg.fluid.name, Tfilm_i)
                else:
                    rho_i = cfg.fluid.density_kg_m3 if cfg.fluid.density_kg_m3 is not None else 1.0
                    mu_i = cfg.fluid.viscosity_pa_s if cfg.fluid.viscosity_pa_s is not None else 1e-3
                    k_i = cfg.fluid.thermal_conductivity_w_mk if cfg.fluid.thermal_conductivity_w_mk is not None else 0.1
                    cp_i = cfg.fluid.specific_heat_j_kgk if cfg.fluid.specific_heat_j_kgk is not None else 1000.0
                    Pr_i = model.prandtl(cp_i, mu_i, k_i)

                u_i, Re_i = model.reynolds_from_mass_flow(cfg.fluid.mass_flow_kg_s, rho_i, D_i_local, mu_i)
                Nu_i = model.nusselt_internal(Re_i, Pr_i, heating=True)
                h_i = model.h_from_nusselt(Nu_i, k_i, D_i_local)

                # external film temperature
                Tfilm_o = 0.5 * (Tinf_loc + Two)
                if cfg.external and cfg.external.mass_flow_kg_s:
                    if cfg.external.name:
                        rho_o, cp_o, mu_o, k_o, Pr_o = model.get_fluid_properties(cfg.external.name, Tfilm_o)
                    else:
                        rho_o = cfg.external.density_kg_m3 if cfg.external.density_kg_m3 is not None else 1000.0
                        mu_o = cfg.external.viscosity_pa_s if cfg.external.viscosity_pa_s is not None else 1e-3
                        k_o = cfg.external.thermal_conductivity_w_mk if cfg.external.thermal_conductivity_w_mk is not None else 0.6
                        cp_o = cfg.external.specific_heat_j_kgk if cfg.external.specific_heat_j_kgk is not None else 4182.0
                        Pr_o = model.prandtl(cp_o, mu_o, k_o)
                    A_char = 1.0
                    u_o = cfg.external.mass_flow_kg_s / (rho_o * A_char)
                    Re_D = rho_o * u_o * D_o / mu_o
                    Nu_o = model.nusselt_external(Re_D, Pr_o)
                    h_o = model.h_from_nusselt(Nu_o, k_o, D_o)
                else:
                    # bath or fixed external temperature: use lookup by name if provided
                    if cfg.external and cfg.external.name:
                        _, _, _, k_o, _ = model.get_fluid_properties(cfg.external.name, Tfilm_o)
                    else:
                        k_o = 0.6
                    h_o = 100.0

                # recompute wall temps for updated h_i/h_o
                Twi_new, Two_new = model.wall_temperatures(Th_local, Tinf_loc, h_i, h_o, D_i, D_o, k_w)
                # check convergence (simple)
                if abs(Twi_new - Twi) < 1e-3 and abs(Two_new - Two) < 1e-3:
                    Twi, Two = Twi_new, Two_new
                    break
                Twi, Two = Twi_new, Two_new

            # overall U and q'' (based on converged h_i/h_o)
            U_loc = model.U_overall(h_i, h_o, D_i, D_o, k_w)
            qpp = U_loc * (Th_local - Tinf_loc)
            return {
                "U": U_loc,
                "h_i": h_i,
                "h_o": h_o,
                "Twi": Twi,
                "Two": Two,
                "qpp": qpp,
                "rho_i": rho_i,
                "mu_i": mu_i,
                "rho_o": (rho_o if 'rho_o' in locals() else None),
                "mu_o": (mu_o if 'mu_o' in locals() else None),
                "t_eff": t_eff,
                "D_i_local": D_i_local,
            }

        # run energy balance with compute_local
        # get inlet properties (use named material lookup when available)
        if cfg.fluid.name:
            rho_in, cp_in, mu_in, k_in, _ = model.get_fluid_properties(cfg.fluid.name, cfg.process.inlet_temp_c)
        else:
            rho_in = cfg.fluid.density_kg_m3 if cfg.fluid.density_kg_m3 is not None else 1.0
            cp_in = cfg.fluid.specific_heat_j_kgk if cfg.fluid.specific_heat_j_kgk is not None else 1000.0
            mu_in = cfg.fluid.viscosity_pa_s if cfg.fluid.viscosity_pa_s is not None else 1e-3

        xs, Ths, = model.solve_energy_balance_with_local(m_dot=cfg.fluid.mass_flow_kg_s, cp=cp_in, Tin=cfg.process.inlet_temp_c, L=L, D_o=D_o, local_calc=compute_local, nsteps=500)

        Tout = Ths[-1]
        Q = cfg.fluid.mass_flow_kg_s * cp_in * (cfg.process.inlet_temp_c - Tout)

        # pressure drop (use inlet properties)
        _, Re = model.reynolds_from_mass_flow(cfg.fluid.mass_flow_kg_s, rho_in, D_i, mu_in)
        f = model.friction_factor(Re)
        dp = model.pressure_drop(cfg.fluid.mass_flow_kg_s, rho_in, D_i, L, f)

        # max wall temp check: evaluate along xs using compute_local with Ths to get Two
        Tw_outers = [compute_local(xi, Thi)["Two"] for xi, Thi in zip(xs, Ths)]
        max_wall_temp = max(Tw_outers)

        # expose the final local calculation at the outlet for diagnostics
        last_local = compute_local(xs[-1], Ths[-1])

        diagnostics = {"Q": Q, "dp": dp, "max_wall_temp": max_wall_temp, "Tout": Tout}
        diagnostics["last_local"] = last_local
        return Q, diagnostics

    def objective_fn(self, x: np.ndarray) -> float:
        Q, diag = self.evaluate(x)
        # negate for minimizer
        return -float(Q)

    def constraint_pressure(self, x: np.ndarray) -> float:
        _, diag = self.evaluate(x)
        # If evaluation failed or did not return 'dp', treat as violated (large dp)
        dp = diag.get("dp") if isinstance(diag, dict) else None
        if dp is None:
            # return negative value to indicate violation
            return -1e6
        return self.cfg.constraints.max_pressure_drop_pa - dp

    def constraint_wall_temp(self, x: np.ndarray) -> float:
        _, diag = self.evaluate(x)
        if self.cfg.constraints.max_surface_temp_c is None:
            return 1e6
        max_wall_temp = diag.get("max_wall_temp") if isinstance(diag, dict) else None
        if max_wall_temp is None:
            # treat as violated
            return -1e6
        return self.cfg.constraints.max_surface_temp_c - max_wall_temp

    def optimize_single_start(self, x0: np.ndarray, bounds: List[Tuple[float, float]], maxiter: int = 200) -> OptimizeResult:
        cons = [
            {"type": "ineq", "fun": self.constraint_pressure},
            {"type": "ineq", "fun": self.constraint_wall_temp},
        ]

        res = minimize(self.objective_fn, x0, bounds=bounds, constraints=cons, options={"maxiter": maxiter, "disp": False})
        xdict = self.design_vector_to_dict(res.x)
        Q, diag = self.evaluate(res.x)
        return OptimizeResult(x=xdict, objective=Q, success=res.success, message=res.message, solver_info={"nfev": res.nfev, "nit": res.nit if hasattr(res, 'nit') else None})

    def run_multi_start(self, bounds: List[Tuple[float, float]], n_starts: int = 4, out_dir: Optional[Path] = None, resume: bool = False, seed: Optional[int] = None, jsonl: bool = True, max_retries: int = 2, backoff_base: float = 0.1) -> Dict:
        """Run a simple sequential multi-start driver, emitting JSON events and writing checkpoints.

        Returns a dict with best result and start summaries.
        """
        rng = np.random.RandomState(seed or (self.cfg.solver.seed if hasattr(self.cfg.solver, 'seed') else None))
        if out_dir is None:
            out_dir = Path('results')
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        events_path = out_dir / f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
        checkpoint = out_dir / "checkpoint.json"
        if not jsonl:
            events_path = None

        # Planned starts: either loaded from checkpoint when resuming, or generated now.
        planned_starts = []
        start_summaries: List[Dict] = []
        completed = 0

        if resume and checkpoint.exists():
            try:
                cp = json.loads(checkpoint.read_text())
                ps = cp.get("planned_starts")
                if ps and len(ps) > 0:
                    planned_starts = [np.array(x, dtype=float) for x in ps]
                    completed = int(cp.get("completed", 0))
                    start_summaries = cp.get("starts", [])
            except Exception:
                # fall back to generating new planned starts
                planned_starts = []

        if not planned_starts:
            for _ in range(n_starts):
                x0 = np.array([rng.uniform(a, b) for (a, b) in bounds], dtype=float)
                # ensure integer for N (last entry)
                x0[-1] = int(round(x0[-1]))
                planned_starts.append(x0)
            # write initial checkpoint with planned starts
            cp0 = {"timestamp": datetime.now(timezone.utc).isoformat(), "planned_starts": [x.tolist() for x in planned_starts], "completed": 0, "starts": []}
            tmp0 = checkpoint.with_suffix('.tmp')
            tmp0.write_text(json.dumps(cp0))
            tmp0.replace(checkpoint)

        best = None
        start_summaries = []
        # iterate from 'completed' index through planned_starts
        import time

        for i in range(completed, len(planned_starts)):
            x0 = planned_starts[i]
            if jsonl and events_path is not None:
                coil_logging.write_json_event(events_path, 'start_run', {'start_index': i, 'x0': x0.tolist()})

            # attempt with retries/backoff on failure
            attempt = 0
            res = None
            while attempt <= max_retries:
                res = self.optimize_single_start(x0, bounds, maxiter=self.cfg.solver.maxiter)
                if res.success:
                    break
                # failed; if we have retries left, back off and retry
                attempt += 1
                if attempt <= max_retries:
                    sleep_time = backoff_base * (2 ** (attempt - 1))
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            # record
            start_summary = {'index': i, 'x': res.x, 'objective': res.objective, 'success': res.success, 'message': res.message, 'retries': attempt}
            start_summaries.append(start_summary)
            if jsonl and events_path is not None:
                coil_logging.write_json_event(events_path, 'local_solve_complete', start_summary)

            # update best
            if res.success:
                if best is None or res.objective > best['objective']:
                    best = start_summary.copy()

            # update completed and write checkpoint atomically
            completed = i + 1
            cp = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'completed': completed,
                'n_starts': len(planned_starts),
                'best': best,
                'starts': start_summaries,
                'planned_starts': [x.tolist() for x in planned_starts],
            }
            tmp = checkpoint.with_suffix('.tmp')
            tmp.write_text(json.dumps(cp))
            tmp.replace(checkpoint)

        if jsonl and events_path is not None:
            coil_logging.write_json_event(events_path, 'end_run', {'best': best, 'n_starts': n_starts})
        return {'best': best, 'starts': start_summaries, 'checkpoint': str(checkpoint), 'events': str(events_path) if events_path is not None else ''}
