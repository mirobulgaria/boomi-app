from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from re import fullmatch


_UUID_PATTERN = (
    r"[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}"
)


@dataclass(frozen=True)
class ProcessConfigurationElement:
    name: str
    attributes: tuple[tuple[str, str], ...]
    text: str | None
    children: tuple[
        ProcessConfigurationElement,
        ...
    ]


@dataclass(frozen=True)
class ProcessComponentReference:
    shape_name: str
    element_name: str
    attribute_name: str
    component_id: str


@dataclass(frozen=True)
class ProcessTransition:
    source_shape: str
    target_shape: str
    dragpoint_name: str | None


@dataclass(frozen=True)
class ProcessShape:
    name: str
    shape_type: str
    user_label: str | None
    image: str | None
    x: str | None
    y: str | None
    configuration: tuple[
        ProcessConfigurationElement,
        ...
    ]
    references: tuple[
        ProcessComponentReference,
        ...
    ]

    @property
    def configuration_root_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            element.name
            for element in self.configuration
        )


@dataclass(frozen=True)
class ProcessAnalysis:
    settings: tuple[tuple[str, str], ...]
    shapes: tuple[ProcessShape, ...]
    transitions: tuple[ProcessTransition, ...]

    @property
    def shape_count(self) -> int:
        return len(self.shapes)

    @property
    def transition_count(self) -> int:
        return len(self.transitions)

    @property
    def referenced_components(
        self,
    ) -> tuple[ProcessComponentReference, ...]:
        return tuple(
            reference
            for shape in self.shapes
            for reference in shape.references
        )

    @property
    def referenced_component_ids(
        self,
    ) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []

        for reference in self.referenced_components:
            if reference.component_id in seen:
                continue

            seen.add(
                reference.component_id
            )

            result.append(
                reference.component_id
            )

        return tuple(result)


class BoomiProcessAnalysisError(RuntimeError):
    pass


