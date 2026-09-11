from pathlib import Path

from boomi_builder.adapters.powershell_runner import PowerShellRunner
from boomi_builder.settings import get_app_paths


def test_app_readonly_blocks_delete_before_authentication(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()
    runner = PowerShellRunner(timeout_seconds=10)

    result = runner.run_script(
        paths.boomi_cli_path,
        arguments=[
            "delete",
            "-Workspace",
            str(tmp_path),
            "-Id",
            "00000000-1111-2222-3333-444444444444",
            "-RuntimeMode",
            "app-readonly",
        ],
        environment={
            "BOOMI_ACCOUNT_ID": "",
            "BOOMI_USERNAME": "",
            "BOOMI_API_TOKEN": "",
        },
    )

    combined = result.stdout + result.stderr

    assert result.exit_code != 0

    assert "APP READ-ONLY SAFETY BLOCK" in combined
    assert "delete" in combined

    # The safety guard must execute before workspace config.
    assert (
        "Workspace configuration file was not found"
        not in combined
    )

    # The safety guard must execute before authentication.
    assert "BOOMI_ACCOUNT_ID is missing" not in combined
    assert "BOOMI_USERNAME is missing" not in combined


def test_app_readonly_get_skips_workspace_config_and_reaches_auth(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()
    runner = PowerShellRunner(timeout_seconds=10)

    result = runner.run_script(
        paths.boomi_cli_path,
        arguments=[
            "get",
            "-Workspace",
            str(tmp_path),
            "-Id",
            "00000000-1111-2222-3333-444444444444",
            "-OutputFormat",
            "json",
            "-RuntimeMode",
            "app-readonly",
        ],
        environment={
            "BOOMI_ACCOUNT_ID": "APP_READONLY_TEST_ACCOUNT",
            "BOOMI_USERNAME": "app-readonly-test@example.invalid",
            "BOOMI_API_TOKEN": "",
        },
    )

    combined = result.stdout + result.stderr

    assert result.exit_code != 0

    # app-readonly/get is explicitly allowed.
    assert "APP READ-ONLY SAFETY BLOCK" not in combined

    # Full workspace configuration must have been skipped.
    assert (
        "Workspace configuration file was not found"
        not in combined
    )

    # Synthetic process-level account and username must have
    # passed their authentication validation.
    assert "BOOMI_ACCOUNT_ID is missing" not in combined
    assert "BOOMI_USERNAME is missing" not in combined

    # With no runtime token and no DPAPI file in the temporary
    # workspace, authentication must stop here, before any
    # Boomi HTTP request can occur.
    assert "DPAPI token file not found" in combined

import pytest


@pytest.mark.parametrize(
    "command",
    [
        "search",
        "export",
        "inspect",
        "list-environments",
        "get-environment-extensions",
        "create-preview",
        "create",
        "create-empty-process",
        "set-label",
        "clone-process",
        "set-process-call",
        "clone-component",
        "set-map",
        "set-connector",
        "delete",
        "restore",
    ],
)
def test_app_readonly_blocks_every_command_except_get(
    tmp_path: Path,
    command: str,
) -> None:
    paths = get_app_paths()
    runner = PowerShellRunner(timeout_seconds=10)

    result = runner.run_script(
        paths.boomi_cli_path,
        arguments=[
            command,
            "-Workspace",
            str(tmp_path),
            "-RuntimeMode",
            "app-readonly",
        ],
        environment={
            "BOOMI_ACCOUNT_ID": "",
            "BOOMI_USERNAME": "",
            "BOOMI_API_TOKEN": "",
        },
    )

    combined = result.stdout + result.stderr

    assert result.exit_code != 0

    assert "APP READ-ONLY SAFETY BLOCK" in combined
    assert f"Command:\n{command}" in combined.replace("\r\n", "\n")

    # Must fail before full workspace configuration.
    assert (
        "Workspace configuration file was not found"
        not in combined
    )

    # Must fail before authentication.
    assert "BOOMI_ACCOUNT_ID is missing" not in combined
    assert "BOOMI_USERNAME is missing" not in combined

    # It must therefore never reach command-specific validation.
    assert f"{command} requires" not in combined