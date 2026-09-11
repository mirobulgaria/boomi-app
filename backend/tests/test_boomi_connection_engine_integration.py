import json
from pathlib import Path

from boomi_builder.adapters.boomi_engine import (
    BoomiComponentResult,
    BoomiEngineAdapter,
)
from boomi_builder.adapters.in_memory_secret_store import (
    InMemorySecretStore,
)
from boomi_builder.adapters.powershell_runner import ProcessResult
from boomi_builder.services.boomi_connection_service import (
    BoomiConnectionService,
)
from boomi_builder.settings import get_app_paths


class CapturingRunner:
    def __init__(self) -> None:
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

        payload = {
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

        return ProcessResult(
            exit_code=0,
            stdout=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            stderr="",
        )


def test_connection_secret_to_engine_get_component(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()

    secret_store = InMemorySecretStore()
    connection_service = BoomiConnectionService(
        secret_store
    )

    synthetic_token = "SYNTHETIC_E2E_TOKEN_NOT_REAL"

    connection = connection_service.create_connection(
        owner_user_id="user-1",
        name="TEST Boomi Connection",
        account_id="TEST_ACCOUNT",
        boomi_username="test.user@example.invalid",
        api_token=synthetic_token,
    )

    assert connection.secret_reference.provider == "memory"
    assert synthetic_token not in repr(connection)

    runtime_environment = (
        connection_service.resolve_runtime_environment(
            connection
        )
    )

    runner = CapturingRunner()

    engine = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    component = engine.get_component(
        workspace=tmp_path,
        component_id=(
            "00000000-1111-2222-3333-444444444444"
        ),
        environment=runtime_environment,
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

    assert call["environment"] == {
        "BOOMI_ACCOUNT_ID": "TEST_ACCOUNT",
        "BOOMI_USERNAME": "test.user@example.invalid",
        "BOOMI_API_TOKEN": synthetic_token,
    }

    assert call["stdin_text"] is None