from pathlib import Path

import pytest

from boomi_builder.adapters.windows_dpapi_secret_store import (
    WindowsDpapiSecretStore,
)
from boomi_builder.services.secret_store import SecretNotFoundError


def test_windows_dpapi_secret_round_trip(
    tmp_path: Path,
) -> None:
    helper = (
        Path(__file__).parents[1]
        / "src"
        / "boomi_builder"
        / "adapters"
        / "dpapi_secret.ps1"
    )

    root = tmp_path / "secrets"

    store = WindowsDpapiSecretStore(
        root=root,
        helper_script=helper,
    )

    synthetic_secret = (
        "SYNTHETIC_DPAPI_SECRET_"
        "Български_"
        "123456789"
    )

    reference = store.put_secret(synthetic_secret)

    assert reference.provider == "windows-dpapi"
    assert reference.key
    assert store.exists(reference) is True

    protected_path = root / f"{reference.key}.dpapi"

    assert protected_path.is_file()

    protected_content = protected_path.read_text(
        encoding="utf-8"
    )

    assert synthetic_secret not in protected_content

    recovered = store.get_secret(reference)

    assert recovered == synthetic_secret

    store.delete_secret(reference)

    assert store.exists(reference) is False

    with pytest.raises(SecretNotFoundError):
        store.get_secret(reference)


def test_windows_dpapi_rejects_invalid_key(
    tmp_path: Path,
) -> None:
    helper = (
        Path(__file__).parents[1]
        / "src"
        / "boomi_builder"
        / "adapters"
        / "dpapi_secret.ps1"
    )

    store = WindowsDpapiSecretStore(
        root=tmp_path / "secrets",
        helper_script=helper,
    )

    with pytest.raises(ValueError):
        store.put_secret(
            "synthetic",
            key="../escape",
        )