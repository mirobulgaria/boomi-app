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

    parser.error(
        f"Unsupported command: {args.command}"
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())