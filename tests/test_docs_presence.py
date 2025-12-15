from pathlib import Path


def test_docs_pages_exist():
    docs = Path('docs')
    expected = ['usage.md', 'cli.md', 'examples.md', 'report.md']
    for e in expected:
        p = docs / e
        assert p.exists(), f"Missing user doc: {p}"
