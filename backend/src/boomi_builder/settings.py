from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    app_root: Path
    backend_root: Path
    engine_root: Path
    boomi_cli_path: Path
    data_root: Path
    secrets_root: Path
    connections_path: Path
    dpapi_helper_path: Path


def get_app_paths() -> AppPaths:
    current_file = Path(__file__).resolve()

    backend_root = current_file.parents[2]
    app_root = backend_root.parent

    engine_root = app_root / "engine" / "boomi-cli"
    boomi_cli_path = engine_root / "boomi.ps1"

    data_root = app_root / "data"
    secrets_root = data_root / "secrets"
    connections_path = data_root / "connections.json"

    dpapi_helper_path = (
        backend_root
        / "src"
        / "boomi_builder"
        / "adapters"
        / "dpapi_secret.ps1"
    )

    return AppPaths(
        app_root=app_root,
        backend_root=backend_root,
        engine_root=engine_root,
        boomi_cli_path=boomi_cli_path,
        data_root=data_root,
        secrets_root=secrets_root,
        connections_path=connections_path,
        dpapi_helper_path=dpapi_helper_path,
    )