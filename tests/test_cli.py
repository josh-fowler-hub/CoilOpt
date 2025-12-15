import sys
from pathlib import Path

from coiloptimization_.main import main, run_config


def test_dry_run_outputs_json(capsys):
    p = Path("docs/example_input.toml")
    rc = run_config(p, dry_run=True)
    assert "provenance" in rc


def test_main_exit_code():
    rv = main(["docs/example_input.toml", "--dry-run"])
    assert rv == 0


def test_dry_run_emits_no_deprecation_warning():
    import warnings

    p = Path("docs/example_input.toml")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        run_config(p, dry_run=True)
        # ensure no DeprecationWarning about utcnow remains
        assert not any(isinstance(x.message, DeprecationWarning) for x in w)


def test_main_prints_summary(capsys):
    rv = main(["docs/example_input.toml", "--dry-run"])
    captured = capsys.readouterr()
    # dry-run currently prints the resolved config JSON; check that schema_version is present
    assert "schema_version" in captured.out
