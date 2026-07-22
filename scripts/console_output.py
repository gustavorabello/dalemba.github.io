from __future__ import annotations

import os
import sys


ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "magenta": "\033[35m",
    "yellow": "\033[33m",
}


def use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


def paint(text: str, *styles: str) -> str:
    if not use_color() or not styles:
        return text
    prefix = "".join(ANSI[style] for style in styles if style in ANSI)
    return f"{prefix}{text}{ANSI['reset']}"


def print_heading(title: str, tone: str = "cyan") -> None:
    print(paint(title, "bold", tone))


def print_kv(
    label: str,
    value: str,
    *,
    indent: int = 2,
    tone: str = "blue",
    value_tone: str | None = None,
) -> None:
    rendered_value = paint(value, value_tone) if value_tone else value
    print(f"{' ' * indent}{paint(label + ':', 'bold', tone)} {rendered_value}")


def print_subheading(title: str, *, indent: int = 2, tone: str = "magenta") -> None:
    print(f"{' ' * indent}{paint(title, 'bold', tone)}")
