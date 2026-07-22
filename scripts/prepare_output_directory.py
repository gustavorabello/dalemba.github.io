from __future__ import annotations

import argparse
import errno
import shutil
import time
from pathlib import Path

from console_output import print_heading, print_kv


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean a generated output directory while preserving selected entries."
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--preserve", nargs="*", default=[".git", ".gitignore"])
    parser.add_argument("--create-if-missing", action="store_true")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    preserve = set(args.preserve)
    if not target.exists():
        if args.create_if_missing:
            target.mkdir(parents=True, exist_ok=True)
        else:
            print_heading("Prepare output directory")
            print_kv("Target", str(target), value_tone="yellow")
            print_kv("Preserve", ", ".join(sorted(preserve)))
            print_kv("Removed entries", "0", value_tone="yellow")
            print_kv("Status", "Target directory not found", value_tone="green")
            return

    removed_entries = 0
    for child in target.iterdir():
        if child.name in preserve:
            continue
        remove_path(child)
        removed_entries += 1

    nojekyll = target / ".nojekyll"
    nojekyll.touch()

    print_heading("Prepare output directory")
    print_kv("Target", str(target), value_tone="yellow")
    print_kv("Preserve", ", ".join(sorted(preserve)))
    print_kv("Removed entries", str(removed_entries), value_tone="yellow")
    print_kv("No Jekyll", nojekyll.name, value_tone="green")


if __name__ == "__main__":
    main()
