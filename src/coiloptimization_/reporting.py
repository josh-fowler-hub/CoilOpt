from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .types import Config

logger = logging.getLogger(__name__)


def _safe_import_matplotlib() -> bool:
    try:
        import matplotlib

        return True
    except Exception:
        return False


def generate_report(result: dict, cfg: Config, out_dir: Path, include_figures: bool = True) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.md"
    lines: List[str] = []

    # Provenance
    lines.append(f"# Optimization Report")
    lines.append("")
    lines.append("**Provenance:**")
    lines.append(f"- timestamp: {result.get('provenance', {}).get('timestamp', 'unknown')}")
    lines.append(f"- solver: {result.get('solver_info', {}).get('method')}")
    lines.append("")

    # Summary
    lines.append("**Run Summary:**")
    lines.append(f"- feasible: {result.get('feasible')}")
    lines.append(f"- objective: {result.get('objective')}")
    lines.append("")

    # Best design
    lines.append("**Best Design:**")
    x = result.get("x") or result.get("x_opt")
    if x:
        for k, v in x.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- (no design variables found)")
    lines.append("")

    # Key metrics
    lines.append("**Key Metrics:**")
    metrics = ["total_length_m", "external_area_m2", "pressure_drop"]
    for m in metrics:
        if m in result:
            lines.append(f"- {m}: {result[m]}")
    lines.append("")

    # Figures
    figures: List[str] = []
    if include_figures:
        if _safe_import_matplotlib():
            figures_dir = out_dir / "figures"
            figures_dir.mkdir(exist_ok=True)
            try:
                figures = generate_all_figures(result, cfg, figures_dir)
            except Exception:
                logger.exception("Plotting failed")
        else:
            lines.append("Note: plotting disabled because matplotlib not available.")

    if figures:
        lines.append("**Figures:**")
        for fig in figures:
            lines.append(f"- ![{fig}]({fig})")
        lines.append("")

    report_path.write_text("\n".join(lines))
    logger.info("Wrote report to %s", report_path)
    return report_path


def _plot_temp_profile(result: dict, cfg: Config, out_dir: Path) -> Optional[str]:
    import matplotlib.pyplot as plt

    y = result.get("y_grid")
    T_hot = result.get("T_hot_x")
    T_inf = result.get("T_inf_x")
    T_wi = result.get("T_wall_inner_x")
    T_wo = result.get("T_wall_outer_x")
    if not (y and T_hot and T_inf):
        return None

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(y, T_hot, label="T_hot")
    ax.plot(y, T_inf, label="T_inf")
    if T_wi:
        ax.plot(y, T_wi, label="T_wall_inner")
    if T_wo:
        ax.plot(y, T_wo, label="T_wall_outer")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("Temperature (C)")
    ax.legend()
    figs = _ensure_fig_dir(out_dir)
    path = figs / "temp_profile_x.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return f"figures/{path.name}"


def generate_all_figures(result: dict, cfg: Config, out_dir: Path) -> List[str]:
    """Generate all available figures for a run and return relative paths list."""
    figs: List[str] = []
    plot_fns = [
        plot_objective_vs_start,
        plot_objective_vs_iter,
        plot_constraint_violations_hist,
        _plot_temp_profile,
        plot_local_q_vs_x,
        plot_cumulative_Q_vs_x,
        plot_pressure_drop_vs_x,
        plot_sensitivity_oneway,
        plot_design_schematic,
    ]
    for fn in plot_fns:
        try:
            p = fn(result, cfg, out_dir)
            if p:
                figs.append(p)
        except Exception:
            logger.exception("Failed to generate figure %s", fn.__name__)
    return figs


def _ensure_fig_dir(out_dir: Path) -> Path:
    figs = out_dir / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    return figs


def plot_objective_vs_start(result: dict, cfg: Config, out_dir: Path) -> Optional[str]:
    import matplotlib.pyplot as plt
    import numpy as np

    starts = result.get("start_results")
    if not starts:
        return None
    objs = [s.get("objective") if isinstance(s, dict) else float(s) for s in starts]
    objs = np.array(objs, dtype=float)
    best = np.maximum.accumulate(objs)
    figs = _ensure_fig_dir(out_dir)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(np.arange(1, len(objs) + 1), objs, 'o-', label='start objective')
    ax.plot(np.arange(1, len(best) + 1), best, 'k--', label='best so far')
    ax.set_xlabel('start index')
    ax.set_ylabel('Objective (Q, W)')
    ax.legend()
    path = figs / 'objective_vs_start.png'
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return f"figures/{path.name}"


def plot_objective_vs_iter(result: dict, cfg: Config, out_dir: Path) -> Optional[str]:
    import matplotlib.pyplot as plt
    import numpy as np

    hist = result.get("objective_history")
    if not hist:
        return None
    hist = np.array(hist, dtype=float)
    figs = _ensure_fig_dir(out_dir)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(np.arange(len(hist)), hist, '-o')
    ax.set_xlabel('iteration')
    ax.set_ylabel('Objective (Q, W)')
    path = figs / 'objective_vs_iter.png'
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return f"figures/{path.name}"


