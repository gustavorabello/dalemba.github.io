from __future__ import annotations

import argparse
import errno
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from cleanup_icloud_duplicates import cleanup_target
from console_output import print_heading, print_kv, print_subheading


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "dalembinha.github.io"
DEFAULT_DEPLOY_REPO = BASE_DIR / "dalembinha.github.io"
DEFAULT_PRESERVE = (".git", ".gitignore")
DEPLOY_REPO_ENV = "DEPLOY_REPO"
DEPLOY_MESSAGE_ENV = "DEPLOY_COMMIT_MESSAGE"


def git_index_lock_path(repo: Path) -> Path:
    return repo / ".git" / "index.lock"


def git_operation_paths(repo: Path) -> list[Path]:
    git_dir = repo / ".git"
    candidates = (
        git_dir / "rebase-merge",
        git_dir / "rebase-apply",
        git_dir / "MERGE_HEAD",
        git_dir / "CHERRY_PICK_HEAD",
        git_dir / "REVERT_HEAD",
        git_dir / "REBASE_HEAD",
    )
    return [path for path in candidates if path.exists()]


def resolve_deploy_repo(explicit: str | None) -> Path:
    raw_value = explicit or os.environ.get(DEPLOY_REPO_ENV, "").strip()
    if raw_value:
        repo = Path(raw_value).expanduser().resolve()
        if not (repo / ".git").exists():
            raise SystemExit(f"Deploy repository is not a git repository: {repo}")
        return repo

    repo = DEFAULT_DEPLOY_REPO.resolve()
    if (repo / ".git").exists():
        return repo

    raise SystemExit(
        "Unable to locate the GitHub Pages repository inside this Pelican project. "
        f"Expected: {repo}. Move or clone the publish repo there, or set {DEPLOY_REPO_ENV} / --deploy-repo."
    )


