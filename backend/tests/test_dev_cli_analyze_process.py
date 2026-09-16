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
    name="Synthetic Process"
    type="process"
    version="1">
  <object>
    <process
        xmlns=""
        workload="general"
        enableUserLog="false">
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
                toShape="mapShape" />
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
                toShape="sendShape" />
          </dragpoints>
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
                toShape="returnShape" />
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
      </shapes>
    </process>
  </object>
</Component>
"""


def _prepare_component(
    tmp_path: Path,
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
        PROCESS_XML,
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
        exit_code = (
            dev_cli.analyze_process_command(
                component_id=COMPONENT_ID,
            )
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    build_runtime.assert_not_called()

    assert (
        "Boomi process analysis"
        in captured.out
    )

    assert COMPONENT_ID in captured.out

    assert (
        "Shape count          : 4"
        in captured.out
    )

    assert (
        "Transition count     : 3"
        in captured.out
    )

    assert (
        "Component references : 3"
        in captured.out
    )

    assert (
        "Unique component IDs : 3"
        in captured.out
    )


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
        exit_code = (
            dev_cli.analyze_process_command(
                component_id=COMPONENT_ID,
            )
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
        exit_code = (
            dev_cli.analyze_process_command(
                component_id=COMPONENT_ID,
            )
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
        exit_code = (
            dev_cli.analyze_process_command(
                component_id=COMPONENT_ID,
            )
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
        exit_code = (
            dev_cli.analyze_process_command(
                component_id=COMPONENT_ID,
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


def test_analyze_process_does_not_print_raw_xml(
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
        exit_code = (
            dev_cli.analyze_process_command(
                component_id=COMPONENT_ID,
            )
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