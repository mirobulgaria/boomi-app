from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    app_root: Path
    backend_root: Path
    engine_root: Path
    boomi_cli_path: Path


def get_app_paths() -> AppPaths:
    current_file = Path(__file__).resolve()

    # ...\boomi-builder\backend\src\boomi_builder\settings.py
    backend_root = current_file.parents[2]
    app_root = backend_root.parent
    engine_root = app_root / "engine" / "boomi-cli"
    boomi_cli_path = engine_root / "boomi.ps1"

    return AppPaths(
        app_root=app_root,
        backend_root=backend_root,
        engine_root=engine_root,
        boomi_cli_path=boomi_cli_path,
    )