from boomi_builder.settings import get_app_paths


def test_embedded_boomi_cli_exists() -> None:
    paths = get_app_paths()

    assert paths.app_root.name == "boomi-builder"
    assert paths.backend_root.name == "backend"
    assert paths.engine_root.name == "boomi-cli"

    assert paths.boomi_cli_path.name == "boomi.ps1"
    assert paths.boomi_cli_path.is_file()