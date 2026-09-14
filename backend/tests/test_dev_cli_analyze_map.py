from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from boomi_builder import dev_cli


COMPONENT_ID = (
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
)

SOURCE_PROFILE_ID = (
    "11111111-1111-1111-1111-111111111111"
)

TARGET_PROFILE_ID = (
    "22222222-2222-2222-2222-222222222222"
)


MAP_XML = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="{COMPONENT_ID}"
    name="Synthetic Customer Map"
    type="transform.map"
    version="1">
  <object>
    <Map
        xmlns=""
        fromProfile="{SOURCE_PROFILE_ID}"
        toProfile="{TARGET_PROFILE_ID}">
      <Mappings>
        <Mapping
            fromKey="10"
            fromKeyPath="*[@key='1']/*[@key='10']"
            fromNamePath="Customer/Id"
            fromType="profile"
            toKey="20"
            toKeyPath="*[@key='2']/*[@key='20']"
            toNamePath="Party/ExternalId"
            toType="profile" />
        <Mapping
            fromKey="11"
            fromKeyPath="*[@key='1']/*[@key='11']"
            fromNamePath="Customer/Name"
            fromType="profile"
            toKey="21"
            toKeyPath="*[@key='2']/*[@key='21']"
            toNamePath="Party/DisplayName"
            toType="profile" />
      </Mappings>
      <Functions optimizeExecutionOrder="true" />
      <Defaults />
      <DocumentCacheJoins />
    </Map>
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
        MAP_XML,
        encoding="utf-8",
        newline="",
    )

    return SimpleNamespace(
        data_root=data_root,
    )


def test_dev_cli_analyze_map_parser() -> None:
    parser = dev_cli.build_parser()

    args = parser.parse_args(
        [
            "analyze-map",
            "--component-id",
            COMPONENT_ID,
        ]
    )

    assert args.command == "analyze-map"
    assert args.component_id == COMPONENT_ID


def test_analyze_map_is_local_only(
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
        exit_code = dev_cli.analyze_map_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    build_runtime.assert_not_called()

    assert (
        "Boomi transform map analysis"
        in captured.out
    )

    assert COMPONENT_ID in captured.out

    assert (
        f"Source profile ID        : "
        f"{SOURCE_PROFILE_ID}"
        in captured.out
    )

    assert (
        f"Target profile ID        : "
        f"{TARGET_PROFILE_ID}"
        in captured.out
    )

    assert (
        "Source equals target     : False"
        in captured.out
    )

    assert (
        "Mapping count            : 2"
        in captured.out
    )

    assert (
        "Identity mapping count   : 0"
        in captured.out
    )

    assert (
        "All mappings identity    : False"
        in captured.out
    )

    assert (
        "Optimize execution order : True"
        in captured.out
    )


def test_analyze_map_prints_sections_and_mappings(
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
        exit_code = dev_cli.analyze_map_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "Functions         : "
        "present=True descendants=0"
        in captured.out
    )

    assert (
        "Defaults          : "
        "present=True descendants=0"
        in captured.out
    )

    assert (
        "DocumentCacheJoins: "
        "present=True descendants=0"
        in captured.out
    )

    assert (
        "Customer/Id -> "
        "profile | Party/ExternalId | "
        "identity=False"
        in captured.out
    )

    assert (
        "Customer/Name -> "
        "profile | Party/DisplayName | "
        "identity=False"
        in captured.out
    )


def test_analyze_map_does_not_print_component_xml(
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
        exit_code = dev_cli.analyze_map_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert MAP_XML not in captured.out
    assert MAP_XML not in captured.err


def test_analyze_map_rejects_missing_local_definition(
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
            dev_cli.analyze_map_command(
                component_id=COMPONENT_ID,
            )