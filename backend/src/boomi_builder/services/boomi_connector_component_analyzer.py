from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass


_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)

_SUPPORTED_COMPONENT_TYPES = {
    "connector-settings",
    "connector-action",
}


@dataclass(frozen=True)
class ConnectorConfigurationElement:
    name: str
    attributes: tuple[tuple[str, str], ...]
    text: str | None
    children: tuple[
        ConnectorConfigurationElement,
        ...
    ]


@dataclass(frozen=True)
class ConnectorField:
    id: str
    type: str | None
    value: str | None
    path: str
    configuration: tuple[
        ConnectorConfigurationElement,
        ...
    ]


@dataclass(frozen=True)
class ConnectorComponentReference:
    element_name: str
    attribute_name: str
    component_id: str
    path: str


@dataclass(frozen=True)
class ConnectorComponentAnalysis:
    component_type: str
    root_name: str
    root_attributes: tuple[tuple[str, str], ...]
    configuration: ConnectorConfigurationElement
    fields: tuple[ConnectorField, ...]
    references: tuple[
        ConnectorComponentReference,
        ...
    ]

    @property
    def field_count(self) -> int:
        return len(self.fields)

    @property
    def referenced_component_ids(
        self,
    ) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []

        for reference in self.references:
            if reference.component_id in seen:
                continue

            seen.add(
                reference.component_id
            )

            result.append(
                reference.component_id
            )

        return tuple(result)

    def find_field(
        self,
        field_id: str,
    ) -> ConnectorField | None:
        for field in self.fields:
            if field.id == field_id:
                return field

        return None


class BoomiConnectorComponentAnalysisError(
    RuntimeError
):
    pass


class BoomiConnectorComponentAnalyzer:
    def analyze(
        self,
        xml_text: str,
    ) -> ConnectorComponentAnalysis:
        if not xml_text.strip():
            raise ValueError(
                "xml_text must not be empty."
            )

        try:
            root = ET.fromstring(
                xml_text
            )
        except ET.ParseError as exc:
            raise BoomiConnectorComponentAnalysisError(
                "Component XML is not well-formed."
            ) from exc

        if self._local_name(root.tag) != "Component":
            raise BoomiConnectorComponentAnalysisError(
                "XML root must be Component."
            )

        component_type = root.attrib.get(
            "type",
            "",
        )

        if (
            component_type
            not in _SUPPORTED_COMPONENT_TYPES
        ):
            raise BoomiConnectorComponentAnalysisError(
                "Component type must be "
                "connector-settings or connector-action."
            )

        object_node = self._find_direct_child(
            root,
            "object",
        )

        if object_node is None:
            raise BoomiConnectorComponentAnalysisError(
                "Component object element is missing."
            )

        object_children = tuple(
            child
            for child in object_node
            if self._is_element(child)
        )

        if len(object_children) != 1:
            raise BoomiConnectorComponentAnalysisError(
                "Connector component object must contain "
                "exactly one root configuration element."
            )

        configuration_root = object_children[0]

        configuration = (
            self._parse_configuration_element(
                configuration_root
            )
        )

        fields = tuple(
            self._collect_fields(
                configuration_root
            )
        )

        references = tuple(
            self._collect_references(
                configuration_root
            )
        )

        return ConnectorComponentAnalysis(
            component_type=component_type,
            root_name=self._local_name(
                configuration_root.tag
            ),
            root_attributes=tuple(
                (
                    str(name),
                    str(value),
                )
                for name, value
                in configuration_root.attrib.items()
            ),
            configuration=configuration,
            fields=fields,
            references=references,
        )

    def _parse_configuration_element(
        self,
        node: ET.Element,
    ) -> ConnectorConfigurationElement:
        children = tuple(
            self._parse_configuration_element(
                child
            )
            for child in node
            if self._is_element(child)
        )

        text = (
            node.text.strip()
            if node.text
            and node.text.strip()
            else None
        )

        return ConnectorConfigurationElement(
            name=self._local_name(
                node.tag
            ),
            attributes=tuple(
                (
                    str(name),
                    str(value),
                )
                for name, value
                in node.attrib.items()
            ),
            text=text,
            children=children,
        )

    def _collect_fields(
        self,
        root: ET.Element,
    ) -> list[ConnectorField]:
        fields: list[ConnectorField] = []

        def walk(
            node: ET.Element,
            path: str,
        ) -> None:
            for child in node:
                if not self._is_element(child):
                    continue

                child_name = self._local_name(
                    child.tag
                )

                child_path = (
                    f"{path}/{child_name}"
                )

                if child_name == "field":
                    field_id = (
                        self._required_attribute(
                            child,
                            "id",
                            element_type="field",
                        )
                    )

                    field_configuration = tuple(
                        self._parse_configuration_element(
                            nested
                        )
                        for nested in child
                        if self._is_element(nested)
                    )

                    fields.append(
                        ConnectorField(
                            id=field_id,
                            type=self._optional_string(
                                child,
                                "type",
                            ),
                            value=self._optional_string(
                                child,
                                "value",
                            ),
                            path=child_path,
                            configuration=(
                                field_configuration
                            ),
                        )
                    )

                walk(
                    child,
                    child_path,
                )

        root_name = self._local_name(
            root.tag
        )

        walk(
            root,
            root_name,
        )

        return fields

    def _collect_references(
        self,
        root: ET.Element,
    ) -> list[ConnectorComponentReference]:
        references: list[
            ConnectorComponentReference
        ] = []

        def walk(
            node: ET.Element,
            path: str,
        ) -> None:
            for attribute_name, value in (
                node.attrib.items()
            ):
                if not _UUID_PATTERN.fullmatch(
                    value
                ):
                    continue

                references.append(
                    ConnectorComponentReference(
                        element_name=(
                            self._local_name(
                                node.tag
                            )
                        ),
                        attribute_name=str(
                            attribute_name
                        ),
                        component_id=str(
                            value
                        ),
                        path=path,
                    )
                )

            for child in node:
                if not self._is_element(child):
                    continue

                child_name = self._local_name(
                    child.tag
                )

                walk(
                    child,
                    f"{path}/{child_name}",
                )

        root_name = self._local_name(
            root.tag
        )

        walk(
            root,
            root_name,
        )

        return references

    @classmethod
    def _find_direct_child(
        cls,
        parent: ET.Element,
        local_name: str,
    ) -> ET.Element | None:
        for child in parent:
            if (
                cls._local_name(child.tag)
                == local_name
            ):
                return child

        return None

    @staticmethod
    def _required_attribute(
        node: ET.Element,
        name: str,
        *,
        element_type: str,
    ) -> str:
        value = node.attrib.get(
            name,
            "",
        )

        if not value:
            raise BoomiConnectorComponentAnalysisError(
                f"{element_type} attribute "
                f"'{name}' is missing."
            )

        return value

    @staticmethod
    def _optional_string(
        node: ET.Element,
        name: str,
    ) -> str | None:
        value = node.attrib.get(
            name
        )

        if value is None or value == "":
            return None

        return value

    @staticmethod
    def _is_element(
        node: ET.Element,
    ) -> bool:
        return isinstance(
            node.tag,
            str,
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