from pathlib import Path

from boomi_builder.adapters.powershell_runner import PowerShellRunner
from boomi_builder.settings import get_app_paths


def test_runtime_auth_does_not_require_dpapi_token_file(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()

    probe = (
        Path(__file__).parent
        / "fixtures"
        / "runtime_auth_probe.ps1"
    )

    runner = PowerShellRunner(timeout_seconds=10)

    synthetic_token = "TEST_TOKEN_NOT_A_REAL_SECRET"

    result = runner.run_script(
        probe,
        arguments=[
            "-CommonFile",
            str(paths.engine_root / "lib" / "Boomi.Common.ps1"),
            "-WorkspaceRoot",
            str(tmp_path),
        ],
        environment={
            "BOOMI_ACCOUNT_ID": "TEST_ACCOUNT",
            "BOOMI_USERNAME": "test.user@example.invalid",
            "BOOMI_API_TOKEN": synthetic_token,
        },
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "RUNTIME_AUTH_OK" in result.stdout

    assert synthetic_token not in result.stdout
    assert synthetic_token not in result.stderr