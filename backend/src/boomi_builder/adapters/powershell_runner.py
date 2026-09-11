from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int
    stdout: str
    stderr: str


class PowerShellExecutionError(RuntimeError):
    pass


class PowerShellRunner:
    def __init__(
        self,
        executable: str = "powershell.exe",
        timeout_seconds: int = 30,
    ) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def run_script(
        self,
        script_path: Path,
        arguments: Sequence[str] = (),
        environment: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        resolved_script = script_path.resolve()

        if not resolved_script.is_file():
            raise FileNotFoundError(
                f"PowerShell script was not found: {resolved_script}"
            )

        command = [
            self.executable,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(resolved_script),
            *arguments,
        ]

        child_environment = os.environ.copy()

        if environment is not None:
            child_environment.update(environment)

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=self.timeout_seconds,
                check=False,
                env=child_environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise PowerShellExecutionError(
                f"PowerShell execution timed out after "
                f"{self.timeout_seconds} seconds."
            ) from exc
        except UnicodeDecodeError as exc:
            raise PowerShellExecutionError(
                "PowerShell output was not valid UTF-8."
            ) from exc

        return ProcessResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )