from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from boomi_builder.adapters.powershell_runner import PowerShellRunner
from boomi_builder.settings import AppPaths, get_app_paths


@dataclass(frozen=True)
class EngineStatus:
    available: bool
    cli_path: Path
    engine_root: Path


class BoomiEngineAdapter:
    def __init__(
        self,
        paths: AppPaths | None = None,
        runner: PowerShellRunner | None = None,
    ) -> None:
        self.paths = paths or get_app_paths()
        self.runner = runner or PowerShellRunner()

    def status(self) -> EngineStatus:
        cli_exists = self.paths.boomi_cli_path.is_file()
        engine_exists = self.paths.engine_root.is_dir()

        return EngineStatus(
            available=cli_exists and engine_exists,
            cli_path=self.paths.boomi_cli_path,
            engine_root=self.paths.engine_root,
        )