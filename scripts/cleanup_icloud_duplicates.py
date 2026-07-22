#!/usr/bin/env python3

from __future__ import annotations

import argparse
import errno
import re
import shutil
import time
from pathlib import Path

from console_output import print_heading, print_kv


DUPLICATE_NAME_RE = re.compile(r" \d+(?:\.[^./]+)?$")


def is_icloud_duplicate(path: Path) -> bool:
    name = path.name
    return name.endswith(".icloud") or bool(DUPLICATE_NAME_RE.search(name))


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


def should_skip(path: Path, root: Path, exclude_git: bool) -> bool:
    if not exclude_git:
        return False
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return ".git" in relative.parts


def cleanup_target(root: Path, exclude_git: bool = False) -> int:
    if not root.exists():
        return 0

    removed = 0
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if should_skip(path, root, exclude_git):
            continue
        if not is_icloud_duplicate(path):
            continue
        remove_path(path)
        removed += 1
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove artefatos duplicados do iCloud, como 'arquivo 2' e entradas '.icloud'."
    )
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--exclude-git", action="store_true")
    args = parser.parse_args()

    print_heading("Cleanup iCloud duplicates")
    total_removed = 0
    for raw_target in args.target:
        target = Path(raw_target).expanduser().resolve()
        removed = cleanup_target(target, exclude_git=args.exclude_git)
        total_removed += removed
        print_kv("Target", str(target), value_tone="yellow")
        print_kv("Removed", str(removed), indent=2, value_tone="green")
    print_kv("Total removed", str(total_removed), value_tone="green")


if __name__ == "__main__":
    main()
