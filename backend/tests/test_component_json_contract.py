import json
from pathlib import Path

from boomi_builder.adapters.powershell_runner import PowerShellRunner
from boomi_builder.settings import get_app_paths


def test_component_json_contract() -> None:
    paths = get_app_paths()

    probe = (
        Path(__file__).parent
        / "fixtures"
        / "component_json_probe.ps1"
    )

    read_file = paths.engine_root / "lib" / "Boomi.Read.ps1"

    runner = PowerShellRunner(timeout_seconds=10)

    result = runner.run_script(
        probe,
        arguments=[
            "-ReadFile",
            str(read_file),
        ],
    )

    assert result.exit_code == 0
    assert result.stderr == ""

    payload = json.loads(result.stdout)

    assert payload == {
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

    assert isinstance(payload["success"], bool)
    assert isinstance(payload["data"]["version"], int)
    assert isinstance(
        payload["data"]["currentVersion"],
        bool,
    )
    assert isinstance(payload["data"]["deleted"], bool)