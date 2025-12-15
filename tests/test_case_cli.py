from pathlib import Path
import json

from coiloptimization_ import main as coil_main


def test_case_cli_run(tmp_path: Path, capsys):
    # copy the example input to a tmp folder to simulate a test case
    case_dir = tmp_path / "example1"
    case_dir.mkdir()
    src = Path("test_case/example1/input.toml")
    dst = case_dir / "input.toml"
    dst.write_text(src.read_text())

    out_dir = tmp_path / "out"
    # run the CLI main with --output pointing to out_dir and report generation
    rc = coil_main.main([str(dst), "--output", str(out_dir), "--report", "--no-json-log"])
    assert rc == 0

    # capture stdout printed by main (banner + summary)
    captured = capsys.readouterr()
    assert "Objective Q" in captured.out

    # check output files
    assert out_dir.exists()
    # find a result json in out_dir
    results = list(out_dir.glob("*.json"))
    assert len(results) >= 1
    # report presence
    assert (out_dir / "report.md").exists()

    # basic sanity: parse result JSON to ensure objective key present
    with results[0].open() as fh:
        data = json.load(fh)
    assert "result" in data
    assert "objective" in data["result"] or "objective" in data
