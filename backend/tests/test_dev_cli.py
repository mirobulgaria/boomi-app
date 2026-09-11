from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from boomi_builder.adapters.boomi_engine import (
    BoomiComponentDefinitionResult,
    BoomiComponentResult,
)
from boomi_builder.dev_cli import build_parser
from boomi_builder.settings import get_app_paths


def test_dev_cli_enroll_parser() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "enroll",
            "--owner-user-id",
            "user-1",
        ]
    )

    assert args.command == "enroll"
    assert args.owner_user_id == "user-1"


def test_dev_cli_get_parser() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "get",
            "--connection-id",
            "connection-1",
            "--component-id",
            "component-1",
        ]
    )

    assert args.command == "get"
    assert args.connection_id == "connection-1"
    assert args.component_id == "component-1"


def test_dev_cli_definition_parser() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "definition",
            "--connection-id",
            "connection-1",
            "--component-id",
            "component-1",
        ]
    )

    assert args.command == "definition"
    assert args.connection_id == "connection-1"
    assert args.component_id == "component-1"


def test_runtime_paths_are_ready_for_dev_cli() -> None:
    paths = get_app_paths()

    assert paths.boomi_cli_path.is_file()
    assert paths.dpapi_helper_path.is_file()

    assert paths.connections_path == (
        paths.data_root / "connections.json"
    )

    assert paths.secrets_root == (
        paths.data_root / "secrets"
    )


def test_dev_cli_get_uses_connection_and_does_not_print_token(
    tmp_path: Path,
    capsys,
) -> None:
    synthetic_token = (
        "SYNTHETIC_DEV_CLI_TOKEN_NOT_REAL"
    )

    connection = SimpleNamespace(
        id="connection-1",
    )

    class FakeRepository:
        def get(self, connection_id):
            assert connection_id == "connection-1"
            return connection

    class FakeConnectionService:
        def resolve_runtime_environment(
            self,
            actual_connection,
        ):
            assert actual_connection is connection

            return {
                "BOOMI_ACCOUNT_ID": "TEST_ACCOUNT",
                "BOOMI_USERNAME": (
                    "test.user@example.invalid"
                ),
                "BOOMI_API_TOKEN": synthetic_token,
            }

    class FakeEngine:
        def __init__(self):
            self.calls = []

        def get_component(
            self,
            *,
            workspace,
            component_id,
            environment,
        ):
            self.calls.append(
                {
                    "workspace": workspace,
                    "component_id": component_id,
                    "environment": environment,
                }
            )

            return BoomiComponentResult(
                component_id="component-1",
                name="TEST - ZTE",
                type="process",
                version=7,
                current_version=True,
                deleted=False,
                folder_full_path="Example/Integration",
                branch_name="main",
            )

    fake_engine = FakeEngine()

    fake_paths = SimpleNamespace(
        data_root=tmp_path,
    )

    fake_runtime = (
        fake_paths,
        object(),
        FakeRepository(),
        FakeConnectionService(),
        object(),
        fake_engine,
    )

    from boomi_builder import dev_cli

    with patch(
        "boomi_builder.dev_cli.build_runtime",
        return_value=fake_runtime,
    ):
        exit_code = dev_cli.get_command(
            connection_id="connection-1",
            component_id="component-1",
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert len(fake_engine.calls) == 1

    call = fake_engine.calls[0]

    assert call["workspace"] == tmp_path
    assert call["component_id"] == "component-1"

    assert call["environment"] == {
        "BOOMI_ACCOUNT_ID": "TEST_ACCOUNT",
        "BOOMI_USERNAME": (
            "test.user@example.invalid"
        ),
        "BOOMI_API_TOKEN": synthetic_token,
    }

    assert "TEST - ZTE" in captured.out
    assert "component-1" in captured.out

    assert synthetic_token not in captured.out
    assert synthetic_token not in captured.err


def test_dev_cli_definition_downloads_validated_xml_without_printing_token(
    tmp_path: Path,
    capsys,
) -> None:
    synthetic_token = (
        "SYNTHETIC_DEFINITION_TOKEN_NOT_REAL"
    )

    component_id = (
        "1548d6fa-15b7-41e0-84ca-45dd46668bed"
    )

    component_xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="{component_id}"
    name="SP S1 - Process MR Order to ZTE"
    type="process"
    version="7">
  <object>
    <process>
      <shapes />
    </process>
  </object>
</Component>
"""

    connection = SimpleNamespace(
        id="connection-1",
    )

    class FakeRepository:
        def get(self, connection_id):
            assert connection_id == "connection-1"
            return connection

    class FakeConnectionService:
        def resolve_runtime_environment(
            self,
            actual_connection,
        ):
            assert actual_connection is connection

            return {
                "BOOMI_ACCOUNT_ID": "TEST_ACCOUNT",
                "BOOMI_USERNAME": (
                    "test.user@example.invalid"
                ),
                "BOOMI_API_TOKEN": synthetic_token,
            }

    class FakeEngine:
        def __init__(self):
            self.calls = []

        def get_component_definition(
            self,
            *,
            workspace,
            component_id,
            environment,
        ):
            self.calls.append(
                {
                    "workspace": workspace,
                    "component_id": component_id,
                    "environment": environment,
                }
            )

            return BoomiComponentDefinitionResult(
                component_id=component_id,
                name=(
                    "SP S1 - Process MR Order to ZTE"
                ),
                type="process",
                version=7,
                xml=component_xml,
            )

    fake_engine = FakeEngine()

    fake_paths = SimpleNamespace(
        data_root=tmp_path,
    )

    fake_runtime = (
        fake_paths,
        object(),
        FakeRepository(),
        FakeConnectionService(),
        object(),
        fake_engine,
    )

    from boomi_builder import dev_cli

    with patch(
        "boomi_builder.dev_cli.build_runtime",
        return_value=fake_runtime,
    ):
        exit_code = dev_cli.definition_command(
            connection_id="connection-1",
            component_id=component_id,
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert len(fake_engine.calls) == 1

    call = fake_engine.calls[0]

    assert call["workspace"] == tmp_path
    assert call["component_id"] == component_id

    assert call["environment"] == {
        "BOOMI_ACCOUNT_ID": "TEST_ACCOUNT",
        "BOOMI_USERNAME": (
            "test.user@example.invalid"
        ),
        "BOOMI_API_TOKEN": synthetic_token,
    }

    expected_path = (
        tmp_path
        / "discovery"
        / component_id
        / "component.xml"
    )

    assert expected_path.is_file()

    assert (
        expected_path.read_text(
            encoding="utf-8"
        )
        == component_xml
    )

    assert component_id in captured.out
    assert (
        "SP S1 - Process MR Order to ZTE"
        in captured.out
    )

    assert str(expected_path) in captured.out

    assert component_xml not in captured.out
    assert synthetic_token not in captured.out
    assert synthetic_token not in captured.err