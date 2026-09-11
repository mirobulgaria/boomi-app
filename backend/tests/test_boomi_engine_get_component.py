import json
from pathlib import Path

import pytest

from boomi_builder.adapters.boomi_engine import (
    BoomiComponentResult,
    BoomiEngineAdapter,
    BoomiEngineContractError,
    BoomiEngineExecutionError,
)
from boomi_builder.adapters.powershell_runner import ProcessResult
from boomi_builder.settings import get_app_paths


class FakeRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def run_script(
        self,
        script_path: Path,
        arguments=(),
        environment=None,
        stdin_text=None,
    ) -> ProcessResult:
        self.calls.append(
            {
                "script_path": script_path,
                "arguments": list(arguments),
                "environment": environment,
                "stdin_text": stdin_text,
            }
        )

        return self.result


def valid_payload() -> dict[str, object]:
    return {
        "success": True,
        "operation": "get",
        "data": {
            "componentId": (
                "00000000-1111-2222-3333-444444444444"
            ),
            "name": "TEST — Български ↔ ZTE",
            "type": "process",
            "version": 7,
            "currentVersion": True,
            "deleted": False,
            "folderFullPath": "Example/Integration",
            "branchName": "main",
        },
    }


def test_get_component_uses_safe_machine_contract(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=json.dumps(
                valid_payload(),
                ensure_ascii=False,
            ),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    environment = {
        "BOOMI_ACCOUNT_ID": "TEST_ACCOUNT",
        "BOOMI_USERNAME": "test.user@example.invalid",
        "BOOMI_API_TOKEN": "SYNTHETIC_TOKEN",
    }

    component = adapter.get_component(
        workspace=tmp_path,
        component_id=(
            "00000000-1111-2222-3333-444444444444"
        ),
        environment=environment,
    )

    assert component == BoomiComponentResult(
        component_id=(
            "00000000-1111-2222-3333-444444444444"
        ),
        name="TEST — Български ↔ ZTE",
        type="process",
        version=7,
        current_version=True,
        deleted=False,
        folder_full_path="Example/Integration",
        branch_name="main",
    )

    assert len(runner.calls) == 1

    call = runner.calls[0]

    assert call["script_path"] == paths.boomi_cli_path

    assert call["arguments"] == [
        "get",
        "-Workspace",
        str(tmp_path.resolve()),
        "-Id",
        "00000000-1111-2222-3333-444444444444",
        "-OutputFormat",
        "json",
        "-RuntimeMode",
        "app-readonly",
    ]

    assert call["environment"] is environment
    assert call["stdin_text"] is None


def test_get_component_rejects_engine_failure(
    tmp_path: Path,
) -> None:
    adapter = BoomiEngineAdapter(
        runner=FakeRunner(
            ProcessResult(
                exit_code=1,
                stdout="",
                stderr="synthetic failure",
            )
        )
    )

    with pytest.raises(BoomiEngineExecutionError):
        adapter.get_component(
            workspace=tmp_path,
            component_id="component-1",
            environment={},
        )


def test_get_component_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    adapter = BoomiEngineAdapter(
        runner=FakeRunner(
            ProcessResult(
                exit_code=0,
                stdout="not-json",
                stderr="",
            )
        )
    )

    with pytest.raises(BoomiEngineContractError):
        adapter.get_component(
            workspace=tmp_path,
            component_id="component-1",
            environment={},
        )


def test_get_component_rejects_stderr_on_success(
    tmp_path: Path,
) -> None:
    adapter = BoomiEngineAdapter(
        runner=FakeRunner(
            ProcessResult(
                exit_code=0,
                stdout=json.dumps(valid_payload()),
                stderr="unexpected diagnostic",
            )
        )
    )

    with pytest.raises(BoomiEngineContractError):
        adapter.get_component(
            workspace=tmp_path,
            component_id="component-1",
            environment={},
        )


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("componentId", ""),
        ("name", None),
        ("type", 123),
        ("version", "7"),
        ("version", True),
        ("currentVersion", "true"),
        ("deleted", 0),
        ("folderFullPath", None),
        ("branchName", ""),
    ],
)
def test_get_component_rejects_invalid_field_types(
    tmp_path: Path,
    field: str,
    invalid_value: object,
) -> None:
    payload = valid_payload()
    data = payload["data"]

    assert isinstance(data, dict)

    data[field] = invalid_value

    adapter = BoomiEngineAdapter(
        runner=FakeRunner(
            ProcessResult(
                exit_code=0,
                stdout=json.dumps(payload),
                stderr="",
            )
        )
    )

    with pytest.raises(BoomiEngineContractError):
        adapter.get_component(
            workspace=tmp_path,
            component_id="component-1",
            environment={},
        )