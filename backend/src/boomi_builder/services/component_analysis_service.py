from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Literal, TypeAlias

from boomi_builder.services.boomi_connector_component_analyzer import (
    BoomiConnectorComponentAnalyzer,
    ConnectorComponentAnalysis,
)
from boomi_builder.services.boomi_process_analyzer import (
    BoomiProcessAnalyzer,
    ProcessAnalysis,
)
from boomi_builder.services.boomi_transform_map_analyzer import (
    BoomiTransformMapAnalyzer,
    TransformMapAnalysis,
)
from boomi_builder.services.boomi_xml_profile_analyzer import (
    BoomiXmlProfileAnalyzer,
    XmlProfileAnalysis,
)


AnalysisKind: TypeAlias = Literal[
    "xml-profile",
    "transform-map",
    "process",
    "connector",
]

ComponentAnalysisResult: TypeAlias = (
    XmlProfileAnalysis
    | TransformMapAnalysis
    | ProcessAnalysis
    | ConnectorComponentAnalysis
)


@dataclass(frozen=True)
class ComponentAnalysis:
    component_type: str
    analysis_kind: AnalysisKind
    result: ComponentAnalysisResult


class UnsupportedComponentAnalysisError(
    RuntimeError
):
    pass


class ComponentAnalysisService:
    def __init__(
        self,
        *,
        xml_profile_analyzer: (
            BoomiXmlProfileAnalyzer | None
        ) = None,
        transform_map_analyzer: (
            BoomiTransformMapAnalyzer | None
        ) = None,
        process_analyzer: (
            BoomiProcessAnalyzer | None
        ) = None,
        connector_analyzer: (
            BoomiConnectorComponentAnalyzer | None
        ) = None,
    ) -> None:
        self._xml_profile_analyzer = (
            xml_profile_analyzer
            or BoomiXmlProfileAnalyzer()
        )

        self._transform_map_analyzer = (
            transform_map_analyzer
            or BoomiTransformMapAnalyzer()
        )

        self._process_analyzer = (
            process_analyzer
            or BoomiProcessAnalyzer()
        )

        self._connector_analyzer = (
            connector_analyzer
            or BoomiConnectorComponentAnalyzer()
        )

    def analyze(
        self,
        xml_text: str,
    ) -> ComponentAnalysis:
        component_type = (
            self._read_component_type(
                xml_text
            )
        )

        if component_type == "profile.xml":
            return ComponentAnalysis(
                component_type=component_type,
                analysis_kind="xml-profile",
                result=(
                    self._xml_profile_analyzer
                    .analyze(xml_text)
                ),
            )

        if component_type == "transform.map":
            return ComponentAnalysis(
                component_type=component_type,
                analysis_kind="transform-map",
                result=(
                    self._transform_map_analyzer
                    .analyze(xml_text)
                ),
            )

        if component_type == "process":
            return ComponentAnalysis(
                component_type=component_type,
                analysis_kind="process",
                result=(
                    self._process_analyzer
                    .analyze(xml_text)
                ),
            )

        if component_type in {
            "connector-settings",
            "connector-action",
        }:
            return ComponentAnalysis(
                component_type=component_type,
                analysis_kind="connector",
                result=(
                    self._connector_analyzer
                    .analyze(xml_text)
                ),
            )

        raise UnsupportedComponentAnalysisError(
            "Unsupported Boomi component type "
            f"for analysis: {component_type}"
        )

    @staticmethod
    def _read_component_type(
        xml_text: str,
    ) -> str:
        if not xml_text.strip():
            raise ValueError(
                "xml_text must not be empty."
            )

        try:
            root = ET.fromstring(
                xml_text
            )
        except ET.ParseError as exc:
            raise UnsupportedComponentAnalysisError(
                "Component XML is not well-formed."
            ) from exc

        if (
            ComponentAnalysisService
            ._local_name(root.tag)
            != "Component"
        ):
            raise UnsupportedComponentAnalysisError(
                "XML root must be Component."
            )

        component_type = root.attrib.get(
            "type",
            "",
        )

        if not component_type:
            raise UnsupportedComponentAnalysisError(
                "Component type is missing."
            )

        return component_type

    @staticmethod
    def _local_name(
        tag: str,
    ) -> str:
        if "}" in tag:
            return tag.rsplit(
                "}",
                1,
            )[1]

        return tag