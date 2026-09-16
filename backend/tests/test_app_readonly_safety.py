from pathlib import Path

import pytest

from boomi_builder.adapters.powershell_runner import PowerShellRunner
from boomi_builder.settings import get_app_paths


APP_READONLY_ALLOWED_COMMANDS = {
    "get",
    "get-definition",
    "list-environments",
    "get-environment-extensions",
    "capability-inventory",
}


APP_READONLY_BLOCKED_COMMANDS = [
    "search",
    "export",
    "inspect",
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
]


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

    assert (
        "Workspace configuration file was not found"
        not in combined
    )

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

    assert "APP READ-ONLY SAFETY BLOCK" not in combined

    assert (
        "Workspace configuration file was not found"
        not in combined
    )

    assert "BOOMI_ACCOUNT_ID is missing" not in combined
    assert "BOOMI_USERNAME is missing" not in combined

    assert "DPAPI token file not found" in combined


def test_app_readonly_get_definition_skips_workspace_config_and_reaches_auth(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()
    runner = PowerShellRunner(timeout_seconds=10)

    result = runner.run_script(
        paths.boomi_cli_path,
        arguments=[
            "get-definition",
            "-Workspace",
            str(tmp_path),
            "-Id",
            "00000000-1111-2222-3333-444444444444",
            "-OutputFormat",
            "xml",
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

    assert "APP READ-ONLY SAFETY BLOCK" not in combined

    assert (
        "Workspace configuration file was not found"
        not in combined
    )

    assert "BOOMI_ACCOUNT_ID is missing" not in combined
    assert "BOOMI_USERNAME is missing" not in combined

    assert "DPAPI token file not found" in combined


def test_app_readonly_list_environments_reaches_auth(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()
    runner = PowerShellRunner(timeout_seconds=10)

    result = runner.run_script(
        paths.boomi_cli_path,
        arguments=[
            "list-environments",
            "-Workspace",
            str(tmp_path),
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

    assert "APP READ-ONLY SAFETY BLOCK" not in combined

    assert (
        "Workspace configuration file was not found"
        not in combined
    )

    assert "BOOMI_ACCOUNT_ID is missing" not in combined
    assert "BOOMI_USERNAME is missing" not in combined

    assert "DPAPI token file not found" in combined


def test_app_readonly_capability_inventory_reaches_auth(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()
    runner = PowerShellRunner(timeout_seconds=10)

    result = runner.run_script(
        paths.boomi_cli_path,
        arguments=[
            "capability-inventory",
            "-Workspace",
            str(tmp_path),
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

    assert "APP READ-ONLY SAFETY BLOCK" not in combined

    assert (
        "Workspace configuration file was not found"
        not in combined
    )

    assert "BOOMI_ACCOUNT_ID is missing" not in combined
    assert "BOOMI_USERNAME is missing" not in combined

    assert "DPAPI token file not found" in combined

def test_app_readonly_environment_extensions_reaches_auth(
    tmp_path: Path,
) -> None:
    paths = get_app_paths()
    runner = PowerShellRunner(timeout_seconds=10)

    result = runner.run_script(
        paths.boomi_cli_path,
        arguments=[
            "get-environment-extensions",
            "-Workspace",
            str(tmp_path),
            "-EnvironmentId",
            "00000000-1111-2222-3333-444444444444",
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

    assert "APP READ-ONLY SAFETY BLOCK" not in combined

    assert (
        "Workspace configuration file was not found"
        not in combined
    )

    assert "BOOMI_ACCOUNT_ID is missing" not in combined
    assert "BOOMI_USERNAME is missing" not in combined

    assert "DPAPI token file not found" in combined


@pytest.mark.parametrize(
    "command",
    APP_READONLY_BLOCKED_COMMANDS,
)
def test_app_readonly_blocks_every_non_allowed_command(
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

    normalized = combined.replace(
        "\r\n",
        "\n",
    )

    assert f"Command:\n{command}" in normalized

    assert (
        "Workspace configuration file was not found"
        not in combined
    )

    assert "BOOMI_ACCOUNT_ID is missing" not in combined
    assert "BOOMI_USERNAME is missing" not in combined

    assert f"{command} requires" not in combined


def test_app_readonly_allowlist_is_exact() -> None:
    assert APP_READONLY_ALLOWED_COMMANDS == {
        "get",
        "get-definition",
        "list-environments",
        "get-environment-extensions",
        "capability-inventory",
    }

    assert set(
        APP_READONLY_BLOCKED_COMMANDS
    ).isdisjoint(
        APP_READONLY_ALLOWED_COMMANDS
    )