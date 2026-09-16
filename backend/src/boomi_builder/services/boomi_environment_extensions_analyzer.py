from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentExtensionField:
    field_id: str
    has_value: bool
    has_component_override: bool
    has_encrypted_value_set: bool
    has_use_default: bool
    has_uses_encryption: bool


@dataclass(frozen=True)
class EnvironmentExtensionConnection:
    component_id: str
    name: str
    fields: tuple[EnvironmentExtensionField, ...]


@dataclass(frozen=True)
class EnvironmentExtensionOperation:
    component_id: str
    name: str
    fields: tuple[EnvironmentExtensionField, ...]


@dataclass(frozen=True)
class EnvironmentExtensionCrossReference:
    component_id: str
    name: str
    has_override_values: bool
    row_container_count: int


@dataclass(frozen=True)
class EnvironmentExtensionProcessPropertyValue:
    key: str
    label: str
    data_type: str
    has_value: bool
    has_encrypted_value_set: bool
    has_use_default: bool
    has_help_text: bool


@dataclass(frozen=True)
class EnvironmentExtensionProcessProperty:
    component_id: str
    name: str
    values: tuple[
        EnvironmentExtensionProcessPropertyValue,
        ...,
    ]


@dataclass(frozen=True)
class EnvironmentExtensionsAnalysis:
    root_name: str
    element_count: int
    element_counts: tuple[
        tuple[str, int],
        ...,
    ]
    connections: tuple[
        EnvironmentExtensionConnection,
        ...,
    ]
    operations: tuple[
        EnvironmentExtensionOperation,
        ...,
    ]
    cross_references: tuple[
        EnvironmentExtensionCrossReference,
        ...,
    ]
    process_properties: tuple[
        EnvironmentExtensionProcessProperty,
        ...,
    ]

    @property
    def connection_count(self) -> int:
        return len(self.connections)

    @property
    def operation_count(self) -> int:
        return len(self.operations)

    @property
    def cross_reference_count(self) -> int:
        return len(self.cross_references)

    @property
    def process_property_count(self) -> int:
        return len(self.process_properties)


class BoomiEnvironmentExtensionsAnalysisError(
    RuntimeError
):
    pass


class BoomiEnvironmentExtensionsAnalyzer:
    def analyze(
        self,
        xml_text: str,
    ) -> EnvironmentExtensionsAnalysis:
        if not xml_text.strip():
            raise BoomiEnvironmentExtensionsAnalysisError(
                "EnvironmentExtensions XML must not be empty."
            )

        try:
            root = ET.fromstring(
                xml_text
            )
        except ET.ParseError as exc:
            raise BoomiEnvironmentExtensionsAnalysisError(
                "EnvironmentExtensions XML is not well-formed."
            ) from exc

        root_name = self._local_name(
            root.tag
        )

        if root_name != "EnvironmentExtensions":
            raise BoomiEnvironmentExtensionsAnalysisError(
                "XML root must be EnvironmentExtensions."
            )

        counts = Counter(
            self._local_name(element.tag)
            for element in root.iter()
        )

        connections = tuple(
            self._parse_connection(node)
            for node in self._find_all(
                root,
                "connection",
            )
        )

        operations = tuple(
            self._parse_operation(node)
            for node in self._find_all(
                root,
                "operation",
            )
        )

        cross_references = tuple(
            self._parse_cross_reference(node)
            for node in self._find_all(
                root,
                "crossReference",
            )
        )

        process_properties = tuple(
            self._parse_process_property(node)
            for node in self._find_all(
                root,
                "ProcessProperty",
            )
        )

        return EnvironmentExtensionsAnalysis(
            root_name=root_name,
            element_count=sum(
                counts.values()
            ),
            element_counts=tuple(
                sorted(
                    counts.items()
                )
            ),
            connections=connections,
            operations=operations,
            cross_references=cross_references,
            process_properties=process_properties,
        )

    def _parse_connection(
        self,
        node: ET.Element,
    ) -> EnvironmentExtensionConnection:
        return EnvironmentExtensionConnection(
            component_id=self._attribute(
                node,
                "id",
            ),
            name=self._attribute(
                node,
                "name",
            ),
            fields=tuple(
                self._parse_field(field)
                for field in self._direct_children(
                    node,
                    "field",
                )
            ),
        )

    def _parse_operation(
        self,
        node: ET.Element,
    ) -> EnvironmentExtensionOperation:
        return EnvironmentExtensionOperation(
            component_id=self._attribute(
                node,
                "id",
            ),
            name=self._attribute(
                node,
                "name",
            ),
            fields=tuple(
                self._parse_field(field)
                for field in self._direct_children(
                    node,
                    "field",
                )
            ),
        )

    def _parse_field(
        self,
        node: ET.Element,
    ) -> EnvironmentExtensionField:
        return EnvironmentExtensionField(
            field_id=self._attribute(
                node,
                "id",
            ),
            has_value=(
                "value" in node.attrib
            ),
            has_component_override=(
                "componentOverride"
                in node.attrib
            ),
            has_encrypted_value_set=(
                "encryptedValueSet"
                in node.attrib
            ),
            has_use_default=(
                "useDefault"
                in node.attrib
            ),
            has_uses_encryption=(
                "usesEncryption"
                in node.attrib
            ),
        )

    def _parse_cross_reference(
        self,
        node: ET.Element,
    ) -> EnvironmentExtensionCrossReference:
        return EnvironmentExtensionCrossReference(
            component_id=self._attribute(
                node,
                "id",
            ),
            name=self._attribute(
                node,
                "name",
            ),
            has_override_values=(
                "overrideValues"
                in node.attrib
            ),
            row_container_count=len(
                self._direct_children(
                    node,
                    "CrossReferenceRows",
                )
            ),
        )

    def _parse_process_property(
        self,
        node: ET.Element,
    ) -> EnvironmentExtensionProcessProperty:
        return EnvironmentExtensionProcessProperty(
            component_id=self._attribute(
                node,
                "id",
            ),
            name=self._attribute(
                node,
                "name",
            ),
            values=tuple(
                self._parse_process_property_value(
                    value
                )
                for value in self._direct_children(
                    node,
                    "ProcessPropertyValue",
                )
            ),
        )

    def _parse_process_property_value(
        self,
        node: ET.Element,
    ) -> EnvironmentExtensionProcessPropertyValue:
        return EnvironmentExtensionProcessPropertyValue(
            key=self._attribute(
                node,
                "key",
            ),
            label=self._attribute(
                node,
                "label",
            ),
            data_type=self._attribute(
                node,
                "dataType",
            ),
            has_value=(
                "value" in node.attrib
            ),
            has_encrypted_value_set=(
                "encryptedValueSet"
                in node.attrib
            ),
            has_use_default=(
                "useDefault"
                in node.attrib
            ),
            has_help_text=(
                "helpText"
                in node.attrib
            ),
        )

    @staticmethod
    def _attribute(
        node: ET.Element,
        name: str,
    ) -> str:
        value = node.attrib.get(
            name,
            "",
        )

        return str(value)

    @classmethod
    def _find_all(
        cls,
        root: ET.Element,
        local_name: str,
    ) -> tuple[ET.Element, ...]:
        return tuple(
            element
            for element in root.iter()
            if cls._local_name(
                element.tag
            )
            == local_name
        )

    @classmethod
    def _direct_children(
        cls,
        node: ET.Element,
        local_name: str,
    ) -> tuple[ET.Element, ...]:
        return tuple(
            child
            for child in node
            if cls._local_name(
                child.tag
            )
            == local_name
        )

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