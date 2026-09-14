from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from boomi_builder.adapters.boomi_engine import (
    BoomiComponentDefinitionResult,
    BoomiEngineAdapter,
    BoomiEngineContractError,
)


SUPPORTED_COMPONENT_TYPES = frozenset(
    {
        "process",
        "transform.map",
        "profile.xml",
        "connector-settings",
        "connector-action",
    }
)


@dataclass(frozen=True)
class DiscoveryComponent:
    component_id: str
    name: str
    type: str
    version: int
    definition_path: Path
    supported: bool


@dataclass(frozen=True)
class DiscoveryEdge:
    source_component_id: str
    target_component_id: str
    relation: str


@dataclass(frozen=True)
class DiscoveryResult:
    root_component_id: str
    components: tuple[DiscoveryComponent, ...]
    edges: tuple[DiscoveryEdge, ...]

    @property
    def unsupported_components(
        self,
    ) -> tuple[DiscoveryComponent, ...]:
        return tuple(
            component
            for component in self.components
            if not component.supported
        )


class BoomiDiscoveryError(RuntimeError):
    pass


class BoomiDiscoveryService:
    def __init__(
        self,
        engine: BoomiEngineAdapter,
    ) -> None:
        self.engine = engine

    def discover(
        self,
        *,
        workspace: Path,
        discovery_root: Path,
        root_component_id: str,
        environment: Mapping[str, str],
    ) -> DiscoveryResult:
        resolved_workspace = workspace.resolve()
        resolved_discovery_root = discovery_root.resolve()

        if not resolved_workspace.is_dir():
            raise ValueError(
                "Workspace directory was not found: "
                f"{resolved_workspace}"
            )

        if not root_component_id.strip():
            raise ValueError(
                "root_component_id must not be empty."
            )

        resolved_discovery_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        components: dict[str, DiscoveryComponent] = {}
        edges: list[DiscoveryEdge] = []

        pending = [root_component_id]

        while pending:
            component_id = pending.pop(0)

            if component_id in components:
                continue

            definition = (
                self.engine.get_component_definition(
                    workspace=resolved_workspace,
                    component_id=component_id,
                    environment=environment,
                )
            )

            definition_path = self._persist_definition(
                discovery_root=resolved_discovery_root,
                definition=definition,
            )

            supported = (
                definition.type
                in SUPPORTED_COMPONENT_TYPES
            )

            component = DiscoveryComponent(
                component_id=definition.component_id,
                name=definition.name,
                type=definition.type,
                version=definition.version,
                definition_path=definition_path,
                supported=supported,
            )

            components[component.component_id] = component

            if not supported:
                continue

            references = self._extract_references(
                definition
            )

            for edge in references:
                edges.append(edge)

                if (
                    edge.target_component_id
                    not in components
                    and edge.target_component_id
                    not in pending
                ):
                    pending.append(
                        edge.target_component_id
                    )

        return DiscoveryResult(
            root_component_id=root_component_id,
            components=tuple(
                components.values()
            ),
            edges=tuple(edges),
        )

    def _extract_references(
        self,
        definition: BoomiComponentDefinitionResult,
    ) -> tuple[DiscoveryEdge, ...]:
        try:
            root = ET.fromstring(
                definition.xml
            )
        except ET.ParseError as exc:
            raise BoomiDiscoveryError(
                "Validated component definition "
                "could not be parsed during discovery."
            ) from exc

        object_node = self._find_direct_child(
            root,
            "object",
        )

        if object_node is None:
            raise BoomiDiscoveryError(
                "Component object element was not found "
                "during discovery."
            )

        if definition.type == "process":
            return self._extract_process_references(
                component_id=definition.component_id,
                object_node=object_node,
            )

        if definition.type == "transform.map":
            return self._extract_map_references(
                component_id=definition.component_id,
                object_node=object_node,
            )

        if definition.type in {
            "profile.xml",
            "connector-settings",
            "connector-action",
        }:
            return ()

        return ()

    def _extract_process_references(
        self,
        *,
        component_id: str,
        object_node: ET.Element,
    ) -> tuple[DiscoveryEdge, ...]:
        process_node = self._find_direct_child(
            object_node,
            "process",
        )

        if process_node is None:
            raise BoomiDiscoveryError(
                "Process component contains no process definition."
            )

        edges: list[DiscoveryEdge] = []

        for element in process_node.iter():
            local_name = self._local_name(
                element.tag
            )

            if local_name == "map":
                self._append_reference(
                    edges=edges,
                    source_component_id=component_id,
                    target_component_id=element.attrib.get(
                        "mapId",
                        "",
                    ),
                    relation="process-map",
                )

            if local_name == "processcall":
                self._append_reference(
                    edges=edges,
                    source_component_id=component_id,
                    target_component_id=element.attrib.get(
                        "processId",
                        "",
                    ),
                    relation="process-call",
                )

            if local_name == "connectoraction":
                self._append_reference(
                    edges=edges,
                    source_component_id=component_id,
                    target_component_id=element.attrib.get(
                        "connectionId",
                        "",
                    ),
                    relation="process-connection",
                )

                self._append_reference(
                    edges=edges,
                    source_component_id=component_id,
                    target_component_id=element.attrib.get(
                        "operationId",
                        "",
                    ),
                    relation="process-operation",
                )

        return tuple(
            self._deduplicate_edges(edges)
        )

    def _extract_map_references(
        self,
        *,
        component_id: str,
        object_node: ET.Element,
    ) -> tuple[DiscoveryEdge, ...]:
        map_node = self._find_direct_child(
            object_node,
            "Map",
        )

        if map_node is None:
            raise BoomiDiscoveryError(
                "Map component contains no Map definition."
            )

        edges: list[DiscoveryEdge] = []

        self._append_reference(
            edges=edges,
            source_component_id=component_id,
            target_component_id=map_node.attrib.get(
                "fromProfile",
                "",
            ),
            relation="map-source-profile",
        )

        self._append_reference(
            edges=edges,
            source_component_id=component_id,
            target_component_id=map_node.attrib.get(
                "toProfile",
                "",
            ),
            relation="map-target-profile",
        )

        return tuple(
            self._deduplicate_edges(edges)
        )

    @staticmethod
    def _append_reference(
        *,
        edges: list[DiscoveryEdge],
        source_component_id: str,
        target_component_id: str,
        relation: str,
    ) -> None:
        if not target_component_id.strip():
            return

        edges.append(
            DiscoveryEdge(
                source_component_id=source_component_id,
                target_component_id=target_component_id,
                relation=relation,
            )
        )

    @staticmethod
    def _deduplicate_edges(
        edges: list[DiscoveryEdge],
    ) -> list[DiscoveryEdge]:
        result: list[DiscoveryEdge] = []
        seen: set[
            tuple[str, str, str]
        ] = set()

        for edge in edges:
            key = (
                edge.source_component_id,
                edge.target_component_id,
                edge.relation,
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(edge)

        return result

    @staticmethod
    def _persist_definition(
        *,
        discovery_root: Path,
        definition: BoomiComponentDefinitionResult,
    ) -> Path:
        component_root = (
            discovery_root
            / definition.component_id
        )

        component_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        definition_path = (
            component_root
            / "component.xml"
        )

        definition_path.write_text(
            definition.xml,
            encoding="utf-8",
            newline="",
        )

        return definition_path

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
    def _local_name(
        tag: str,
    ) -> str:
        if "}" in tag:
            return tag.rsplit(
                "}",
                1,
            )[1]

        return tag