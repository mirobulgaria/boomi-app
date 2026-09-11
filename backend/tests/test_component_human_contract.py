from pathlib import Path

from boomi_builder.adapters.powershell_runner import PowerShellRunner
from boomi_builder.settings import get_app_paths


def test_component_human_contract_is_preserved() -> None:
    paths = get_app_paths()

    probe = (
        Path(__file__).parent
        / "fixtures"
        / "component_human_probe.ps1"
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

    assert "Boomi Component" in result.stdout
    assert "Name            : TEST — Български ↔ ZTE" in result.stdout
    assert "Type            : process" in result.stdout
    assert (
        "Component ID    : "
        "00000000-1111-2222-3333-444444444444"
        in result.stdout
    )
    assert "Version         : 7" in result.stdout
    assert "Current Version : true" in result.stdout
    assert "Deleted         : false" in result.stdout
    assert "Folder          : Example/Integration" in result.stdout
    assert "Branch          : main" in result.stdout