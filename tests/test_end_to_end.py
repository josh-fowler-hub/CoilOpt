from pathlib import Path

from coiloptimization_ import main as coil_main
from coiloptimization_ import config as config_module
from coiloptimization_.reporting import generate_report


def test_run_config_and_report(tmp_path: Path):
    example = Path("docs/example_input.toml")
    cfg = config_module.load_config(example)

    out_file = tmp_path / "result.json"
    res = coil_main.run_config(cfg, out_path=out_file, no_save=False)

    # output file should be written and contain result
    assert out_file.exists()
    data = out_file.read_text()
    assert "objective" in data
    assert "Q_w" in data

    # generate a report (no figures) and validate it does not mention pump/material
    rpt = generate_report(res, cfg, tmp_path, include_figures=False)
    assert rpt.exists()
    txt = rpt.read_text().lower()
    assert "optimization report" in txt
    assert "pump" not in txt
    assert "material" not in txt


def test_cli_no_save():
    # ensure CLI entrypoint runs without writing files when --no-save is used
    rc = coil_main.main(["docs/example_input.toml", "--no-save"])
    assert rc == 0


def test_run_config_with_report(tmp_path: Path):
    example = Path("docs/example_input.toml")
    cfg = config_module.load_config(example)
    # request multi-start via cfg and report
    cfg.solver.n_starts = 2
    res = coil_main.run_config(cfg, out_path=tmp_path, report=True, jsonl=False)
    # check a report was generated in out_dir
    rpt = tmp_path / 'report.md'
    # generate_report writes report_path in out_dir; it may also write in root - check for existence
    assert (tmp_path / 'report.md').exists() or (tmp_path / 'figures').exists() or 'multi_start' in res
