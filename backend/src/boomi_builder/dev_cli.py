from __future__ import annotations

import argparse
from pathlib import Path

from boomi_builder.adapters.boomi_engine import (
    BoomiEngineAdapter,
)
from boomi_builder.adapters.windows_dpapi_secret_store import (
    WindowsDpapiSecretStore,
)
from boomi_builder.repositories.json_boomi_connection_repository import (
    JsonBoomiConnectionRepository,
)
from boomi_builder.services.boomi_connection_lifecycle import (
    BoomiConnectionLifecycleService,
)
from boomi_builder.services.boomi_connection_service import (
    BoomiConnectionService,
)
from boomi_builder.services.boomi_discovery_service import (
    BoomiDiscoveryService,
)
from boomi_builder.services.boomi_transform_map_analyzer import (
    BoomiTransformMapAnalyzer,
)
from boomi_builder.services.boomi_xml_profile_analyzer import (
    BoomiXmlProfileAnalyzer,
)
from boomi_builder.services.connection_enrollment import (
    ConnectionEnrollment,
)
from boomi_builder.settings import get_app_paths


def build_runtime():
    paths = get_app_paths()

    secret_store = WindowsDpapiSecretStore(
        root=paths.secrets_root,
        helper_script=paths.dpapi_helper_path,
    )

    repository = JsonBoomiConnectionRepository(
        paths.connections_path
    )

    connection_service = BoomiConnectionService(
        secret_store
    )

    lifecycle_service = BoomiConnectionLifecycleService(
        connection_service,
        repository,
    )

    engine = BoomiEngineAdapter(
        paths=paths
    )

    return (
        paths,
        secret_store,
        repository,
        connection_service,
        lifecycle_service,
        engine,
    )


def enroll_command(
    owner_user_id: str,
) -> int:
    (
        _paths,
        _secret_store,
        _repository,
        _connection_service,
        lifecycle_service,
        _engine,
    ) = build_runtime()

    enrollment = ConnectionEnrollment(
        lifecycle_service
    )

    connection = enrollment.enroll_interactively(
        owner_user_id=owner_user_id
    )

    print()
    print("Boomi connection enrolled successfully.")
    print(f"Connection ID : {connection.id}")
    print(f"Name          : {connection.name}")
    print(f"Account ID    : {connection.account_id}")
    print(f"Username      : {connection.boomi_username}")
    print(f"Status        : {connection.status.value}")

    return 0


def get_command(
    *,
    connection_id: str,
    component_id: str,
) -> int:
    (
        paths,
        _secret_store,
        repository,
        connection_service,
        _lifecycle_service,
        engine,
    ) = build_runtime()

    connection = repository.get(
        connection_id
    )

    environment = (
        connection_service.resolve_runtime_environment(
            connection
        )
    )

    component = engine.get_component(
        workspace=paths.data_root,
        component_id=component_id,
        environment=environment,
    )

    print()
    print("Boomi component")
    print("===============")
    print(f"Component ID    : {component.component_id}")
    print(f"Name            : {component.name}")
    print(f"Type            : {component.type}")
    print(f"Version         : {component.version}")
    print(f"Current Version : {component.current_version}")
    print(f"Deleted         : {component.deleted}")
    print(f"Folder          : {component.folder_full_path}")
    print(f"Branch          : {component.branch_name}")

    return 0


def definition_command(
    *,
    connection_id: str,
    component_id: str,
) -> int:
    (
        paths,
        _secret_store,
        repository,
        connection_service,
        _lifecycle_service,
        engine,
    ) = build_runtime()

    connection = repository.get(
        connection_id
    )

    environment = (
        connection_service.resolve_runtime_environment(
            connection
        )
    )

    definition = engine.get_component_definition(
        workspace=paths.data_root,
        component_id=component_id,
        environment=environment,
    )

    definition_root = (
        paths.data_root
        / "discovery"
        / definition.component_id
    )

    definition_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    definition_path = (
        definition_root
        / "component.xml"
    )

    _write_utf8_text(
        definition_path,
        definition.xml,
    )

    print()
    print("Boomi component definition downloaded.")
    print(f"Component ID : {definition.component_id}")
    print(f"Name         : {definition.name}")
    print(f"Type         : {definition.type}")
    print(f"Version      : {definition.version}")
    print(f"File         : {definition_path}")

    return 0


