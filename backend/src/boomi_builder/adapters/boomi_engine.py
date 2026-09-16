from __future__ import annotations

import json
import xml.etree.ElementTree as ET
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


@dataclass(frozen=True)
class BoomiComponentDefinitionResult:
    component_id: str
    name: str
    type: str
    version: int
    xml: str


@dataclass(frozen=True)
class BoomiEnvironmentResult:
    environment_id: str
    name: str
    classification: str

@dataclass(frozen=True)
class BoomiEnvironmentExtensionsResult:
    environment_id: str
    xml: str

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
        resolved_workspace = self._validate_request(
            workspace=workspace,
            component_id=component_id,
        )

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

        self._validate_process_result(
            result,
            operation="get",
        )

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

        if data["componentId"] != component_id:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned a different component ID."
            )

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

    def get_component_definition(
        self,
        *,
        workspace: Path,
        component_id: str,
        environment: Mapping[str, str],
    ) -> BoomiComponentDefinitionResult:
        resolved_workspace = self._validate_request(
            workspace=workspace,
            component_id=component_id,
        )

        result = self.runner.run_script(
            self.paths.boomi_cli_path,
            arguments=[
                "get-definition",
                "-Workspace",
                str(resolved_workspace),
                "-Id",
                component_id,
                "-OutputFormat",
                "xml",
                "-RuntimeMode",
                "app-readonly",
            ],
            environment=environment,
        )

        self._validate_process_result(
            result,
            operation="get-definition",
        )

        xml_text = result.stdout

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned invalid component XML."
            ) from exc

        if self._local_name(root.tag) != "Component":
            raise BoomiEngineContractError(
                "Embedded Boomi CLI XML root must be Component."
            )

        actual_component_id = root.attrib.get(
            "componentId",
            "",
        )

        if actual_component_id != component_id:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned a different component ID."
            )

        name = root.attrib.get("name", "")
        component_type = root.attrib.get("type", "")
        version_text = root.attrib.get("version", "")

        if not name:
            raise BoomiEngineContractError(
                "Component XML attribute 'name' is missing."
            )

        if not component_type:
            raise BoomiEngineContractError(
                "Component XML attribute 'type' is missing."
            )

        try:
            version = int(version_text)
        except ValueError as exc:
            raise BoomiEngineContractError(
                "Component XML attribute 'version' "
                "must be an integer."
            ) from exc

        object_node = next(
            (
                child
                for child in root
                if self._local_name(child.tag) == "object"
            ),
            None,
        )

        if object_node is None:
            raise BoomiEngineContractError(
                "Component XML object element is missing."
            )

        if len(object_node) == 0:
            raise BoomiEngineContractError(
                "Component XML object contains no definition."
            )

        return BoomiComponentDefinitionResult(
            component_id=actual_component_id,
            name=name,
            type=component_type,
            version=version,
            xml=xml_text,
        )

    def list_environments(
        self,
        *,
        workspace: Path,
        environment: Mapping[str, str],
    ) -> tuple[BoomiEnvironmentResult, ...]:
        resolved_workspace = self._validate_workspace(
            workspace
        )

        result = self.runner.run_script(
            self.paths.boomi_cli_path,
            arguments=[
                "list-environments",
                "-Workspace",
                str(resolved_workspace),
                "-OutputFormat",
                "json",
                "-RuntimeMode",
                "app-readonly",
            ],
            environment=environment,
        )

        self._validate_process_result(
            result,
            operation="list-environments",
        )

        try:
            payload = json.loads(
                result.stdout
            )
        except json.JSONDecodeError as exc:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned invalid JSON."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise BoomiEngineContractError(
                "Embedded Boomi CLI JSON root must be an object."
            )

        if payload.get("success") is not True:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI did not report success=true."
            )

        if (
            payload.get("operation")
            != "list-environments"
        ):
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned an unexpected operation."
            )

        data = payload.get(
            "data"
        )

        if not isinstance(
            data,
            list,
        ):
            raise BoomiEngineContractError(
                "Embedded Boomi CLI environment "
                "data must be an array."
            )

        environments: list[
            BoomiEnvironmentResult
        ] = []

        seen_ids: set[str] = set()

        for item in data:
            if not isinstance(
                item,
                dict,
            ):
                raise BoomiEngineContractError(
                    "Embedded Boomi CLI environment "
                    "entry must be an object."
                )

            self._require_string(
                item,
                "id",
            )

            self._require_string(
                item,
                "name",
            )

            self._require_string(
                item,
                "classification",
            )

            environment_id = item["id"]

            if environment_id in seen_ids:
                raise BoomiEngineContractError(
                    "Embedded Boomi CLI returned "
                    "a duplicate environment ID."
                )

            seen_ids.add(
                environment_id
            )

            environments.append(
                BoomiEnvironmentResult(
                    environment_id=environment_id,
                    name=item["name"],
                    classification=(
                        item["classification"]
                    ),
                )
            )

        return tuple(
            environments
        )

    def get_environment_extensions(
        self,
        *,
        workspace: Path,
        environment_id: str,
        environment: Mapping[str, str],
    ) -> BoomiEnvironmentExtensionsResult:
        resolved_workspace = self._validate_workspace(
            workspace
        )

        if not environment_id.strip():
            raise ValueError(
                "environment_id must not be empty."
            )

        result = self.runner.run_script(
            self.paths.boomi_cli_path,
            arguments=[
                "get-environment-extensions",
                "-Workspace",
                str(resolved_workspace),
                "-EnvironmentId",
                environment_id,
                "-OutputFormat",
                "xml",
                "-RuntimeMode",
                "app-readonly",
            ],
            environment=environment,
        )

        self._validate_process_result(
            result,
            operation="get-environment-extensions",
        )

        xml_text = result.stdout

        try:
            root = ET.fromstring(
                xml_text
            )
        except ET.ParseError as exc:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned invalid "
                "EnvironmentExtensions XML."
            ) from exc

        if (
            self._local_name(root.tag)
            != "EnvironmentExtensions"
        ):
            raise BoomiEngineContractError(
                "Embedded Boomi CLI "
                "EnvironmentExtensions XML root "
                "must be EnvironmentExtensions."
            )

        return BoomiEnvironmentExtensionsResult(
            environment_id=environment_id,
            xml=xml_text,
        )

    def get_process_definition_corpus(
        self,
        *,
        workspace: Path,
        environment: Mapping[str, str],
    ) -> list[str]:
        resolved_workspace = self._validate_workspace(
            workspace
        )

        corpus_script_path = (
            self.paths.engine_root
            / "get-process-definition-corpus.ps1"
        )

        result = self.runner.run_script(
            corpus_script_path,
            arguments=[
                "-Workspace",
                str(resolved_workspace),
                "-RuntimeMode",
                "app-readonly",
            ],
            environment=environment,
        )

        self._validate_process_result(
            result,
            operation="get-process-definition-corpus",
        )

        return self._validate_corpus_envelope(
            result.stdout
        )

    @staticmethod
    def _validate_corpus_envelope(
        stdout: str,
    ) -> list[str]:
        try:
            envelope = json.loads(
                stdout
            )
        except json.JSONDecodeError as exc:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI returned an invalid "
                "corpus envelope."
            ) from exc

        if not isinstance(envelope, dict):
            raise BoomiEngineContractError(
                "Embedded Boomi CLI corpus envelope "
                "root must be an object."
            )

        if set(envelope.keys()) != {
            "version",
            "definitions",
        }:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI corpus envelope "
                "must contain only 'version' and "
                "'definitions'."
            )

        version = envelope["version"]

        if type(version) is not int or version != 1:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI corpus envelope "
                "version must be integer 1."
            )

        definitions = envelope["definitions"]

        if not isinstance(definitions, list):
            raise BoomiEngineContractError(
                "Embedded Boomi CLI corpus envelope "
                "'definitions' must be an array."
            )

        if len(definitions) == 0:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI corpus envelope "
                "contained no definitions."
            )

        if len(definitions) > 10:
            raise BoomiEngineContractError(
                "Embedded Boomi CLI corpus envelope "
                "exceeded the maximum of 10 definitions."
            )

        for index, definition in enumerate(definitions):

            if not isinstance(definition, str):
                raise BoomiEngineContractError(
                    "Embedded Boomi CLI corpus envelope "
                    "definition entries must be strings."
                )

            if not definition.strip():
                raise BoomiEngineContractError(
                    "Embedded Boomi CLI corpus envelope "
                    "definition entries must not be empty."
                )

            try:
                root = ET.fromstring(definition)
            except ET.ParseError as exc:
                raise BoomiEngineContractError(
                    "Embedded Boomi CLI corpus envelope "
                    "contained a definition that is not "
                    "valid XML."
                ) from exc

            if (
                BoomiEngineAdapter._local_name(root.tag)
                != "Component"
            ):
                raise BoomiEngineContractError(
                    "Embedded Boomi CLI corpus envelope "
                    "definition root must be Component."
                )

        return definitions

    @staticmethod
    def _validate_workspace(
        workspace: Path,
    ) -> Path:
        resolved_workspace = workspace.resolve()

        if not resolved_workspace.is_dir():
            raise ValueError(
                "Workspace directory was not found: "
                f"{resolved_workspace}"
            )

        return resolved_workspace

    @staticmethod
    def _validate_request(
        *,
        workspace: Path,
        component_id: str,
    ) -> Path:
        resolved_workspace = (
            BoomiEngineAdapter._validate_workspace(
                workspace
            )
        )

        if not component_id.strip():
            raise ValueError(
                "component_id must not be empty."
            )

        return resolved_workspace

    @staticmethod
    def _validate_process_result(
        result: ProcessResult,
        *,
        operation: str,
    ) -> None:
        if result.exit_code != 0:
            raise BoomiEngineExecutionError(
                f"Embedded Boomi CLI {operation} operation failed."
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
    def _local_name(tag: str) -> str:
        if "}" in tag:
            return tag.rsplit("}", 1)[1]

        return tag

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