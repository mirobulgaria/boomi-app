from __future__ import annotations

import json
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


class RecordingRunner:
    def __init__(
        self,
        result: ProcessResult,
    ) -> None:
        self.result = result
        self.calls: list[
            tuple[
                Path,
                list[str],
                dict[str, str],
            ]
        ] = []

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
                dict(
                    environment or {}
                ),
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


def success_result(
    data: list[dict[str, object]],
) -> ProcessResult:
    payload = {
        "success": True,
        "operation": "list-environments",
        "data": data,
    }

    return ProcessResult(
        exit_code=0,
        stdout=json.dumps(
            payload
        ),
        stderr="",
    )


def test_list_environments_invokes_readonly_json_contract(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    runner = RecordingRunner(
        success_result([])
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

    result = adapter.list_environments(
        workspace=paths.data_root,
        environment=runtime_environment,
    )

    assert result == ()

    assert len(
        runner.calls
    ) == 1

    (
        script_path,
        arguments,
        environment,
    ) = runner.calls[0]

    assert (
        script_path
        == paths.boomi_cli_path
    )

    assert arguments == [
        "list-environments",
        "-Workspace",
        str(
            paths.data_root.resolve()
        ),
        "-OutputFormat",
        "json",
        "-RuntimeMode",
        "app-readonly",
    ]

    assert (
        environment
        == runtime_environment
    )


def test_list_environments_returns_typed_results(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    runner = RecordingRunner(
        success_result(
            [
                {
                    "id": "env-test",
                    "name": "Test",
                    "classification": "TEST",
                },
                {
                    "id": "env-prod",
                    "name": "Production",
                    "classification": "PROD",
                },
            ]
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    result = adapter.list_environments(
        workspace=paths.data_root,
        environment={},
    )

    assert len(result) == 2

    assert (
        result[0].environment_id
        == "env-test"
    )

    assert result[0].name == "Test"

    assert (
        result[0].classification
        == "TEST"
    )

    assert (
        result[1].environment_id
        == "env-prod"
    )

    assert (
        result[1].classification
        == "PROD"
    )


def test_list_environments_allows_empty_data(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            success_result([])
        ),
    )

    assert (
        adapter.list_environments(
            workspace=paths.data_root,
            environment={},
        )
        == ()
    )


def test_list_environments_rejects_execution_failure(
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
                stderr=(
                    "SYNTHETIC_SECRET_"
                    "MUST_NOT_LEAK"
                ),
            )
        ),
    )

    with pytest.raises(
        BoomiEngineExecutionError,
        match=(
            "Embedded Boomi CLI "
            "list-environments "
            "operation failed"
        ),
    ) as exc_info:
        adapter.list_environments(
            workspace=paths.data_root,
            environment={},
        )

    assert (
        "SYNTHETIC_SECRET_MUST_NOT_LEAK"
        not in str(exc_info.value)
    )


def test_list_environments_rejects_stderr_on_success(
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
                stdout=json.dumps(
                    {
                        "success": True,
                        "operation": (
                            "list-environments"
                        ),
                        "data": [],
                    }
                ),
                stderr="unexpected",
            )
        ),
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="wrote to stderr",
    ):
        adapter.list_environments(
            workspace=paths.data_root,
            environment={},
        )


def test_list_environments_rejects_empty_stdout(
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
        adapter.list_environments(
            workspace=paths.data_root,
            environment={},
        )


def test_list_environments_rejects_invalid_json(
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
                stdout="{",
                stderr="",
            )
        ),
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="invalid JSON",
    ):
        adapter.list_environments(
            workspace=paths.data_root,
            environment={},
        )


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {
            "success": False,
            "operation": "list-environments",
            "data": [],
        },
        {
            "success": True,
            "operation": "wrong-operation",
            "data": [],
        },
        {
            "success": True,
            "operation": "list-environments",
            "data": {},
        },
    ],
)
def test_list_environments_rejects_invalid_envelope(
    tmp_path: Path,
    payload,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            ProcessResult(
                exit_code=0,
                stdout=json.dumps(
                    payload
                ),
                stderr="",
            )
        ),
    )

    with pytest.raises(
        BoomiEngineContractError
    ):
        adapter.list_environments(
            workspace=paths.data_root,
            environment={},
        )


@pytest.mark.parametrize(
    "entry",
    [
        "not-an-object",
        {
            "name": "Test",
            "classification": "TEST",
        },
        {
            "id": "env-1",
            "classification": "TEST",
        },
        {
            "id": "env-1",
            "name": "Test",
        },
        {
            "id": "",
            "name": "Test",
            "classification": "TEST",
        },
    ],
)
def test_list_environments_rejects_invalid_entries(
    tmp_path: Path,
    entry,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            success_result(
                [entry]
            )
        ),
    )

    with pytest.raises(
        BoomiEngineContractError
    ):
        adapter.list_environments(
            workspace=paths.data_root,
            environment={},
        )


def test_list_environments_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            success_result(
                [
                    {
                        "id": "env-1",
                        "name": "One",
                        "classification": "TEST",
                    },
                    {
                        "id": "env-1",
                        "name": "Two",
                        "classification": "PROD",
                    },
                ]
            )
        ),
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="duplicate environment ID",
    ):
        adapter.list_environments(
            workspace=paths.data_root,
            environment={},
        )


def test_list_environments_rejects_missing_workspace(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=RecordingRunner(
            success_result([])
        ),
    )

    with pytest.raises(
        ValueError,
        match="Workspace directory was not found",
    ):
        adapter.list_environments(
            workspace=(
                tmp_path
                / "missing"
            ),
            environment={},
        )