def discover_command(
    *,
    connection_id: str,
    root_component_id: str,
) -> int:
    (
        paths,
        _secret_store,
        repository,
        connection_service,
        _lifecycle_service,
        engine,
    ) = build_runtime()

    connection = repository.get(
        connection_id
    )

    environment = (
        connection_service.resolve_runtime_environment(
            connection
        )
    )

    discovery_root = (
        paths.data_root
        / "discovery"
    )

    discovery_service = BoomiDiscoveryService(
        engine
    )

    result = discovery_service.discover(
        workspace=paths.data_root,
        discovery_root=discovery_root,
        root_component_id=root_component_id,
        environment=environment,
    )

    print()
    print("Boomi discovery completed.")
    print("==========================")
    print(
        f"Root component : "
        f"{result.root_component_id}"
    )
    print(
        f"Components     : "
        f"{len(result.components)}"
    )
    print(
        f"References     : "
        f"{len(result.edges)}"
    )
    print(
        f"Unsupported    : "
        f"{len(result.unsupported_components)}"
    )

    print()
    print("Components")
    print("----------")

    for component in result.components:
        status = (
            "supported"
            if component.supported
            else "unsupported"
        )

        print(
            f"{component.type} | "
            f"{component.component_id} | "
            f"{component.name} | "
            f"v{component.version} | "
            f"{status}"
        )

    print()
    print("References")
    print("----------")

    for edge in result.edges:
        print(
            f"{edge.relation} | "
            f"{edge.source_component_id} -> "
            f"{edge.target_component_id}"
        )

    return 0


def analyze_profile_command(
    *,
    component_id: str,
) -> int:
    component_path = _local_component_path(
        component_id
    )

    xml_text = component_path.read_text(
        encoding="utf-8",
    )

    analysis = BoomiXmlProfileAnalyzer().analyze(
        xml_text
    )

    print()
    print("Boomi XML profile analysis")
    print("==========================")
    print(f"Component ID       : {component_id}")
    print(f"File               : {component_path}")
    print(f"Model version      : {analysis.model_version}")
    print(f"Strict             : {analysis.strict}")
    print(f"Logical elements   : {analysis.element_count}")
    print(f"XML attributes     : {analysis.attribute_count}")
    print(
        f"Repeating elements : "
        f"{len(analysis.repeating_elements)}"
    )

    print()
    print("Root paths")
    print("----------")

    for root_path in analysis.root_paths:
        print(root_path)

    print()
    print("Repeating elements")
    print("------------------")

    for element in analysis.repeating_elements:
        print(
            f"{element.path} | "
            f"{_format_occurs(element.min_occurs, element.max_occurs)}"
        )

    return 0


def analyze_map_command(
    *,
    component_id: str,
) -> int:
    component_path = _local_component_path(
        component_id
    )

    xml_text = component_path.read_text(
        encoding="utf-8",
    )

    analysis = BoomiTransformMapAnalyzer().analyze(
        xml_text
    )

    print()
    print("Boomi transform map analysis")
    print("============================")
    print(f"Component ID             : {component_id}")
    print(f"File                     : {component_path}")
    print(
        f"Source profile ID        : "
        f"{analysis.source_profile_id}"
    )
    print(
        f"Target profile ID        : "
        f"{analysis.target_profile_id}"
    )
    print(
        f"Source equals target     : "
        f"{analysis.source_equals_target}"
    )
    print(
        f"Mapping count            : "
        f"{analysis.mapping_count}"
    )
    print(
        f"Identity mapping count   : "
        f"{analysis.identity_mapping_count}"
    )
    print(
        f"All mappings identity    : "
        f"{analysis.all_mappings_are_identity}"
    )
    print(
        f"Optimize execution order : "
        f"{analysis.optimize_execution_order}"
    )

    print()
    print("Sections")
    print("--------")

    _print_map_section(
        "Functions",
        analysis.functions,
    )

    _print_map_section(
        "Defaults",
        analysis.defaults,
    )

    _print_map_section(
        "DocumentCacheJoins",
        analysis.document_cache_joins,
    )

    print()
    print("Mappings")
    print("--------")

    for index, mapping in enumerate(
        analysis.mappings,
        start=1,
    ):
        print(
            f"{index} | "
            f"{_display_optional(mapping.from_type)} | "
            f"{_display_optional(mapping.from_name_path)} "
            f"-> "
            f"{_display_optional(mapping.to_type)} | "
            f"{_display_optional(mapping.to_name_path)} | "
            f"identity={mapping.is_identity}"
        )

    return 0


