from pathlib import Path

from boomi_builder.adapters.powershell_runner import PowerShellRunner


def test_powershell_runner_captures_utf8_output() -> None:
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "unicode_probe.ps1"
    )

    runner = PowerShellRunner(timeout_seconds=10)
    result = runner.run_script(fixture)

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "BOOMI_BUILDER_POWERSHELL_OK" in result.stdout
    assert "Български — SAP ↔ ZTE" in result.stdout