class BoomiProcessAnalyzer:
    def analyze(
        self,
        xml_text: str,
    ) -> ProcessAnalysis:
        if not xml_text.strip():
            raise ValueError(
                "xml_text must not be empty."
            )

        try:
            root = ET.fromstring(
                xml_text
            )
        except ET.ParseError as exc:
            raise BoomiProcessAnalysisError(
                "Component XML is not well-formed."
            ) from exc

        if self._local_name(root.tag) != "Component":
            raise BoomiProcessAnalysisError(
                "XML root must be Component."
            )

        component_type = root.attrib.get(
            "type",
            "",
        )

        if component_type != "process":
            raise BoomiProcessAnalysisError(
                "Component type must be process."
            )

        object_node = self._find_direct_child(
            root,
            "object",
        )

        if object_node is None:
            raise BoomiProcessAnalysisError(
                "Component object element is missing."
            )

        process_node = self._find_direct_child(
            object_node,
            "process",
        )

        if process_node is None:
            raise BoomiProcessAnalysisError(
                "Process definition is missing."
            )

        settings = tuple(
            (
                str(name),
                str(value),
            )
            for name, value
            in process_node.attrib.items()
        )

        shapes_node = self._find_direct_child(
            process_node,
            "shapes",
        )

        if shapes_node is None:
            return ProcessAnalysis(
                settings=settings,
                shapes=(),
                transitions=(),
            )

        shape_nodes = tuple(
            child
            for child in shapes_node
            if self._local_name(child.tag)
            == "shape"
        )

        shapes = tuple(
            self._parse_shape(
                shape_node
            )
            for shape_node in shape_nodes
        )

        self._validate_unique_shape_names(
            shapes
        )

        transitions = self._parse_transitions(
            shape_nodes
        )

        self._validate_transition_targets(
            shapes=shapes,
            transitions=transitions,
        )

        return ProcessAnalysis(
            settings=settings,
            shapes=shapes,
            transitions=transitions,
        )

    def _parse_shape(
        self,
        shape_node: ET.Element,
    ) -> ProcessShape:
        name = self._required_attribute(
            shape_node,
            "name",
            element_type="shape",
        )

        shape_type = self._required_attribute(
            shape_node,
            "shapetype",
            element_type="shape",
        )

        configuration_node = (
            self._find_direct_child(
                shape_node,
                "configuration",
            )
        )

        configuration: tuple[
            ProcessConfigurationElement,
            ...
        ] = ()

        references: tuple[
            ProcessComponentReference,
            ...
        ] = ()

        if configuration_node is not None:
            configuration = tuple(
                self._parse_configuration_element(
                    child
                )
                for child in configuration_node
                if self._is_element(child)
            )

            references = tuple(
                self._collect_references(
                    shape_name=name,
                    configuration_node=(
                        configuration_node
                    ),
                )
            )

        return ProcessShape(
            name=name,
            shape_type=shape_type,
            user_label=self._optional_string(
                shape_node,
                "userlabel",
            ),
            image=self._optional_string(
                shape_node,
                "image",
            ),
            x=self._optional_string(
                shape_node,
                "x",
            ),
            y=self._optional_string(
                shape_node,
                "y",
            ),
            configuration=configuration,
            references=references,
        )

    def _parse_configuration_element(
        self,
        node: ET.Element,
    ) -> ProcessConfigurationElement:
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

        return ProcessConfigurationElement(
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

    def _parse_transitions(
        self,
        shape_nodes: tuple[
            ET.Element,
            ...
        ],
    ) -> tuple[ProcessTransition, ...]:
        transitions: list[
            ProcessTransition
        ] = []

        for shape_node in shape_nodes:
            source_shape = (
                self._required_attribute(
                    shape_node,
                    "name",
                    element_type="shape",
                )
            )

            dragpoints_node = (
                self._find_direct_child(
                    shape_node,
                    "dragpoints",
                )
            )

            if dragpoints_node is None:
                continue

            for dragpoint in dragpoints_node:
                if (
                    self._local_name(
                        dragpoint.tag
                    )
                    != "dragpoint"
                ):
                    continue

                target_shape = (
                    self._required_attribute(
                        dragpoint,
                        "toShape",
                        element_type="dragpoint",
                    )
                )

                transitions.append(
                    ProcessTransition(
                        source_shape=source_shape,
                        target_shape=target_shape,
                        dragpoint_name=(
                            self._optional_string(
                                dragpoint,
                                "name",
                            )
                        ),
                    )
                )

        return tuple(transitions)

    def _collect_references(
        self,
        *,
        shape_name: str,
        configuration_node: ET.Element,
    ) -> list[ProcessComponentReference]:
        references: list[
            ProcessComponentReference
        ] = []

        for element in configuration_node.iter():
            if element is configuration_node:
                continue

            for attribute_name, value in (
                element.attrib.items()
            ):
                if not fullmatch(
                    _UUID_PATTERN,
                    value,
                ):
                    continue

                references.append(
                    ProcessComponentReference(
                        shape_name=shape_name,
                        element_name=(
                            self._local_name(
                                element.tag
                            )
                        ),
                        attribute_name=(
                            str(attribute_name)
                        ),
                        component_id=str(value),
                    )
                )

        return references

    @staticmethod
    def _validate_unique_shape_names(
        shapes: tuple[ProcessShape, ...],
    ) -> None:
        seen: set[str] = set()

        for shape in shapes:
            if shape.name in seen:
                raise BoomiProcessAnalysisError(
                    "Duplicate process shape name: "
                    f"{shape.name}"
                )

            seen.add(
                shape.name
            )

    @staticmethod
    def _validate_transition_targets(
        *,
        shapes: tuple[ProcessShape, ...],
        transitions: tuple[
            ProcessTransition,
            ...
        ],
    ) -> None:
        shape_names = {
            shape.name
            for shape in shapes
        }

        for transition in transitions:
            if (
                transition.target_shape
                not in shape_names
            ):
                raise BoomiProcessAnalysisError(
                    "Process transition target "
                    "does not exist: "
                    f"{transition.source_shape} -> "
                    f"{transition.target_shape}"
                )

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
            raise BoomiProcessAnalysisError(
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