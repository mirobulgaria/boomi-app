from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from boomi_builder.adapters.powershell_runner import (
    PowerShellRunner,
    ProcessResult,
)
from boomi_builder.settings import AppPaths, get_app_paths


@dataclass(frozen=True)
class EngineStatus:
    available: bool
    cli_path: Path
    engine_root: Path


@dataclass(frozen=True)
class BoomiComponentResult:
    component_id: str
    name: str
    type: str
    version: int
    current_version: bool
    deleted: bool
    folder_full_path: str
    branch_name: str


class BoomiEngineError(RuntimeError):
    pass


class BoomiEngineExecutionError(BoomiEngineError):
    pass


class BoomiEngineContractError(BoomiEngineError):
    pass


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

    def get_component(
        self,
        *,
        workspace: Path,
        component_id: str,
        environment: Mapping[str, str],
    ) -> BoomiComponentResult:
        resolved_workspace = workspace.resolve()

        if not resolved_workspace.is_dir():
            raise ValueError(
                f"Workspace directory was not found: "
                f"{resolved_workspace}"
            )

        if not component_id.strip():
            raise ValueError("component_id must not be empty.")

        result = self.runner.run_script(
            self.paths.boomi_cli_path,
            arguments=[
                "get",
                "-Workspace",
                str(resolved_workspace),
                "-Id",
                component_id,
                "-OutputFormat",
                "json",
                "-RuntimeMode",
                "app-readonly",
            ],
            environment=environment,
        )

        self._validate_process_result(result)

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise BoomiEngineContractError(
                "Embedded Boomi CLI JSON root must be an object."
            )

        if payload.get("success") is not True:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI did not report success=true."
            )

        if payload.get("operation") != "get":
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned an unexpected operation."
            )

        data = payload.get("data")

        if not isinstance(data, dict):
            raise BoomiEngineContractError(
                "Embedded Boomi CLI data must be an object."
            )

        self._require_string(data, "componentId")
        self._require_string(data, "name")
        self._require_string(data, "type")
        self._require_int(data, "version")
        self._require_bool(data, "currentVersion")
        self._require_bool(data, "deleted")
        self._require_string(data, "folderFullPath")
        self._require_string(data, "branchName")

        return BoomiComponentResult(
            component_id=data["componentId"],
            name=data["name"],
            type=data["type"],
            version=data["version"],
            current_version=data["currentVersion"],
            deleted=data["deleted"],
            folder_full_path=data["folderFullPath"],
            branch_name=data["branchName"],
        )

    @staticmethod
    def _validate_process_result(
        result: ProcessResult,
    ) -> None:
        if result.exit_code != 0:
            raise BoomiEngineExecutionError(
                "Embedded Boomi CLI get operation failed."
            )

        if result.stderr:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI wrote to stderr on success."
            )

        if not result.stdout.strip():
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned empty stdout."
            )

    @staticmethod
    def _require_string(
        data: dict[str, object],
        field: str,
    ) -> None:
        value = data.get(field)

        if not isinstance(value, str) or not value:
            raise BoomiEngineContractError(
                f"Embedded Boomi CLI field '{field}' "
                f"must be a non-empty string."
            )

    @staticmethod
    def _require_int(
        data: dict[str, object],
        field: str,
    ) -> None:
        value = data.get(field)

        # bool is a subclass of int in Python, therefore it must
        # be rejected explicitly.
        if isinstance(value, bool) or not isinstance(value, int):
            raise BoomiEngineContractError(
                f"Embedded Boomi CLI field '{field}' "
                f"must be an integer."
            )

    @staticmethod
    def _require_bool(
        data: dict[str, object],
        field: str,
    ) -> None:
        value = data.get(field)

        if not isinstance(value, bool):
            raise BoomiEngineContractError(
                f"Embedded Boomi CLI field '{field}' "
                f"must be a boolean."
            )