from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from boomi_builder import dev_cli


COMPONENT_ID = (
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
)

MAP_ID = (
    "11111111-1111-1111-1111-111111111111"
)

CONNECTION_ID = (
    "22222222-2222-2222-2222-222222222222"
)

OPERATION_ID = (
    "33333333-3333-3333-3333-333333333333"
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


PROCESS_XML = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="{COMPONENT_ID}"
    name="Synthetic Order Process"
    type="process"
    version="1">
  <object>
    <process
        xmlns=""
        allowDynamicCredentials="false"
        authorizationMode="none"
        enableUserLog="false"
        passwordPolicy="standard"
        stopProcessingIfZeroDocuments="true"
        workload="general">
      <shapes>
        <shape
            image="start"
            name="startShape"
            shapetype="start"
            userlabel=""
            x="100.0"
            y="100.0">
          <configuration>
            <passthroughaction />
          </configuration>
          <dragpoints>
            <dragpoint
                name="startShape.out"
                toShape="mapShape"
                x="200.0"
                y="100.0" />
          </dragpoints>
        </shape>

        <shape
            image="map_icon"
            name="mapShape"
            shapetype="map"
            userlabel="Transform Customer"
            x="300.0"
            y="100.0">
          <configuration>
            <map mapId="{MAP_ID}" />
          </configuration>
          <dragpoints>
            <dragpoint
                name="mapShape.out"
                toShape="sendShape"
                x="400.0"
                y="100.0" />
          </dragpoints>
        </shape>

        <shape
            image="returndocuments_icon"
            name="returnShape"
            shapetype="returndocuments"
            userlabel=""
            x="700.0"
            y="100.0">
          <configuration>
            <returndocuments label="" />
          </configuration>
          <dragpoints />
        </shape>

        <shape
            image="connectoraction_icon"
            name="sendShape"
            shapetype="connectoraction"
            userlabel="Send Customer"
            x="500.0"
            y="100.0">
          <configuration>
            <connectoraction
                actionType="EXECUTE"
                allowDynamicCredentials="false"
                connectionId="{CONNECTION_ID}"
                connectorType="syntheticconnector"
                operationId="{OPERATION_ID}"
                password="{SYNTHETIC_PASSWORD}"
                apiToken="{SYNTHETIC_TOKEN}"
                authorization="{SYNTHETIC_AUTH}">
              <parameters>
                <parameter
                    name="mode"
                    value="example" />
                <privateKey>
                  {SYNTHETIC_PRIVATE_KEY}
                </privateKey>
              </parameters>
              <dynamicProperties />
            </connectoraction>
          </configuration>
          <dragpoints>
            <dragpoint
                name="sendShape.out"
                toShape="returnShape"
                x="600.0"
                y="100.0" />
          </dragpoints>
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""


def _prepare_component(
    tmp_path: Path,
    xml_text: str = PROCESS_XML,
) -> SimpleNamespace:
    data_root = tmp_path / "data"

    component_path = (
        data_root
        / "discovery"
        / COMPONENT_ID
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


def test_dev_cli_analyze_process_parser() -> None:
    parser = dev_cli.build_parser()

    args = parser.parse_args(
        [
            "analyze-process",
            "--component-id",
            COMPONENT_ID,
        ]
    )

    assert args.command == "analyze-process"
    assert args.component_id == COMPONENT_ID


def test_analyze_process_parser_does_not_require_connection_id() -> None:
    parser = dev_cli.build_parser()

    args = parser.parse_args(
        [
            "analyze-process",
            "--component-id",
            COMPONENT_ID,
        ]
    )

    assert not hasattr(args, "connection_id")


def test_analyze_process_is_local_only(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ), patch(
        "boomi_builder.dev_cli.build_runtime"
    ) as build_runtime:
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    build_runtime.assert_not_called()

    assert (
        "Boomi process analysis"
        in captured.out
    )

    assert COMPONENT_ID in captured.out


def test_analyze_process_shows_generic_process_facts(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "Shape count          : 4" in captured.out
    assert "Transition count     : 3" in captured.out
    assert "Component references : 3" in captured.out
    assert "Unique component IDs : 3" in captured.out


def test_analyze_process_prints_graph_and_references(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "startShape -> mapShape"
        in captured.out
    )

    assert (
        "mapShape -> sendShape"
        in captured.out
    )

    assert (
        "sendShape -> returnShape"
        in captured.out
    )

    assert MAP_ID in captured.out
    assert CONNECTION_ID in captured.out
    assert OPERATION_ID in captured.out

    assert "mapId" in captured.out
    assert "connectionId" in captured.out
    assert "operationId" in captured.out


def test_analyze_process_prints_safe_configuration_metadata(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "@actionType = EXECUTE"
        in captured.out
    )

    assert (
        "@allowDynamicCredentials = false"
        in captured.out
    )

    assert (
        "@connectorType = syntheticconnector"
        in captured.out
    )

    assert (
        "@connectionId = "
        f"{CONNECTION_ID}"
        in captured.out
    )

    assert (
        "@operationId = "
        f"{OPERATION_ID}"
        in captured.out
    )

    assert (
        "@value = example"
        in captured.out
    )


def test_analyze_process_shows_process_settings_with_redaction(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "Process settings" in captured.out
    assert (
        "allowDynamicCredentials = false"
        in captured.out
    )
    assert (
        "authorizationMode = none"
        in captured.out
    )
    assert (
        "passwordPolicy = standard"
        in captured.out
    )


def test_analyze_process_shows_shapes_with_metadata(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "Shapes" in captured.out
    assert "Name                : startShape" in captured.out
    assert "Name                : mapShape" in captured.out
    assert "Name                : returnShape" in captured.out
    assert "Name                : sendShape" in captured.out


def test_analyze_process_shows_transitions_from_analysis(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "Transitions" in captured.out
    assert (
        "startShape -> mapShape | dragpoint=startShape.out"
        in captured.out
    )
    assert (
        "mapShape -> sendShape | dragpoint=mapShape.out"
        in captured.out
    )
    assert (
        "sendShape -> returnShape | dragpoint=sendShape.out"
        in captured.out
    )


def test_analyze_process_shows_component_references(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "Component references" in captured.out
    assert MAP_ID in captured.out
    assert CONNECTION_ID in captured.out
    assert OPERATION_ID in captured.out

    assert "mapId" in captured.out
    assert "connectionId" in captured.out
    assert "operationId" in captured.out


def test_security_leakage_test_synthetic_secrets_are_redacted(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "@password = <REDACTED>"
        in captured.out
    )

    assert (
        "@apiToken = <REDACTED>"
        in captured.out
    )

    assert (
        "@authorization = <REDACTED>"
        in captured.out
    )

    assert SYNTHETIC_PASSWORD not in captured.out
    assert SYNTHETIC_TOKEN not in captured.out
    assert SYNTHETIC_AUTH not in captured.out

    assert SYNTHETIC_PASSWORD not in captured.err
    assert SYNTHETIC_TOKEN not in captured.err
    assert SYNTHETIC_AUTH not in captured.err


def test_analyze_process_redacts_sensitive_attributes(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "@password = <REDACTED>"
        in captured.out
    )

    assert (
        "@apiToken = <REDACTED>"
        in captured.out
    )

    assert (
        "@authorization = <REDACTED>"
        in captured.out
    )

    assert SYNTHETIC_PASSWORD not in captured.out
    assert SYNTHETIC_TOKEN not in captured.out
    assert SYNTHETIC_AUTH not in captured.out

    assert SYNTHETIC_PASSWORD not in captured.err
    assert SYNTHETIC_TOKEN not in captured.err
    assert SYNTHETIC_AUTH not in captured.err


def test_false_positive_cli_test_safe_metadata_remains_visible(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "allowDynamicCredentials = false" in captured.out
    assert "authorizationMode = none" in captured.out
    assert "passwordPolicy = standard" in captured.out


def test_analyze_process_shows_configuration_tree_generically(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "connectoraction" in captured.out
    assert "parameters" in captured.out
    assert "parameter" in captured.out
    assert "dynamicProperties" in captured.out
    assert "privateKey" in captured.out


def test_analyze_process_redacts_sensitive_attribute_values(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "@password = <REDACTED>"
        in captured.out
    )

    assert SYNTHETIC_PASSWORD not in captured.out


def test_analyze_process_redacts_sensitive_element_text(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
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


def test_analyze_process_redacts_component_reference_when_attribute_name_sensitive(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert MAP_ID in captured.out
    assert CONNECTION_ID in captured.out
    assert OPERATION_ID in captured.out

    assert "mapId" in captured.out
    assert "connectionId" in captured.out
    assert "operationId" in captured.out


def test_analyze_process_does_not_dump_raw_xml(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert PROCESS_XML not in captured.out
    assert PROCESS_XML not in captured.err


def test_analyze_process_rejects_missing_local_definition(
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
            dev_cli.analyze_process_command(
                component_id=COMPONENT_ID,
            )


def test_analyze_process_execution_order_from_transitions_not_xml_order(
    tmp_path: Path,
    capsys,
) -> None:
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    name="Test Process"
    type="process"
    version="1">
  <object>
    <process xmlns="" workload="general">
      <shapes>
        <shape
            image="start"
            name="startShape"
            shapetype="start"
            x="100.0"
            y="100.0">
          <configuration>
            <passthroughaction />
          </configuration>
          <dragpoints>
            <dragpoint
                name="startShape.out"
                toShape="mapShape"
                x="200.0"
                y="100.0" />
          </dragpoints>
        </shape>

        <shape
            image="map_icon"
            name="mapShape"
            shapetype="map"
            x="300.0"
            y="100.0">
          <configuration>
            <map mapId="11111111-1111-1111-1111-111111111111" />
          </configuration>
          <dragpoints>
            <dragpoint
                name="mapShape.out"
                toShape="sendShape"
                x="400.0"
                y="100.0" />
          </dragpoints>
        </shape>

        <shape
            image="returndocuments_icon"
            name="returnShape"
            shapetype="returndocuments"
            x="700.0"
            y="100.0">
          <configuration>
            <returndocuments label="" />
          </configuration>
          <dragpoints />
        </shape>

        <shape
            image="connectoraction_icon"
            name="sendShape"
            shapetype="connectoraction"
            x="500.0"
            y="100.0">
          <configuration>
            <connectoraction
                actionType="EXECUTE"
                connectionId="22222222-2222-2222-2222-222222222222"
                connectorType="example">
              <parameters />
              <dynamicProperties />
            </connectoraction>
          </configuration>
          <dragpoints>
            <dragpoint
                name="sendShape.out"
                toShape="returnShape"
                x="600.0"
                y="100.0" />
          </dragpoints>
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""

    fake_paths = _prepare_component(
        tmp_path,
        xml_text=xml,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "startShape -> mapShape | dragpoint=startShape.out"
        in captured.out
    )
    assert (
        "mapShape -> sendShape | dragpoint=mapShape.out"
        in captured.out
    )
    assert (
        "sendShape -> returnShape | dragpoint=sendShape.out"
        in captured.out
    )


def test_analyze_process_uses_project_neutral_names(
    tmp_path: Path,
    capsys,
) -> None:
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    name="Customer Process"
    type="process"
    version="1">
  <object>
    <process xmlns="" workload="general">
      <shapes>
        <shape
            image="start"
            name="customerStart"
            shapetype="start"
            x="100.0"
            y="100.0">
          <configuration>
            <passthroughaction />
          </configuration>
          <dragpoints>
            <dragpoint
                name="customerStart.out"
                toShape="orderMap"
                x="200.0"
                y="100.0" />
          </dragpoints>
        </shape>

        <shape
            image="map_icon"
            name="orderMap"
            shapetype="map"
            x="300.0"
            y="100.0">
          <configuration>
            <map mapId="11111111-1111-1111-1111-111111111111" />
          </configuration>
          <dragpoints />
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""

    fake_paths = _prepare_component(
        tmp_path,
        xml_text=xml,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "customerStart" in captured.out
    assert "orderMap" in captured.out


def test_analyze_process_does_not_contain_sap_zte_references(
    tmp_path: Path,
    capsys,
) -> None:
    fake_paths = _prepare_component(
        tmp_path
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "SAP" not in captured.out
    assert "ZTE" not in captured.out
    assert "ZDVMBG_MR_REQUEST" not in captured.out
    assert "ABLBELNR" not in captured.out


def test_adversarial_shape_name_password_does_not_redact_userlabel(
    tmp_path: Path,
    capsys,
) -> None:
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    name="Adversarial Test"
    type="process"
    version="1">
  <object>
    <process xmlns="" workload="general">
      <shapes>
        <shape
            image="start"
            name="password"
            shapetype="start"
            userlabel="Visible safe label"
            x="100.0"
            y="100.0">
          <configuration>
            <passthroughaction />
          </configuration>
          <dragpoints />
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""

    fake_paths = _prepare_component(
        tmp_path,
        xml_text=xml,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_process_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert "password" in captured.out
    assert "Visible safe label" in captured.out
