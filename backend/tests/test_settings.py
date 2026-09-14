from boomi_builder.settings import get_app_paths


def test_embedded_boomi_cli_exists() -> None:
    paths = get_app_paths()

    assert paths.backend_root == paths.app_root / "backend"
    assert paths.engine_root == (
        paths.app_root / "engine" / "boomi-cli"
    )
    assert paths.boomi_cli_path == (
        paths.engine_root / "boomi.ps1"
    )
    assert paths.boomi_cli_path.is_file()

def test_application_runtime_paths() -> None:
    paths = get_app_paths()

    assert paths.data_root == (
        paths.app_root / "data"
    )

    assert paths.secrets_root == (
        paths.data_root / "secrets"
    )

    assert paths.connections_path == (
        paths.data_root / "connections.json"
    )

    assert paths.dpapi_helper_path == (
        paths.backend_root
        / "src"
        / "boomi_builder"
        / "adapters"
        / "dpapi_secret.ps1"
    )

    assert paths.dpapi_helper_path.is_file()