def plot_constraint_violations_hist(result: dict, cfg: Config, out_dir: Path) -> Optional[str]:
    import matplotlib.pyplot as plt
    import numpy as np

    v = result.get('constraint_violations')
    if not v:
        return None
    # accept dicts or numeric lists
    if isinstance(v, dict):
        vals = list(v.values())
    else:
        vals = list(v)
    vals = np.array(vals, dtype=float)
    figs = _ensure_fig_dir(out_dir)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.hist(vals, bins=20)
    ax.set_xlabel('Constraint violation (positive = violation)')
    ax.set_ylabel('Count')
    path = figs / 'constraint_violations_hist.png'
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return f"figures/{path.name}"


def plot_local_q_vs_x(result: dict, cfg: Config, out_dir: Path) -> Optional[str]:
    import matplotlib.pyplot as plt
    y = result.get('y_grid')
    q = result.get('q_x')
    if not (y and q):
        return None
    fig_dir = _ensure_fig_dir(out_dir)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(y, q)
    ax.set_xlabel('x (m)')
    ax.set_ylabel("local q'' (W/m2)")
    path = fig_dir / 'local_q_vs_x.png'
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return f"figures/{path.name}"


def plot_cumulative_Q_vs_x(result: dict, cfg: Config, out_dir: Path) -> Optional[str]:
    import matplotlib.pyplot as plt
    y = result.get('y_grid')
    cum = result.get('cum_Q_x')
    if not (y and cum):
        return None
    fig_dir = _ensure_fig_dir(out_dir)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(y, cum)
    ax.set_xlabel('x (m)')
    ax.set_ylabel('Cumulative Q (W)')
    path = fig_dir / 'cumulative_Q_vs_x.png'
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return f"figures/{path.name}"


def plot_pressure_drop_vs_x(result: dict, cfg: Config, out_dir: Path) -> Optional[str]:
    import matplotlib.pyplot as plt
    figs = _ensure_fig_dir(out_dir)
    pd = result.get('pressure_drop')
    pd_profile = result.get('pressure_drop_profile')
    if pd_profile is not None:
        import numpy as np

        fig, ax = plt.subplots(figsize=(6.5, 4))
        ax.plot(np.arange(len(pd_profile)), pd_profile)
        ax.set_xlabel('segment')
        ax.set_ylabel('Pressure drop (Pa)')
        path = figs / 'pressure_drop_vs_x.png'
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return f"figures/{path.name}"
    elif pd is not None:
        fig, ax = plt.subplots(figsize=(6.5, 4))
        ax.bar(['pressure_drop'], [pd])
        ax.set_ylabel('Pressure drop (Pa)')
        path = figs / 'pressure_drop_vs_x.png'
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return f"figures/{path.name}"
    return None


def plot_sensitivity_oneway(result: dict, cfg: Config, out_dir: Path) -> Optional[str]:
    import matplotlib.pyplot as plt
    sens = result.get('sensitivity')
    if not sens:
        return None
    items = list(sens.items())
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    fig_dir = _ensure_fig_dir(out_dir)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.barh(names, vals)
    ax.set_xlabel('Relative change in objective (%)')
    path = fig_dir / 'sensitivity_oneway.png'
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return f"figures/{path.name}"


def plot_design_schematic(result: dict, cfg: Config, out_dir: Path) -> Optional[str]:
    import matplotlib.pyplot as plt
    fig_dir = _ensure_fig_dir(out_dir)
    D_c = None
    D_o = None
    p = None
    N = None
    x = result.get('x') or result.get('x_opt')
    if x:
        D_c = x.get('D_c_m') or x.get('D_c')
        D_o = x.get('D_o_m') or x.get('D_o')
        p = x.get('pitch_m') or x.get('p')
        N = x.get('N')
    # Draw a simple 2D schematic
    fig, ax = plt.subplots(figsize=(6.5, 4))
    # coil outer circle
    if D_c:
        circle = plt.Circle((0, 0), D_c / 2.0, fill=False, linewidth=2)
        ax.add_patch(circle)
    if D_o:
        tube = plt.Circle((0, 0), D_o / 2.0, fill=False, linestyle='--')
        ax.add_patch(tube)
    ax.set_aspect('equal')
    ax.set_xlim(-1.1 * (D_c or 1.0) / 2.0, 1.1 * (D_c or 1.0) / 2.0)
    ax.set_ylim(-1.1 * (D_c or 1.0) / 2.0, 1.1 * (D_c or 1.0) / 2.0)
    title = 'Design schematic'
    if N is not None:
        title += f' (N={N})'
    ax.set_title(title)
    if p is not None:
        ax.text(0.05, 0.95, f'pitch={p:.3f} m', transform=ax.transAxes, verticalalignment='top')
    path = fig_dir / 'design_schematic.png'
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return f"figures/{path.name}"
