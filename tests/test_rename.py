import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.mark.live
def test_rename_app_and_tests_pass():
    # We will copy the whole project into a temp dir and run rename_app
    project_root = Path(__file__).parent.parent

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir) / "project"

        # Copy everything except .git and venv to save time
        shutil.copytree(
            project_root,
            temp_root,
            ignore=shutil.ignore_patterns(".git", "venv", ".pytest_cache", "__pycache__"),
        )

        # Run rename_app.py
        rename_cmd = [
            "python",
            str(temp_root / "scripts" / "rename_app.py"),
            "--name",
            "NewApp",
            "--pkg",
            "newapp",
            "--cli",
            "newcli",
            "--env-prefix",
            "NEWAPP_",
            "--live",
        ]

        env = os.environ.copy()
        env["BYPASS_GIT_DIRTY_CHECK"] = "1"

        res = subprocess.run(
            rename_cmd,
            cwd=temp_root,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert res.returncode == 0, f"Rename script failed: {res.stderr}"

        # Run pytest inside the new project
        # Ensure pytest tests the renamed package by setting PYTHONPATH
        env["PYTHONPATH"] = str(temp_root / "src")
        pytest_cmd = [sys.executable, "-m", "pytest", "tests", "-k", "not test_rename"]

        # Wait, sys.executable in the test will be the venv's pytest
        res_pytest = subprocess.run(
            pytest_cmd,
            cwd=temp_root,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert res_pytest.returncode == 0, f"Tests failed after rename:\n{res_pytest.stdout}\n{res_pytest.stderr}"
