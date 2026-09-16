from __future__ import annotations

from dataclasses import dataclass

import pytest

from boomi_builder.services.component_analysis_service import (
    ComponentAnalysisService,
    UnsupportedComponentAnalysisError,
)


@dataclass(frozen=True)
class SyntheticAnalysis:
    analyzer: str


class RecordingAnalyzer:
    def __init__(
        self,
        name: str,
    ) -> None:
        self.name = name
        self.calls: list[str] = []

    def analyze(
        self,
        xml_text: str,
    ) -> SyntheticAnalysis:
        self.calls.append(
            xml_text
        )

        return SyntheticAnalysis(
            analyzer=self.name
        )


def component_xml(
    component_type: str,
) -> str:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    name="Synthetic Component"
    type="{component_type}"
    version="1">
  <object />
</Component>
"""


def build_service():
    profile = RecordingAnalyzer(
        "profile"
    )

    transform_map = RecordingAnalyzer(
        "map"
    )

    process = RecordingAnalyzer(
        "process"
    )

    connector = RecordingAnalyzer(
        "connector"
    )

    service = ComponentAnalysisService(
        xml_profile_analyzer=profile,
        transform_map_analyzer=transform_map,
        process_analyzer=process,
        connector_analyzer=connector,
    )

    return (
        service,
        profile,
        transform_map,
        process,
        connector,
    )


def test_dispatches_xml_profile() -> None:
    (
        service,
        profile,
        transform_map,
        process,
        connector,
    ) = build_service()

    xml_text = component_xml(
        "profile.xml"
    )

    result = service.analyze(
        xml_text
    )

    assert (
        result.component_type
        == "profile.xml"
    )

    assert (
        result.analysis_kind
        == "xml-profile"
    )

    assert result.result == (
        SyntheticAnalysis(
            analyzer="profile"
        )
    )

    assert profile.calls == [
        xml_text
    ]

    assert transform_map.calls == []
    assert process.calls == []
    assert connector.calls == []


def test_dispatches_transform_map() -> None:
    (
        service,
        profile,
        transform_map,
        process,
        connector,
    ) = build_service()

    xml_text = component_xml(
        "transform.map"
    )

    result = service.analyze(
        xml_text
    )

    assert (
        result.component_type
        == "transform.map"
    )

    assert (
        result.analysis_kind
        == "transform-map"
    )

    assert result.result == (
        SyntheticAnalysis(
            analyzer="map"
        )
    )

    assert profile.calls == []

    assert transform_map.calls == [
        xml_text
    ]

    assert process.calls == []
    assert connector.calls == []


def test_dispatches_process() -> None:
    (
        service,
        profile,
        transform_map,
        process,
        connector,
    ) = build_service()

    xml_text = component_xml(
        "process"
    )

    result = service.analyze(
        xml_text
    )

    assert (
        result.component_type
        == "process"
    )

    assert (
        result.analysis_kind
        == "process"
    )

    assert result.result == (
        SyntheticAnalysis(
            analyzer="process"
        )
    )

    assert profile.calls == []
    assert transform_map.calls == []

    assert process.calls == [
        xml_text
    ]

    assert connector.calls == []


@pytest.mark.parametrize(
    "component_type",
    [
        "connector-settings",
        "connector-action",
    ],
)
def test_dispatches_connector_components(
    component_type: str,
) -> None:
    (
        service,
        profile,
        transform_map,
        process,
        connector,
    ) = build_service()

    xml_text = component_xml(
        component_type
    )

    result = service.analyze(
        xml_text
    )

    assert (
        result.component_type
        == component_type
    )

    assert (
        result.analysis_kind
        == "connector"
    )

    assert result.result == (
        SyntheticAnalysis(
            analyzer="connector"
        )
    )

    assert profile.calls == []
    assert transform_map.calls == []
    assert process.calls == []

    assert connector.calls == [
        xml_text
    ]


def test_unsupported_component_type_fails_closed() -> None:
    (
        service,
        profile,
        transform_map,
        process,
        connector,
    ) = build_service()

    xml_text = component_xml(
        "future.component"
    )

    with pytest.raises(
        UnsupportedComponentAnalysisError,
        match=(
            "Unsupported Boomi component type "
            "for analysis: future.component"
        ),
    ):
        service.analyze(
            xml_text
        )

    assert profile.calls == []
    assert transform_map.calls == []
    assert process.calls == []
    assert connector.calls == []


def test_empty_input_is_rejected() -> None:
    service = ComponentAnalysisService()

    with pytest.raises(
        ValueError,
        match="xml_text must not be empty",
    ):
        service.analyze(
            ""
        )


def test_invalid_xml_is_rejected_before_dispatch() -> None:
    (
        service,
        profile,
        transform_map,
        process,
        connector,
    ) = build_service()

    with pytest.raises(
        UnsupportedComponentAnalysisError,
        match="not well-formed",
    ):
        service.analyze(
            "<Component>"
        )

    assert profile.calls == []
    assert transform_map.calls == []
    assert process.calls == []
    assert connector.calls == []


def test_non_component_root_is_rejected() -> None:
    (
        service,
        profile,
        transform_map,
        process,
        connector,
    ) = build_service()

    xml_text = """\
<SomethingElse type="process" />
"""

    with pytest.raises(
        UnsupportedComponentAnalysisError,
        match="XML root must be Component",
    ):
        service.analyze(
            xml_text
        )

    assert profile.calls == []
    assert transform_map.calls == []
    assert process.calls == []
    assert connector.calls == []


def test_missing_component_type_is_rejected() -> None:
    (
        service,
        profile,
        transform_map,
        process,
        connector,
    ) = build_service()

    xml_text = """\
<Component
    xmlns="http://api.platform.boomi.com/">
  <object />
</Component>
"""

    with pytest.raises(
        UnsupportedComponentAnalysisError,
        match="Component type is missing",
    ):
        service.analyze(
            xml_text
        )

    assert profile.calls == []
    assert transform_map.calls == []
    assert process.calls == []
    assert connector.calls == []


def test_default_analyzers_are_constructible() -> None:
    service = ComponentAnalysisService()

    assert service is not None