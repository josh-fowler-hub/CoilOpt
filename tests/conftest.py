"""Pytest configuration for tests.

Set a non-interactive matplotlib backend to avoid GUI/Pillow deprecation warnings
when tests create figures in headless CI environments.
"""
import os

# Prefer a non-interactive backend to avoid TkAgg/Pillow warnings in CI
os.environ.setdefault("MPLBACKEND", "agg")

def pytest_configure(config):
    # Ensure matplotlib picks up the backend early
    try:
        import matplotlib

        matplotlib.use(os.environ.get("MPLBACKEND", "agg"), force=True)
    except Exception:
        # If matplotlib isn't available, tests that need it will skip appropriately
        pass
from pathlib import Path
import sys


def pytest_configure():
    """Ensure `src/` is on sys.path so tests can import the package."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