def _local_component_path(
    component_id: str,
) -> Path:
    paths = get_app_paths()

    component_path = (
        paths.data_root
        / "discovery"
        / component_id
        / "component.xml"
    )

    if not component_path.is_file():
        raise FileNotFoundError(
            "Local component definition was not found: "
            f"{component_path}"
        )

    return component_path


def _print_map_section(
    name: str,
    section,
) -> None:
    print(
        f"{name:<18}: "
        f"present={section.present} "
        f"descendants="
        f"{section.descendant_element_count}"
    )


def _display_optional(
    value: str | None,
) -> str:
    if value is None:
        return "<none>"

    return value


def _format_occurs(
    min_occurs: int | None,
    max_occurs: int | None,
) -> str:
    minimum = (
        "?"
        if min_occurs is None
        else str(min_occurs)
    )

    maximum = (
        "?"
        if max_occurs is None
        else str(max_occurs)
    )

    return f"{minimum}..{maximum}"


def _write_utf8_text(
    path: Path,
    content: str,
) -> None:
    path.write_text(
        content,
        encoding="utf-8",
        newline="",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="boomi-builder-dev",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    enroll_parser = subparsers.add_parser(
        "enroll",
        help="Enroll a Boomi API connection.",
    )

    enroll_parser.add_argument(
        "--owner-user-id",
        required=True,
    )

    get_parser = subparsers.add_parser(
        "get",
        help="Read one Boomi component.",
    )

    get_parser.add_argument(
        "--connection-id",
        required=True,
    )

    get_parser.add_argument(
        "--component-id",
        required=True,
    )

    definition_parser = subparsers.add_parser(
        "definition",
        help="Download one Boomi component definition.",
    )

    definition_parser.add_argument(
        "--connection-id",
        required=True,
    )

    definition_parser.add_argument(
        "--component-id",
        required=True,
    )

    discover_parser = subparsers.add_parser(
        "discover",
        help="Discover a Boomi component dependency graph.",
    )

    discover_parser.add_argument(
        "--connection-id",
        required=True,
    )

    discover_parser.add_argument(
        "--root-component-id",
        required=True,
    )

    analyze_profile_parser = subparsers.add_parser(
        "analyze-profile",
        help="Analyze a local discovered Boomi XML profile.",
    )

    analyze_profile_parser.add_argument(
        "--component-id",
        required=True,
    )

    analyze_map_parser = subparsers.add_parser(
        "analyze-map",
        help="Analyze a local discovered Boomi transform map.",
    )

    analyze_map_parser.add_argument(
        "--component-id",
        required=True,
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "enroll":
        return enroll_command(
            owner_user_id=args.owner_user_id
        )

    if args.command == "get":
        return get_command(
            connection_id=args.connection_id,
            component_id=args.component_id,
        )

    if args.command == "definition":
        return definition_command(
            connection_id=args.connection_id,
            component_id=args.component_id,
        )

    if args.command == "discover":
        return discover_command(
            connection_id=args.connection_id,
            root_component_id=args.root_component_id,
        )

    if args.command == "analyze-profile":
        return analyze_profile_command(
            component_id=args.component_id,
        )

    if args.command == "analyze-map":
        return analyze_map_command(
            component_id=args.component_id,
        )

    parser.error(
        f"Unsupported command: {args.command}"
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())