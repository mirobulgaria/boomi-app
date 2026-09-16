from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from boomi_builder import dev_cli


SETTINGS_ID = (
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
)

OPERATION_ID = (
    "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
)

REFERENCE_ID = (
    "11111111-1111-1111-1111-111111111111"
)

SYNTHETIC_PASSWORD = (
    "SYNTHETIC_PASSWORD_MUST_NOT_LEAK"
)

SYNTHETIC_TOKEN = (
    "SYNTHETIC_TOKEN_MUST_NOT_LEAK"
)

SYNTHETIC_AUTH = (
    "SYNTHETIC_AUTH_MUST_NOT_LEAK"
)

SYNTHETIC_PRIVATE_KEY = (
    "SYNTHETIC_PRIVATE_KEY_MUST_NOT_LEAK"
)


SETTINGS_XML = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="{SETTINGS_ID}"
    name="Synthetic Connector Settings"
    type="connector-settings"
    version="1">
  <object>
    <SyntheticConnectionConfig xmlns="">
      <field
          id="endpoint"
          type="string"
          value="https://example.invalid/service" />
      <field
          id="password"
          type="password"
          value="{SYNTHETIC_PASSWORD}" />
      <field
          id="apiToken"
          type="string"
          value="{SYNTHETIC_TOKEN}" />
      <field
          id="authorization"
          type="string"
          value="{SYNTHETIC_AUTH}" />
      <field
          id="advancedOptions"
          type="custom">
        <SyntheticOptions mode="example">
          <privateKey>
            {SYNTHETIC_PRIVATE_KEY}
          </privateKey>
        </SyntheticOptions>
      </field>
    </SyntheticConnectionConfig>
  </object>
</Component>
"""


OPERATION_XML = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="{OPERATION_ID}"
    name="Synthetic Connector Operation"
    type="connector-action"
    version="1">
  <object>
    <SyntheticOperation
        xmlns=""
        returnApplicationErrors="false">
      <Configuration>
        <SyntheticOperationConfig
            operationType="EXECUTE">
          <field
              id="requestEnvelope"
              type="boolean"
              value="true" />
          <SyntheticReference
              componentId="{REFERENCE_ID}" />
        </SyntheticOperationConfig>
      </Configuration>
    </SyntheticOperation>
  </object>
</Component>
"""


def _prepare_component(
    tmp_path: Path,
    *,
    component_id: str,
    xml_text: str,
) -> SimpleNamespace:
    data_root = tmp_path / "data"

    component_path = (
        data_root
        / "discovery"
        / component_id
        / "component.xml"
    )

    component_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    component_path.write_text(
        xml_text,
        encoding="utf-8",
        newline="",
    )

    return SimpleNamespace(
        data_root=data_root,
    )


def test_dev_cli_analyze_connector_parser() -> None:
    parser = dev_cli.build_parser()

    args = parser.parse_args(
        [
            "analyze-connector",
            "--component-id",
            SETTINGS_ID,
        ]
    )

    assert args.command == "analyze-connector"
    assert args.component_id == SETTINGS_ID


def test_analyze_connector_is_local_only(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path,
        component_id=SETTINGS_ID,
        xml_text=SETTINGS_XML,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ), patch(
        "boomi_builder.dev_cli.build_runtime"
    ) as build_runtime:
        exit_code = (
            dev_cli.analyze_connector_command(
                component_id=SETTINGS_ID,
            )
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    build_runtime.assert_not_called()

    assert (
        "Boomi connector component analysis"
        in captured.out
    )

    assert SETTINGS_ID in captured.out

    assert (
        "Component type      : connector-settings"
        in captured.out
    )

    assert (
        "Configuration root  : "
        "SyntheticConnectionConfig"
        in captured.out
    )

    assert (
        "Field count         : 5"
        in captured.out
    )


def test_analyze_connector_prints_safe_field_values(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path,
        component_id=SETTINGS_ID,
        xml_text=SETTINGS_XML,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = (
            dev_cli.analyze_connector_command(
                component_id=SETTINGS_ID,
            )
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "endpoint | type=string | "
        "value=https://example.invalid/service"
        in captured.out
    )

    assert (
        "password | type=password | "
        "value=<REDACTED>"
        in captured.out
    )

    assert (
        "apiToken | type=string | "
        "value=<REDACTED>"
        in captured.out
    )

    assert (
        "authorization | type=string | "
        "value=<REDACTED>"
        in captured.out
    )


def test_analyze_connector_redacts_field_values_in_tree(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path,
        component_id=SETTINGS_ID,
        xml_text=SETTINGS_XML,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = (
            dev_cli.analyze_connector_command(
                component_id=SETTINGS_ID,
            )
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "@id = password"
        in captured.out
    )

    assert (
        "@value = <REDACTED>"
        in captured.out
    )

    assert SYNTHETIC_PASSWORD not in captured.out
    assert SYNTHETIC_TOKEN not in captured.out
    assert SYNTHETIC_AUTH not in captured.out

    assert SYNTHETIC_PASSWORD not in captured.err
    assert SYNTHETIC_TOKEN not in captured.err
    assert SYNTHETIC_AUTH not in captured.err


def test_analyze_connector_redacts_sensitive_element_text(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path,
        component_id=SETTINGS_ID,
        xml_text=SETTINGS_XML,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = (
            dev_cli.analyze_connector_command(
                component_id=SETTINGS_ID,
            )
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "privateKey" in captured.out

    assert (
        "#text = <REDACTED>"
        in captured.out
    )

    assert (
        SYNTHETIC_PRIVATE_KEY
        not in captured.out
    )

    assert (
        SYNTHETIC_PRIVATE_KEY
        not in captured.err
    )


def test_analyze_connector_prints_operation_and_reference(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path,
        component_id=OPERATION_ID,
        xml_text=OPERATION_XML,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = (
            dev_cli.analyze_connector_command(
                component_id=OPERATION_ID,
            )
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "Component type      : connector-action"
        in captured.out
    )

    assert (
        "Configuration root  : "
        "SyntheticOperation"
        in captured.out
    )

    assert (
        "requestEnvelope | "
        "type=boolean | value=true"
        in captured.out
    )

    assert REFERENCE_ID in captured.out

    assert (
        "componentId"
        in captured.out
    )


def test_analyze_connector_does_not_print_raw_xml(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path,
        component_id=SETTINGS_ID,
        xml_text=SETTINGS_XML,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = (
            dev_cli.analyze_connector_command(
                component_id=SETTINGS_ID,
            )
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert SETTINGS_XML not in captured.out
    assert SETTINGS_XML not in captured.err


def test_analyze_connector_rejects_missing_local_definition(
    tmp_path: Path,
) -> None:
    fake_paths = SimpleNamespace(
        data_root=tmp_path / "data",
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        with pytest.raises(
            FileNotFoundError,
            match=(
                "Local component definition "
                "was not found"
            ),
        ):
            dev_cli.analyze_connector_command(
                component_id=SETTINGS_ID,
            )