def run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def git(repo: Path, *args: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return run_command(["git", "-C", str(repo), *args], capture_output=capture_output)


def ensure_git_index_unlocked(repo: Path) -> None:
    lock_file = git_index_lock_path(repo)
    if not lock_file.exists():
        return
    raise SystemExit(
        f"Git index lock detected at {lock_file}. "
        "Confirm no git process is using this repository, remove the lock file, and retry."
    )


def ensure_no_git_operation_in_progress(repo: Path) -> None:
    active_paths = git_operation_paths(repo)
    if not active_paths:
        return
    raise SystemExit(
        "Git repository has an operation in progress: {}. "
        "Finish or abort that operation before publishing.".format(
            ", ".join(str(path) for path in active_paths)
        )
    )


def upstream_divergence(repo: Path) -> tuple[str, int, int] | None:
    try:
        upstream = git(
            repo,
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{upstream}",
            capture_output=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return None

    raw_counts = git(
        repo,
        "rev-list",
        "--left-right",
        "--count",
        f"HEAD...{upstream}",
        capture_output=True,
    ).stdout.strip()
    ahead_raw, behind_raw = raw_counts.split()
    return upstream, int(ahead_raw), int(behind_raw)


def ensure_upstream_ready_for_push(repo: Path) -> None:
    divergence = upstream_divergence(repo)
    if divergence is None:
        return

    upstream, ahead_count, behind_count = divergence
    if behind_count == 0:
        return

    state = "diverged from" if ahead_count else "is behind"
    raise SystemExit(
        "Publish repository {} {} by {} commit(s) relative to {}. "
        "Synchronize it before publishing, for example with 'git -C {} pull --rebase'.".format(
            repo,
            state,
            behind_count,
            upstream,
            repo,
        )
    )


def changed_status_entries(repo: Path) -> list[dict[str, object]]:
    raw_output = git(
        repo,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        capture_output=True,
    ).stdout
    if not raw_output:
        return []

    tokens = raw_output.split("\0")
    entries: list[dict[str, object]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token:
            index += 1
            continue
        status = token[:2]
        path = token[3:]
        paths = [path] if path else []
        if "R" in status or "C" in status:
            index += 1
            if index < len(tokens) and tokens[index]:
                paths.append(tokens[index])
        entries.append({"status": status, "paths": paths})
        index += 1
    return entries


def stage_changed_entries(repo: Path, entries: list[dict[str, object]], batch_size: int = 100) -> int:
    pathspecs: list[str] = []
    seen_paths: set[str] = set()
    for entry in entries:
        for path in entry.get("paths", []):
            text = str(path).strip()
            if not text or text in seen_paths:
                continue
            seen_paths.add(text)
            pathspecs.append(text)

    for start in range(0, len(pathspecs), batch_size):
        git(repo, "add", "-A", "--", *pathspecs[start : start + batch_size])
    return len(pathspecs)


def remove_path(path: Path, retries: int = 4) -> None:
    for attempt in range(retries):
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            if exc.errno == errno.ENOTEMPTY and attempt < retries - 1:
                time.sleep(0.2 * (attempt + 1))
                continue
            raise


def clean_directory(target_dir: Path, preserve: set[str]) -> int:
    removed_entries = 0
    for child in target_dir.iterdir():
        if child.name in preserve:
            continue
        remove_path(child)
        removed_entries += 1
    return removed_entries


def copy_output(source_dir: Path, target_dir: Path) -> tuple[int, int]:
    copied_files = 0
    copied_dirs = 0
    for item in source_dir.iterdir():
        destination = target_dir / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
            copied_dirs += 1
            copied_files += sum(1 for path in destination.rglob("*") if path.is_file())
        else:
            shutil.copy2(item, destination)
            copied_files += 1
    return copied_dirs, copied_files


def build_commit_message(explicit: str | None) -> str:
    raw_value = explicit or os.environ.get(DEPLOY_MESSAGE_ENV, "").strip()
    if raw_value:
        return raw_value
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    return f"Publish Pelican site ({timestamp})"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy the generated Pelican output to a GitHub Pages repository."
    )
    parser.add_argument("--source", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--deploy-repo")
    parser.add_argument("--commit-message")
    parser.add_argument("--preserve", nargs="*", default=list(DEFAULT_PRESERVE))
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()

    source_dir = Path(args.source).expanduser().resolve()
    if not args.preflight and not source_dir.exists():
        raise SystemExit(f"Generated output directory not found: {source_dir}")

    deploy_repo = resolve_deploy_repo(args.deploy_repo)
    preserve = set(args.preserve)
    preserve.add(".git")
    commit_message = build_commit_message(args.commit_message)

    branch = git(deploy_repo, "branch", "--show-current", capture_output=True).stdout.strip() or "unknown"
    remote = git(deploy_repo, "config", "--get", "remote.origin.url", capture_output=True).stdout.strip() or "n/a"

    print_heading("GitHub Pages deploy")
    print_kv("Source", str(source_dir), value_tone="yellow")
    print_kv("Destination", str(deploy_repo), value_tone="yellow")
    print_kv("Branch", branch, value_tone="yellow")
    print_kv("Remote", remote)
    print_kv("Preserve", ", ".join(sorted(preserve)))

    print_subheading("Preflight")
    ensure_no_git_operation_in_progress(deploy_repo)
    ensure_git_index_unlocked(deploy_repo)
    divergence = upstream_divergence(deploy_repo)
    if divergence is None:
        print_kv("Upstream", "No upstream configured", indent=4, value_tone="yellow")
    else:
        upstream, ahead_count, behind_count = divergence
        print_kv("Upstream", upstream, indent=4, value_tone="yellow")
        print_kv("Ahead", str(ahead_count), indent=4, value_tone="yellow")
        print_kv("Behind", str(behind_count), indent=4, value_tone="yellow")
    ensure_upstream_ready_for_push(deploy_repo)
    if args.preflight:
        print_kv("Status", "Publish repository ready", indent=4, value_tone="green")
        return

    if source_dir != deploy_repo:
        print_subheading("Sync")
        git(deploy_repo, "pull", "--ff-only")
        removed_entries = clean_directory(deploy_repo, preserve)
        copied_dirs, copied_files = copy_output(source_dir, deploy_repo)
        print_kv("Removed root entries", str(removed_entries), indent=4, value_tone="yellow")
        print_kv("Copied directories", str(copied_dirs), indent=4, value_tone="yellow")
        print_kv("Copied files", str(copied_files), indent=4, value_tone="yellow")
    else:
        print_subheading("Sync")
        print_kv("Mode", "Build already generated in publish repository", indent=4, value_tone="green")

    print_subheading("Sanitize")
    removed_duplicates = cleanup_target(deploy_repo, exclude_git=True)
    print_kv("Removed duplicate artifacts", str(removed_duplicates), indent=4, value_tone="green")

    print_subheading("Git")
    print_kv("Step", "git status --porcelain", indent=4, value_tone="yellow")
    status_entries = changed_status_entries(deploy_repo)
    if not status_entries:
        print_kv("Status", "No changes to publish", indent=4, value_tone="green")
        return

    print_kv("Changed entries", str(len(status_entries)), indent=4, value_tone="yellow")
    print_kv("Step", "git add -A -- <changed paths>", indent=4, value_tone="yellow")
    staged_path_count = stage_changed_entries(deploy_repo, status_entries)
    print_kv("Staged paths", str(staged_path_count), indent=4, value_tone="yellow")
    staged_names = [
        line
        for line in git(deploy_repo, "diff", "--cached", "--name-only", capture_output=True).stdout.splitlines()
        if line.strip()
    ]
    if not staged_names:
        print_kv("Status", "No staged changes to publish", indent=4, value_tone="green")
        return

    print_kv("Step", "git commit", indent=4, value_tone="yellow")
    git(deploy_repo, "commit", "-m", commit_message)
    print_kv("Step", "git push", indent=4, value_tone="yellow")
    git(deploy_repo, "push")
    print_kv("Commit", commit_message, indent=4, value_tone="green")
    print_kv("Status", "Published", indent=4, value_tone="green")


if __name__ == "__main__":
    main()
