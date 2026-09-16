from __future__ import annotations

from pathlib import Path

import pytest

from boomi_builder.adapters.boomi_engine import (
    BoomiEngineAdapter,
    BoomiEngineContractError,
    BoomiEngineExecutionError,
)
from boomi_builder.adapters.powershell_runner import (
    ProcessResult,
)
from boomi_builder.settings import AppPaths


ENVIRONMENT_ID = (
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
)

SYNTHETIC_SECRET = (
    "SYNTHETIC_EXTENSION_SECRET_MUST_NOT_LEAK"
)


class RecordingRunner:
    def __init__(
        self,
        result: ProcessResult,
    ) -> None:
        self.result = result
        self.calls = []

    def run_script(
        self,
        script_path: Path,
        arguments=(),
        environment=None,
        stdin_text=None,
    ) -> ProcessResult:
        self.calls.append(
            (
                script_path,
                list(arguments),
                dict(environment or {}),
            )
        )

        return self.result


def build_paths(
    tmp_path: Path,
) -> AppPaths:
    engine_root = (
        tmp_path
        / "engine"
        / "boomi-cli"
    )

    engine_root.mkdir(
        parents=True
    )

    cli_path = (
        engine_root
        / "boomi.ps1"
    )

    cli_path.write_text(
        "# synthetic",
        encoding="utf-8",
    )

    data_root = (
        tmp_path
        / "data"
    )

    data_root.mkdir()

    return AppPaths(
        app_root=tmp_path,
        backend_root=tmp_path / "backend",
        engine_root=engine_root,
        boomi_cli_path=cli_path,
        data_root=data_root,
        connections_path=(
            data_root
            / "connections.json"
        ),
        secrets_root=(
            data_root
            / "secrets"
        ),
        dpapi_helper_path=(
            tmp_path
            / "dpapi.ps1"
        ),
    )


def valid_xml() -> str:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<EnvironmentExtensions>
  <connections>
    <connection
        id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        name="Synthetic Connection">
      <field
          id="password"
          value="{SYNTHETIC_SECRET}" />
    </connection>
  </connections>
</EnvironmentExtensions>
"""


def test_get_environment_extensions_invokes_internal_xml_contract(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    runner = RecordingRunner(
        ProcessResult(
            exit_code=0,
            stdout=valid_xml(),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    runtime_environment = {
        "BOOMI_ACCOUNT_ID": "ACCOUNT",
        "BOOMI_USERNAME": "USER",
        "BOOMI_API_TOKEN": "TOKEN",
    }

    result = adapter.get_environment_extensions(
        workspace=paths.data_root,
        environment_id=ENVIRONMENT_ID,
        environment=runtime_environment,
    )

    assert result.environment_id == ENVIRONMENT_ID
    assert result.xml == valid_xml()

    assert len(runner.calls) == 1

    (
        script_path,
        arguments,
        environment,
    ) = runner.calls[0]

    assert script_path == paths.boomi_cli_path

    assert arguments == [
        "get-environment-extensions",
        "-Workspace",
        str(paths.data_root.resolve()),
        "-EnvironmentId",
        ENVIRONMENT_ID,
        "-OutputFormat",
        "xml",
        "-RuntimeMode",
        "app-readonly",
    ]

    assert environment == runtime_environment


def test_get_environment_extensions_preserves_raw_xml_internally(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            ProcessResult(
                exit_code=0,
                stdout=valid_xml(),
                stderr="",
            )
        ),
    )

    result = adapter.get_environment_extensions(
        workspace=paths.data_root,
        environment_id=ENVIRONMENT_ID,
        environment={},
    )

    assert SYNTHETIC_SECRET in result.xml


def test_get_environment_extensions_does_not_leak_stderr_on_failure(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            ProcessResult(
                exit_code=1,
                stdout="",
                stderr=SYNTHETIC_SECRET,
            )
        ),
    )

    with pytest.raises(
        BoomiEngineExecutionError,
        match=(
            "Embedded Boomi CLI "
            "get-environment-extensions "
            "operation failed"
        ),
    ) as exc_info:
        adapter.get_environment_extensions(
            workspace=paths.data_root,
            environment_id=ENVIRONMENT_ID,
            environment={},
        )

    assert (
        SYNTHETIC_SECRET
        not in str(exc_info.value)
    )


def test_get_environment_extensions_rejects_stderr_on_success(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            ProcessResult(
                exit_code=0,
                stdout=valid_xml(),
                stderr="unexpected",
            )
        ),
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="wrote to stderr",
    ):
        adapter.get_environment_extensions(
            workspace=paths.data_root,
            environment_id=ENVIRONMENT_ID,
            environment={},
        )


def test_get_environment_extensions_rejects_empty_stdout(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            ProcessResult(
                exit_code=0,
                stdout="",
                stderr="",
            )
        ),
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="empty stdout",
    ):
        adapter.get_environment_extensions(
            workspace=paths.data_root,
            environment_id=ENVIRONMENT_ID,
            environment={},
        )


def test_get_environment_extensions_rejects_invalid_xml(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            ProcessResult(
                exit_code=0,
                stdout="<EnvironmentExtensions>",
                stderr="",
            )
        ),
    )

    with pytest.raises(
        BoomiEngineContractError,
        match=(
            "invalid EnvironmentExtensions XML"
        ),
    ):
        adapter.get_environment_extensions(
            workspace=paths.data_root,
            environment_id=ENVIRONMENT_ID,
            environment={},
        )


def test_get_environment_extensions_rejects_wrong_root(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            ProcessResult(
                exit_code=0,
                stdout="<SomethingElse />",
                stderr="",
            )
        ),
    )

    with pytest.raises(
        BoomiEngineContractError,
        match=(
            "XML root must be "
            "EnvironmentExtensions"
        ),
    ):
        adapter.get_environment_extensions(
            workspace=paths.data_root,
            environment_id=ENVIRONMENT_ID,
            environment={},
        )


def test_get_environment_extensions_rejects_empty_environment_id(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            ProcessResult(
                exit_code=0,
                stdout=valid_xml(),
                stderr="",
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="environment_id must not be empty",
    ):
        adapter.get_environment_extensions(
            workspace=paths.data_root,
            environment_id="",
            environment={},
        )


def test_get_environment_extensions_rejects_missing_workspace(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            ProcessResult(
                exit_code=0,
                stdout=valid_xml(),
                stderr="",
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="Workspace directory was not found",
    ):
        adapter.get_environment_extensions(
            workspace=tmp_path / "missing",
            environment_id=ENVIRONMENT_ID,
            environment={},
        )