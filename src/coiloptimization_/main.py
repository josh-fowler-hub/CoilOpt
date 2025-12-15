from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from . import config as config_module
from .types import Config


logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="coilopt")
    p.add_argument("input", help="Path to TOML input file")
    p.add_argument("-o", "--output", help="Path to write output JSON (default: results/<timestamp>_result.json)")
    p.add_argument("-m", "--method", help="Override solver method")
    p.add_argument("--maxiter", type=int, help="Override solver maxiter")
    p.add_argument("--seed", type=int, help="RNG seed")
    p.add_argument("-v", "--verbose", action="count", default=0, help="Increase logging verbosity")
    p.add_argument("--dry-run", action="store_true", help="Validate config and print resolved values, then exit")
    p.add_argument("--no-save", action="store_true", help="Run but do not write result files")
    p.add_argument("--resume", action="store_true", help="Resume from checkpoint in --output dir")
    p.add_argument("--n-starts", type=int, help="Override multi-start count")
    p.add_argument("--max-workers", type=int, help="Override parallel worker count for multi-start")
    p.add_argument("--log-file", help="Write detailed run log to file")
    p.add_argument("--no-json-log", action="store_true", help="Disable JSON-line event logging")
    p.add_argument("--report", action="store_true", help="Generate markdown report after run")
    return p


def setup_logging(verbosity: int = 0, log_file: Optional[str] = None) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logging.getLogger().addHandler(fh)


def run_config(cfg: Union[Config, str, Path], out_path: Optional[Union[str, Path]] = None, resume: bool = False, dry_run: bool = False, no_save: bool = False, report: bool = False, jsonl: bool = True) -> dict:
    # Load config
    if isinstance(cfg, (str, Path)):
        cfg = config_module.load_config(cfg)
    assert isinstance(cfg, Config)

    # Apply simple overrides are left to caller (main)

    # If dry-run, print resolved config and return
    result = {"provenance": {"timestamp": datetime.now(timezone.utc).isoformat()}, "feasible": True}
    if dry_run:
        print(json.dumps(cfg.__dict__, default=lambda o: o.__dict__, indent=2))
        return result

    # Prepare output directory and paths
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if out_path is not None:
        out_path = Path(out_path)
        if out_path.suffix:
            out_dir = out_path.parent
        else:
            out_dir = out_path
    else:
        out_dir = Path("results") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # If multi-start requested, run optimizer and emit events/checkpoints
    if getattr(cfg.solver, 'n_starts', 0) and cfg.solver.n_starts > 1:
        from .optimize import Optimizer

        opt = Optimizer(cfg)
        db = cfg.design_bounds
        bounds = [
            (db.min_tube_od_m, db.max_tube_od_m),
            (db.min_wall_thickness_m, db.max_wall_thickness_m),
            (db.min_coil_diameter_m, db.max_coil_diameter_m),
            (db.min_pitch_m, db.max_pitch_m),
            (db.min_turns, db.max_turns),
        ]
        multi_res = opt.run_multi_start(bounds, n_starts=cfg.solver.n_starts, out_dir=out_dir, resume=resume, seed=cfg.solver.seed if hasattr(cfg.solver, 'seed') else None, jsonl=jsonl)
        result.update({"multi_start": multi_res, "feasible": True})
        # if report requested, generate it
        if report:
            try:
                from .reporting import generate_report

                generate_report(result, cfg, out_dir, include_figures=True)
            except Exception:
                logger.exception("Failed to generate report")
        # write summary result JSON
        out_file = out_dir / f"result_{run_id}.json"
        with out_file.open("w") as fh:
            json.dump({"config": cfg.__dict__, "result": result}, fh, indent=2, default=lambda o: o.__dict__)
        result["output_path"] = str(out_file)
        return result

    # Simple stub optimizer: pick midpoint geometry and estimate Q by U * A * LMTD
    db = cfg.design_bounds
    D_o = 0.5 * (db.min_tube_od_m + db.max_tube_od_m)
    p = 0.5 * (db.min_pitch_m + db.max_pitch_m)
    D_c = 0.5 * (db.min_coil_diameter_m + db.max_coil_diameter_m)
    N = db.min_turns

    # Derived geometry
    import math

    ell_turn = math.hypot(math.pi * D_c, p)
    L = N * ell_turn
    A_o = math.pi * D_o * L

    # Temperature driving potential: simple LMTD using inlet and outlet if available
    Tin = cfg.process.inlet_temp_c
    Tout = cfg.process.outlet_temp_c if cfg.process.outlet_temp_c is not None else (Tin - 10.0)
    # assume external bath at 20C
    T_ext = 20.0
    dT1 = Tin - T_ext
    dT2 = Tout - T_ext
    if dT1 == dT2:
        LMTD = dT1
    else:
        LMTD = (dT1 - dT2) / (math.log(dT1 / dT2)) if dT1 * dT2 > 0 else max(dT1, dT2)

    # Very simple U estimation
    U = 100.0  # W/m2K default stub
    Q = U * A_o * LMTD

    result.update(
        {
            "x": {"D_o_m": D_o, "pitch_m": p, "D_c_m": D_c, "N": N},
            "objective": {"Q_w": Q, "U_w_m2k": U},
            "feasible": True,
            "solver_info": {"method": cfg.solver.method, "maxiter": cfg.solver.maxiter},
        }
    )

    # Write output if requested
    if not no_save:
        if out_path is None:
            out_dir = Path("results")
            out_dir.mkdir(exist_ok=True)
            out_path = out_dir / f"result_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        out_path = Path(out_path)
        # If user provided a directory (or a path without suffix), create a result file inside it
        if out_path.exists() and out_path.is_dir() or out_path.suffix == "":
            out_dirp = out_path
            out_dirp.mkdir(parents=True, exist_ok=True)
            out_path = out_dirp / f"result_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        with out_path.open("w") as fh:
            json.dump({"config": cfg.__dict__, "result": result}, fh, indent=2, default=lambda o: o.__dict__)
        logger.info("Wrote result to %s", out_path)
        result["output_path"] = str(out_path)

        # generate report for single-run if requested
        if report:
            try:
                from .reporting import generate_report

                generate_report(result, cfg, out_dir, include_figures=True)
            except Exception:
                logger.exception("Failed to generate report")

    return result

