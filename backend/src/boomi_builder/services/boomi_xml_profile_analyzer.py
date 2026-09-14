from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass(frozen=True)
class XmlProfileAttribute:
    key: str
    name: str
    data_type: str | None
    required: bool | None
    is_mappable: bool | None
    is_node: bool | None
    validate_data: bool | None
    use_namespace: str | None


@dataclass(frozen=True)
class XmlProfileElement:
    key: str
    name: str
    path: str
    parent_path: str | None
    depth: int
    data_type: str | None
    min_occurs: int | None
    max_occurs: int | None
    max_length: int | None
    comments: str | None
    looping_option: str | None
    is_mappable: bool | None
    is_node: bool | None
    validate_data: bool | None
    type_expanded: bool | None
    type_key: str | None
    type_name: str | None
    use_namespace: str | None
    attributes: tuple[XmlProfileAttribute, ...]
    child_paths: tuple[str, ...]

    @property
    def repeating(self) -> bool:
        return (
            self.max_occurs is not None
            and self.max_occurs > 1
        )


@dataclass(frozen=True)
class XmlProfileAnalysis:
    model_version: str | None
    strict: bool | None
    root_paths: tuple[str, ...]
    elements: tuple[XmlProfileElement, ...]

    @property
    def element_count(self) -> int:
        return len(self.elements)

    @property
    def attribute_count(self) -> int:
        return sum(
            len(element.attributes)
            for element in self.elements
        )

    @property
    def repeating_elements(
        self,
    ) -> tuple[XmlProfileElement, ...]:
        return tuple(
            element
            for element in self.elements
            if element.repeating
        )

    def find_by_path(
        self,
        path: str,
    ) -> XmlProfileElement | None:
        for element in self.elements:
            if element.path == path:
                return element

        return None

    def find_by_name(
        self,
        name: str,
    ) -> tuple[XmlProfileElement, ...]:
        return tuple(
            element
            for element in self.elements
            if element.name == name
        )


class BoomiXmlProfileAnalysisError(RuntimeError):
    pass


