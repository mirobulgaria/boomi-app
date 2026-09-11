from boomi_builder.adapters.boomi_engine import BoomiEngineAdapter


def test_embedded_boomi_engine_is_available() -> None:
    adapter = BoomiEngineAdapter()

    status = adapter.status()

    assert status.available is True
    assert status.cli_path.name == "boomi.ps1"
    assert status.cli_path.is_file()
    assert status.engine_root.name == "boomi-cli"