#!/usr/bin/env python3

from __future__ import annotations

from site_sync_common import (
    GENERATED_DIR,
    finalize_status_line,
    render_home_page,
    style_text,
)
from sync_recipes import sync_recipes
from sync_tabs import sync_tabs


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    print(style_text("Sincronizando receitas e tablaturas...", tone="blue"), flush=True)
    recipes = sync_recipes()
    tabs = sync_tabs()
    render_home_page(recipes, tabs)
    finalize_status_line(
        f"Sincronização concluída: {len(recipes)} receitas, {len(tabs)} tablaturas",
        tone="green",
    )


if __name__ == "__main__":
    main()
