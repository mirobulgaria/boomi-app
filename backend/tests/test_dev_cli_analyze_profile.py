from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from boomi_builder import dev_cli


COMPONENT_ID = (
    "798a16a7-de85-4dd1-bee7-5b80fd84a734"
)


PROFILE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="798a16a7-de85-4dd1-bee7-5b80fd84a734"
    name="Synthetic XML Profile"
    type="profile.xml"
    version="1">
  <object>
    <XMLProfile
        xmlns=""
        modelVersion="2"
        strict="true">
      <DataElements>
        <XMLElement
            dataType="character"
            isMappable="true"
            isNode="true"
            key="1"
            maxOccurs="1"
            minOccurs="1"
            name="ROOT">
          <XMLElement
              dataType="character"
              isMappable="true"
              isNode="true"
              key="2"
              maxOccurs="999999999"
              minOccurs="1"
              name="ITEM">
            <XMLAttribute
                dataType="character"
                isMappable="true"
                isNode="true"
                key="3"
                name="SEGMENT"
                required="true"
                validateData="false" />
          </XMLElement>
        </XMLElement>
      </DataElements>
    </XMLProfile>
  </object>
</Component>
"""


def test_dev_cli_analyze_profile_parser() -> None:
    parser = dev_cli.build_parser()

    args = parser.parse_args(
        [
            "analyze-profile",
            "--component-id",
            COMPONENT_ID,
        ]
    )

    assert args.command == "analyze-profile"
    assert args.component_id == COMPONENT_ID


def test_analyze_profile_is_local_only(
    tmp_path: Path,
    capsys,
) -> None:
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
        PROFILE_XML,
        encoding="utf-8",
        newline="",
    )

    fake_paths = SimpleNamespace(
        data_root=data_root,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ), patch(
        "boomi_builder.dev_cli.build_runtime"
    ) as build_runtime:
        exit_code = dev_cli.analyze_profile_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    build_runtime.assert_not_called()

    assert "Boomi XML profile analysis" in captured.out
    assert COMPONENT_ID in captured.out
    assert "Model version      : 2" in captured.out
    assert "Strict             : True" in captured.out
    assert "Logical elements   : 2" in captured.out
    assert "XML attributes     : 1" in captured.out
    assert "Repeating elements : 1" in captured.out

    assert "ROOT" in captured.out
    assert "ROOT/ITEM | 1..999999999" in captured.out


def test_analyze_profile_does_not_print_component_xml(
    tmp_path: Path,
    capsys,
) -> None:
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
        PROFILE_XML,
        encoding="utf-8",
        newline="",
    )

    fake_paths = SimpleNamespace(
        data_root=data_root,
    )

    with patch(
        "boomi_builder.dev_cli.get_app_paths",
        return_value=fake_paths,
    ):
        exit_code = dev_cli.analyze_profile_command(
            component_id=COMPONENT_ID,
        )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert PROFILE_XML not in captured.out
    assert PROFILE_XML not in captured.err


def test_analyze_profile_rejects_missing_local_definition(
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
            dev_cli.analyze_profile_command(
                component_id=COMPONENT_ID,
            )