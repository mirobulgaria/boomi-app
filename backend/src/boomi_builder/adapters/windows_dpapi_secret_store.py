from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from boomi_builder.adapters.powershell_runner import PowerShellRunner
from boomi_builder.services.secret_store import (
    SecretNotFoundError,
    SecretReference,
    SecretStore,
)


class WindowsDpapiSecretStore(SecretStore):
    provider = "windows-dpapi"

    def __init__(
        self,
        root: Path,
        helper_script: Path,
        runner: PowerShellRunner | None = None,
    ) -> None:
        self.root = root.resolve()
        self.helper_script = helper_script.resolve()
        self.runner = runner or PowerShellRunner(timeout_seconds=10)

    def put_secret(
        self,
        value: str,
        *,
        key: str | None = None,
    ) -> SecretReference:
        if not value:
            raise ValueError("Secret value must not be empty.")

        self.root.mkdir(parents=True, exist_ok=True)

        secret_key = key or uuid4().hex
        self._validate_key(secret_key)

        path = self._path_for(secret_key)

        if path.exists():
            raise FileExistsError(
                f"Secret reference already exists: {secret_key}"
            )

        result = self.runner.run_script(
            self.helper_script,
            arguments=[
                "-Action",
                "protect",
                "-Path",
                str(path),
            ],
            stdin_text=value,
        )

        if result.exit_code != 0:
            path.unlink(missing_ok=True)
            raise RuntimeError("Failed to protect secret.")

        if result.stdout.strip() != "PROTECTED":
            path.unlink(missing_ok=True)
            raise RuntimeError(
                "Unexpected response from DPAPI protect operation."
            )

        return SecretReference(
            provider=self.provider,
            key=secret_key,
        )

    def get_secret(
        self,
        reference: SecretReference,
    ) -> str:
        self._validate_reference(reference)

        path = self._path_for(reference.key)

        if not path.is_file():
            raise SecretNotFoundError(reference.key)

        result = self.runner.run_script(
            self.helper_script,
            arguments=[
                "-Action",
                "unprotect",
                "-Path",
                str(path),
            ],
        )

        if result.exit_code != 0:
            raise RuntimeError("Failed to unprotect secret.")

        if not result.stdout:
            raise RuntimeError("Unprotected secret was empty.")

        return result.stdout

    def delete_secret(
        self,
        reference: SecretReference,
    ) -> None:
        self._validate_reference(reference)

        path = self._path_for(reference.key)

        if not path.is_file():
            raise SecretNotFoundError(reference.key)

        path.unlink()

    def exists(
        self,
        reference: SecretReference,
    ) -> bool:
        self._validate_reference(reference)
        return self._path_for(reference.key).is_file()

    def _validate_reference(
        self,
        reference: SecretReference,
    ) -> None:
        if reference.provider != self.provider:
            raise ValueError(
                f"Secret provider mismatch: {reference.provider}"
            )

        self._validate_key(reference.key)

    @staticmethod
    def _validate_key(key: str) -> None:
        if not key:
            raise ValueError("Secret key must not be empty.")

        if any(character not in "0123456789abcdef" for character in key):
            raise ValueError("Secret key must be lowercase hexadecimal.")

    def _path_for(self, key: str) -> Path:
        return self.root / f"{key}.dpapi"