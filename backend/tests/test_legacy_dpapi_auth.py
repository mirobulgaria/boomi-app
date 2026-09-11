from pathlib import Path

from boomi_builder.adapters.powershell_runner import PowerShellRunner
from boomi_builder.settings import get_app_paths


def test_legacy_dpapi_auth_fallback_still_works(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()

    probe = (
        Path(__file__).parent
        / "fixtures"
        / "legacy_dpapi_auth_probe.ps1"
    )

    runner = PowerShellRunner(timeout_seconds=10)

    synthetic_token = "LEGACY_DPAPI_TEST_TOKEN_NOT_REAL"

    result = runner.run_script(
        probe,
        arguments=[
            "-CommonFile",
            str(paths.engine_root / "lib" / "Boomi.Common.ps1"),
            "-WorkspaceRoot",
            str(tmp_path),
        ],
        environment={
            "BOOMI_ACCOUNT_ID": "LEGACY_TEST_ACCOUNT",
            "BOOMI_USERNAME": "legacy.test@example.invalid",
            "BOOMI_API_TOKEN": "",
        },
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "LEGACY_DPAPI_AUTH_OK" in result.stdout

    assert synthetic_token not in result.stdout
    assert synthetic_token not in result.stderr