def print_banner() -> None:
    banner = """
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║                          CoilOpt                               ║
║            Coil geometry heat-transfer optimizer               ║
║          Focused on maximizing overall heat transfer (Q)       ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main(argv: Optional[list] = None) -> int:
    print_banner()
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(args.verbose or 0, args.log_file)
    try:
        cfg = config_module.load_config(args.input)
    except config_module.ConfigError as e:
        logger.error("Invalid config: %s - %s", e.field, e.message)
        return 1

    # apply small overrides
    if args.method:
        cfg.solver.method = args.method
    if args.maxiter:
        cfg.solver.maxiter = args.maxiter
    if args.seed:
        cfg.solver.seed = args.seed
    if args.n_starts:
        setattr(cfg.solver, "n_starts", args.n_starts)
    if args.max_workers:
        setattr(cfg.solver, "max_workers", args.max_workers)

    if args.dry_run:
        run_config(cfg, dry_run=True)
        return 0

    try:
        res = run_config(cfg, out_path=args.output, resume=args.resume, dry_run=False, no_save=args.no_save, report=args.report, jsonl=(not args.no_json_log))
    except Exception as e:
        logger.exception("Run failed: %s", str(e))
        return 2

    # print short summary
    print("Result: feasible=" + str(res.get("feasible", False)))
    print(f"Objective Q = {res['objective']['Q_w']:.2f} W")
    if "output_path" in res:
        print("Wrote output:", res["output_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

