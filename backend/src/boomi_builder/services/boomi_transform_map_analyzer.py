from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass(frozen=True)
class TransformMapMapping:
    from_key: str | None
    from_key_path: str | None
    from_name_path: str | None
    from_type: str | None
    to_key: str | None
    to_key_path: str | None
    to_name_path: str | None
    to_type: str | None

    @property
    def is_identity(self) -> bool:
        return (
            self.from_key == self.to_key
            and self.from_key_path == self.to_key_path
            and self.from_name_path == self.to_name_path
            and self.from_type == self.to_type
        )


@dataclass(frozen=True)
class TransformMapSection:
    present: bool
    attributes: tuple[tuple[str, str], ...]
    descendant_element_count: int


@dataclass(frozen=True)
class TransformMapAnalysis:
    source_profile_id: str
    target_profile_id: str
    mappings: tuple[TransformMapMapping, ...]
    optimize_execution_order: bool | None
    functions: TransformMapSection
    defaults: TransformMapSection
    document_cache_joins: TransformMapSection

    @property
    def source_equals_target(self) -> bool:
        return (
            self.source_profile_id
            == self.target_profile_id
        )

    @property
    def mapping_count(self) -> int:
        return len(self.mappings)

    @property
    def identity_mapping_count(self) -> int:
        return sum(
            mapping.is_identity
            for mapping in self.mappings
        )

    @property
    def all_mappings_are_identity(self) -> bool:
        return (
            bool(self.mappings)
            and self.identity_mapping_count
            == self.mapping_count
        )


class BoomiTransformMapAnalysisError(RuntimeError):
    pass


class BoomiTransformMapAnalyzer:
    def analyze(
        self,
        xml_text: str,
    ) -> TransformMapAnalysis:
        if not xml_text.strip():
            raise ValueError(
                "xml_text must not be empty."
            )

        try:
            root = ET.fromstring(
                xml_text
            )
        except ET.ParseError as exc:
            raise BoomiTransformMapAnalysisError(
                "Component XML is not well-formed."
            ) from exc

        if self._local_name(root.tag) != "Component":
            raise BoomiTransformMapAnalysisError(
                "XML root must be Component."
            )

        component_type = root.attrib.get(
            "type",
            "",
        )

        if component_type != "transform.map":
            raise BoomiTransformMapAnalysisError(
                "Component type must be transform.map."
            )

        object_node = self._find_direct_child(
            root,
            "object",
        )

        if object_node is None:
            raise BoomiTransformMapAnalysisError(
                "Component object element is missing."
            )

        map_node = self._find_direct_child(
            object_node,
            "Map",
        )

        if map_node is None:
            raise BoomiTransformMapAnalysisError(
                "Map definition is missing."
            )

        source_profile_id = self._required_attribute(
            map_node,
            "fromProfile",
            element_type="Map",
        )

        target_profile_id = self._required_attribute(
            map_node,
            "toProfile",
            element_type="Map",
        )

        mappings_node = self._find_direct_child(
            map_node,
            "Mappings",
        )

        mappings: list[TransformMapMapping] = []

        if mappings_node is not None:
            for child in mappings_node:
                if (
                    self._local_name(child.tag)
                    != "Mapping"
                ):
                    continue

                mappings.append(
                    self._parse_mapping(
                        child
                    )
                )

        functions_node = self._find_direct_child(
            map_node,
            "Functions",
        )

        defaults_node = self._find_direct_child(
            map_node,
            "Defaults",
        )

        document_cache_joins_node = (
            self._find_direct_child(
                map_node,
                "DocumentCacheJoins",
            )
        )

        optimize_execution_order = None

        if functions_node is not None:
            optimize_execution_order = (
                self._optional_bool(
                    functions_node,
                    "optimizeExecutionOrder",
                )
            )

        return TransformMapAnalysis(
            source_profile_id=source_profile_id,
            target_profile_id=target_profile_id,
            mappings=tuple(mappings),
            optimize_execution_order=(
                optimize_execution_order
            ),
            functions=self._section(
                functions_node
            ),
            defaults=self._section(
                defaults_node
            ),
            document_cache_joins=self._section(
                document_cache_joins_node
            ),
        )

    def _parse_mapping(
        self,
        node: ET.Element,
    ) -> TransformMapMapping:
        return TransformMapMapping(
            from_key=self._optional_string(
                node,
                "fromKey",
            ),
            from_key_path=self._optional_string(
                node,
                "fromKeyPath",
            ),
            from_name_path=self._optional_string(
                node,
                "fromNamePath",
            ),
            from_type=self._optional_string(
                node,
                "fromType",
            ),
            to_key=self._optional_string(
                node,
                "toKey",
            ),
            to_key_path=self._optional_string(
                node,
                "toKeyPath",
            ),
            to_name_path=self._optional_string(
                node,
                "toNamePath",
            ),
            to_type=self._optional_string(
                node,
                "toType",
            ),
        )

    @classmethod
    def _section(
        cls,
        node: ET.Element | None,
    ) -> TransformMapSection:
        if node is None:
            return TransformMapSection(
                present=False,
                attributes=(),
                descendant_element_count=0,
            )

        attributes = tuple(
            (
                str(name),
                str(value),
            )
            for name, value
            in node.attrib.items()
        )

        descendant_element_count = sum(
            1
            for descendant in node.iter()
            if descendant is not node
        )

        return TransformMapSection(
            present=True,
            attributes=attributes,
            descendant_element_count=(
                descendant_element_count
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
            raise BoomiTransformMapAnalysisError(
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

        raise BoomiTransformMapAnalysisError(
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