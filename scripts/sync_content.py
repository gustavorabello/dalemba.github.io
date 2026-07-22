#!/usr/bin/env python3

from __future__ import annotations

from site_sync_common import (
    GENERATED_DIR,
    finalize_status_line,
    print_sync_result,
    print_sync_step,
    render_home_page,
)
from sync_academicdb import sync_academicdb
from sync_financeiro import get_password, sync_financeiro
from sync_recipes import sync_recipes
from sync_tabs import sync_tabs


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    print_sync_step("Sincronizando receitas", tone="cyan")
    recipes = sync_recipes()
    print_sync_result("Receitas", f"{len(recipes)} paginas")

    print_sync_step("Sincronizando musicas", tone="cyan")
    tabs = sync_tabs()
    print_sync_result("Musicas", f"{len(tabs)} paginas")

    print_sync_step("Preparando senha compartilhada", "Financeiro e AcademicDB", tone="amber")
    protected_password = get_password()

    print_sync_step("Sincronizando financeiro", tone="magenta")
    financeiro = sync_financeiro(password=protected_password)
    print_sync_result(
        "Financeiro",
        f"{financeiro['paginas']} paginas no vault, {financeiro['produtos']} produtos",
    )

    print_sync_step("Sincronizando AcademicDB", tone="magenta")
    academicdb = sync_academicdb(password=protected_password)
    omitted_mb = academicdb["omitted_bytes"] / (1024 * 1024)
    print_sync_result(
        "AcademicDB",
        f"{academicdb['assets']} arquivos no vault, "
        f"{academicdb['omitted']} omitidos ({omitted_mb:.1f} MiB)",
    )

    print_sync_step("Renderizando home", tone="blue")
    render_home_page(recipes, tabs, financeiro, academicdb)
    finalize_status_line(
        f"Sincronização concluída: {len(recipes)} receitas, {len(tabs)} músicas, "
        f"{financeiro['paginas']} páginas financeiras, "
        f"{academicdb['assets']} arquivos do AcademicDB",
        tone="green",
    )


if __name__ == "__main__":
    main()
