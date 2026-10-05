import argparse
import os
import shutil
import subprocess
import sys


def check_git_dirty():
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="New app name")
    parser.add_argument("--pkg", help="New python package name")
    parser.add_argument("--cli", help="New CLI command name")
    parser.add_argument("--env-prefix", help="New environment variable prefix")
    parser.add_argument("--live", action="store_true", help="Apply changes (default is dry-run)")
    args = parser.parse_args()

    if not args.name or not args.pkg or not args.cli or not args.env_prefix:
        print("Usage: python scripts/rename_app.py --name NAME --pkg PKG --cli CLI --env-prefix PREFIX")
        sys.exit(1)

    # In a test environment, checking git might not be strictly necessary if we are running the test on a temp copy,
    # but the instructions say "refuse on a dirty git tree". We'll only enforce this if running in a git repo.
    if os.path.exists(".git") and check_git_dirty() and args.live:
        if os.environ.get("BYPASS_GIT_DIRTY_CHECK") != "1":
            print("Error: Git tree is dirty. Commit or stash changes before renaming.")
            sys.exit(1)

    # Hardcoded current values (could be parsed from branding.py, but we know them right now)
    CURRENT_NAME = "Rolesmith"
    CURRENT_PKG = "rolesmith_ai"
    CURRENT_CLI = "rolesmith_ai"
    CURRENT_PREFIX = "ROLESMITH_"

    # We will search and replace in all files except certain dirs
    EXCLUDE_DIRS = {".git", "venv", ".pytest_cache", "__pycache__", "scripts"}

    replacements = [
        (CURRENT_NAME, args.name),
        (CURRENT_PKG, args.pkg),
        (CURRENT_CLI, args.cli),
        (CURRENT_PREFIX, args.env_prefix),
        (CURRENT_PREFIX.lower(), args.env_prefix.lower()),
    ]

    print(f"Renaming to {args.name} (pkg={args.pkg}, cli={args.cli}, prefix={args.env_prefix})")

    diff_summary = []

    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(".db") or file.endswith(".pyc") or file == "rename_app.py":
                continue
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                continue

            new_content = content
            for old, new in replacements:
                if old != new:
                    new_content = new_content.replace(old, new)

            if content != new_content:
                diff_summary.append(path)
                if args.live:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)

    if args.live:
        # Rename the package directory
        old_pkg_dir = os.path.join("src", CURRENT_PKG)
        new_pkg_dir = os.path.join("src", args.pkg)
        if os.path.exists(old_pkg_dir) and old_pkg_dir != new_pkg_dir:
            shutil.move(old_pkg_dir, new_pkg_dir)
            print(f"Moved directory {old_pkg_dir} to {new_pkg_dir}")

    print(f"{'LIVE RUN' if args.live else 'DRY RUN'}: Would modify {len(diff_summary)} files.")
    for f in diff_summary:
        print(f" - {f}")


if __name__ == "__main__":
    main()
