import tempfile
from pathlib import Path

from rolesmith_ai.config import ensure_dirs


def test_legacy_migration(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_home:
        # Mock Path.home() to temp_home
        monkeypatch.setattr(Path, "home", lambda: Path(temp_home))

        # Override APP_DIR for test context since it's already initialized at module load
        test_app_dir = Path(temp_home) / ".rolesmith_ai"
        monkeypatch.setattr("rolesmith_ai.config.APP_DIR", test_app_dir)
        monkeypatch.setattr("rolesmith_ai.config.SESSIONS_DIR", test_app_dir / "sessions")

        legacy_dir = Path(temp_home) / ".job-apply-mcp"
        legacy_dir.mkdir(parents=True)

        # Add some dummy files
        (legacy_dir / "config.json").write_text('{"legacy": true}')

        # Run migration
        ensure_dirs()

        # Check migration results
        assert test_app_dir.exists()
        print(f"Files in test_app_dir: {list(test_app_dir.iterdir())}")
        assert (test_app_dir / "config.json").exists()
        assert (test_app_dir / "config.json").read_text() == '{"legacy": true}'

        # Check marker
        marker = legacy_dir / "migrated_to_rolesmith_ai.txt"
        assert marker.exists()