class BoomiXmlProfileAnalyzer:
    def analyze(
        self,
        xml_text: str,
    ) -> XmlProfileAnalysis:
        if not xml_text.strip():
            raise ValueError(
                "xml_text must not be empty."
            )

        try:
            root = ET.fromstring(
                xml_text
            )
        except ET.ParseError as exc:
            raise BoomiXmlProfileAnalysisError(
                "Component XML is not well-formed."
            ) from exc

        if self._local_name(root.tag) != "Component":
            raise BoomiXmlProfileAnalysisError(
                "XML root must be Component."
            )

        component_type = root.attrib.get(
            "type",
            "",
        )

        if component_type != "profile.xml":
            raise BoomiXmlProfileAnalysisError(
                "Component type must be profile.xml."
            )

        object_node = self._find_direct_child(
            root,
            "object",
        )

        if object_node is None:
            raise BoomiXmlProfileAnalysisError(
                "Component object element is missing."
            )

        profile_node = self._find_direct_child(
            object_node,
            "XMLProfile",
        )

        if profile_node is None:
            raise BoomiXmlProfileAnalysisError(
                "XMLProfile definition is missing."
            )

        data_elements = self._find_direct_child(
            profile_node,
            "DataElements",
        )

        if data_elements is None:
            raise BoomiXmlProfileAnalysisError(
                "XMLProfile DataElements is missing."
            )

        root_nodes = tuple(
            child
            for child in data_elements
            if self._local_name(child.tag)
            == "XMLElement"
        )

        if not root_nodes:
            raise BoomiXmlProfileAnalysisError(
                "XMLProfile contains no root XMLElement."
            )

        elements: list[XmlProfileElement] = []
        root_paths: list[str] = []

        for root_node in root_nodes:
            root_name = self._required_attribute(
                root_node,
                "name",
                element_type="XMLElement",
            )

            root_path = root_name
            root_paths.append(
                root_path
            )

            self._walk_element(
                node=root_node,
                path=root_path,
                parent_path=None,
                depth=0,
                elements=elements,
            )

        return XmlProfileAnalysis(
            model_version=self._optional_string(
                profile_node,
                "modelVersion",
            ),
            strict=self._optional_bool(
                profile_node,
                "strict",
            ),
            root_paths=tuple(root_paths),
            elements=tuple(elements),
        )

    def _walk_element(
        self,
        *,
        node: ET.Element,
        path: str,
        parent_path: str | None,
        depth: int,
        elements: list[XmlProfileElement],
    ) -> None:
        key = self._required_attribute(
            node,
            "key",
            element_type="XMLElement",
        )

        name = self._required_attribute(
            node,
            "name",
            element_type="XMLElement",
        )

        child_element_nodes = tuple(
            child
            for child in node
            if self._local_name(child.tag)
            == "XMLElement"
        )

        child_paths_list: list[str] = []
        
        for child in child_element_nodes:
            child_name = self._required_attribute(
                child,
                "name",
                element_type="XMLElement",
            )
        
            child_paths_list.append(
                f"{path}/{child_name}"
            )
        
        child_paths = tuple(
            child_paths_list
        )

        xml_attributes = tuple(
            self._parse_xml_attribute(
                child
            )
            for child in node
            if self._local_name(child.tag)
            == "XMLAttribute"
        )

        element = XmlProfileElement(
            key=key,
            name=name,
            path=path,
            parent_path=parent_path,
            depth=depth,
            data_type=self._optional_string(
                node,
                "dataType",
            ),
            min_occurs=self._optional_int(
                node,
                "minOccurs",
            ),
            max_occurs=self._optional_int(
                node,
                "maxOccurs",
            ),
            max_length=self._optional_int(
                node,
                "maxLength",
            ),
            comments=self._optional_string(
                node,
                "comments",
            ),
            looping_option=self._optional_string(
                node,
                "loopingOption",
            ),
            is_mappable=self._optional_bool(
                node,
                "isMappable",
            ),
            is_node=self._optional_bool(
                node,
                "isNode",
            ),
            validate_data=self._optional_bool(
                node,
                "validateData",
            ),
            type_expanded=self._optional_bool(
                node,
                "typeExpanded",
            ),
            type_key=self._optional_string(
                node,
                "typeKey",
            ),
            type_name=self._optional_string(
                node,
                "typeName",
            ),
            use_namespace=self._optional_string(
                node,
                "useNamespace",
            ),
            attributes=xml_attributes,
            child_paths=child_paths,
        )

        elements.append(
            element
        )

        for child_node, child_path in zip(
            child_element_nodes,
            child_paths,
            strict=True,
        ):
            self._walk_element(
                node=child_node,
                path=child_path,
                parent_path=path,
                depth=depth + 1,
                elements=elements,
            )

    def _parse_xml_attribute(
        self,
        node: ET.Element,
    ) -> XmlProfileAttribute:
        return XmlProfileAttribute(
            key=self._required_attribute(
                node,
                "key",
                element_type="XMLAttribute",
            ),
            name=self._required_attribute(
                node,
                "name",
                element_type="XMLAttribute",
            ),
            data_type=self._optional_string(
                node,
                "dataType",
            ),
            required=self._optional_bool(
                node,
                "required",
            ),
            is_mappable=self._optional_bool(
                node,
                "isMappable",
            ),
            is_node=self._optional_bool(
                node,
                "isNode",
            ),
            validate_data=self._optional_bool(
                node,
                "validateData",
            ),
            use_namespace=self._optional_string(
                node,
                "useNamespace",
            ),
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
            raise BoomiXmlProfileAnalysisError(
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

    @classmethod
    def _optional_int(
        cls,
        node: ET.Element,
        name: str,
    ) -> int | None:
        value = cls._optional_string(
            node,
            name,
        )

        if value is None:
            return None

        try:
            return int(value)
        except ValueError as exc:
            raise BoomiXmlProfileAnalysisError(
                f"Attribute '{name}' must be an integer."
            ) from exc

    @classmethod
    def _optional_bool(
        cls,
        node: ET.Element,
        name: str,
    ) -> bool | None:
        value = cls._optional_string(
            node,
            name,
        )

        if value is None:
            return None

        normalized = value.lower()

        if normalized == "true":
            return True

        if normalized == "false":
            return False

        raise BoomiXmlProfileAnalysisError(
            f"Attribute '{name}' must be true or false."
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