#!/usr/bin/env python3

from __future__ import annotations

import argparse
import errno
import filecmp
import re
import shutil
import time
from pathlib import Path

from console_output import paint, print_heading, print_kv, print_subheading


# O iCloud renomeia cópias em conflito inserindo " N" antes da extensão:
# "berinjela.md" -> "berinjela 2.md", "foo" -> "foo 2". O número é pequeno
# (2, 3, 4...); limitá-lo a 1-2 dígitos evita confundir com anos ou versões
# legítimos como "COBEM 2025.md" ou "Rio Fluids 2026".
DUPLICATE_SUFFIX_RE = re.compile(r" (\d{1,2})(\.[^./]+)?$")


def base_name_for(name: str) -> str | None:
    """Nome original do qual este seria uma cópia numerada, ou None.

    "berinjela 2.md" -> "berinjela.md"; "foo 2" -> "foo";
    "COBEM 2025.md" -> None (2025 tem 4 dígitos, não casa)."""
    match = DUPLICATE_SUFFIX_RE.search(name)
    if not match:
        return None
    return name[: match.start()] + (match.group(2) or "")


def is_numbered_duplicate(path: Path) -> bool:
    """Cópia numerada do iCloud cujo nome-base existe ao lado (nome repetido).

    A checagem do nome-base é o que separa uma cópia de conflito real de um
    arquivo legítimo terminado em número: só apagamos "aula 3.pdf" se
    "aula.pdf" também estiver na mesma pasta."""
    base = base_name_for(path.name)
    return base is not None and (path.parent / base).exists()


def is_icloud_placeholder(path: Path) -> bool:
    """Marcador ".icloud" de um arquivo removido do disco local mas ainda na
    nuvem. Apagá-lo propaga a exclusão do arquivo real para todos os
    dispositivos, então é sinalizado com destaque no modo de simulação."""
    return path.name.endswith(".icloud")


def is_removable(path: Path) -> bool:
    return is_numbered_duplicate(path) or is_icloud_placeholder(path)


def describe(path: Path) -> tuple[str, str]:
    """(rótulo, cor) descrevendo o candidato para a listagem do dry-run."""
    if is_icloud_placeholder(path):
        return "icloud ⚠ (apaga o arquivo real na nuvem)", "yellow"
    if path.is_dir() and not path.is_symlink():
        return "diretório (conteúdo não comparado)", "blue"
    base = base_name_for(path.name)
    original = path.parent / base if base else None
    try:
        if original and filecmp.cmp(path, original, shallow=False):
            return "idêntico ao original", "green"
    except OSError:
        pass
    return "DIFERE do original — revisar", "yellow"


def remove_path(path: Path, retries: int = 4) -> bool:
    for attempt in range(retries):
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
            return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            if exc.errno == errno.ENOTEMPTY and attempt < retries - 1:
                time.sleep(0.2 * (attempt + 1))
                continue
            raise
    return False


def should_skip(path: Path, root: Path, exclude_git: bool) -> bool:
    if not exclude_git:
        return False
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return ".git" in relative.parts


def cleanup_target(root: Path, exclude_git: bool = False, dry_run: bool = False) -> int:
    """Remove cópias numeradas do iCloud (com nome-base existente) e marcadores
    ".icloud". Com dry_run, apenas lista os candidatos e retorna quantos seriam
    removidos, sem apagar nada."""
    if not root.exists():
        return 0

    # Profundidade decrescente: filhos antes dos pais, para que um diretório
    # duplicado seja removido por inteiro sem tropeçar em itens já apagados.
    candidates = [
        path
        for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True)
        if not should_skip(path, root, exclude_git) and is_removable(path)
    ]

    affected = 0
    for path in candidates:
        if dry_run:
            label, tone = describe(path)
            try:
                shown = path.relative_to(root)
            except ValueError:
                shown = path
            print(f"    {paint('• ' + str(shown), 'bold')}  {paint(label, tone)}")
            affected += 1
        elif remove_path(path):
            affected += 1
    return affected


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Remove cópias duplicadas do iCloud: arquivos e pastas 'nome N' cujo "
            "'nome' existe ao lado, além de marcadores '.icloud'. Por segurança, "
            "apenas lista (dry-run) até receber --apply."
        )
    )
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--exclude-git", action="store_true")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apaga de fato. Sem esta flag, apenas mostra o que seria removido.",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    print_heading("Cleanup iCloud duplicates" + (" (dry-run)" if dry_run else ""))
    total = 0
    for raw_target in args.target:
        target = Path(raw_target).expanduser().resolve()
        print_subheading(str(target), tone="yellow")
        affected = cleanup_target(target, exclude_git=args.exclude_git, dry_run=dry_run)
        total += affected
        print_kv("Would remove" if dry_run else "Removed", str(affected), indent=2, value_tone="green")

    label = "Total to remove" if dry_run else "Total removed"
    print_kv(label, str(total), value_tone="green")
    if dry_run:
        print_kv("Next", "re-execute com --apply para apagar", value_tone="yellow")


if __name__ == "__main__":
    main()
