from __future__ import annotations

from pathlib import Path

import pytest

from boomi_builder.adapters.boomi_engine import (
    BoomiComponentDefinitionResult,
    BoomiEngineAdapter,
    BoomiEngineContractError,
    BoomiEngineExecutionError,
)
from boomi_builder.adapters.powershell_runner import ProcessResult
from boomi_builder.settings import AppPaths


COMPONENT_ID = (
    "1548d6fa-15b7-41e0-84ca-45dd46668bed"
)


VALID_COMPONENT_XML = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="{COMPONENT_ID}"
    name="SP S1 - Process MR Order to ZTE"
    type="process"
    version="7"
    currentVersion="true"
    deleted="false"
    folderFullPath="Electrohold ICT/#TestMiro/04_Subprocesses"
    branchName="main">
  <object>
    <process>
      <shapes>
        <shape
            name="shape1"
            shapetype="start" />
      </shapes>
    </process>
  </object>
</Component>
"""


class FakeRunner:
    def __init__(
        self,
        result: ProcessResult,
    ) -> None:
        self.result = result
        self.calls: list[
            tuple[
                Path,
                list[str],
                dict[str, str],
            ]
        ] = []

    def run_script(
        self,
        script_path: Path,
        arguments=(),
        environment=None,
        stdin_text=None,
    ) -> ProcessResult:
        self.calls.append(
            (
                script_path,
                list(arguments),
                dict(environment or {}),
            )
        )

        return self.result


def build_paths(
    tmp_path: Path,
) -> AppPaths:
    app_root = tmp_path / "app"
    backend_root = app_root / "backend"

    engine_root = (
        app_root
        / "engine"
        / "boomi-cli"
    )

    engine_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    boomi_cli_path = (
        engine_root
        / "boomi.ps1"
    )

    boomi_cli_path.write_text(
        "# synthetic CLI",
        encoding="utf-8",
    )

    data_root = app_root / "data"
    data_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    secrets_root = (
        data_root
        / "secrets"
    )

    dpapi_helper_path = (
        backend_root
        / "src"
        / "boomi_builder"
        / "adapters"
        / "dpapi_secret.ps1"
    )

    connections_path = (
        data_root
        / "connections.json"
    )

    return AppPaths(
        app_root=app_root,
        backend_root=backend_root,
        engine_root=engine_root,
        boomi_cli_path=boomi_cli_path,
        data_root=data_root,
        secrets_root=secrets_root,
        connections_path=connections_path,
        dpapi_helper_path=dpapi_helper_path,
    )


def test_get_component_definition_uses_safe_machine_contract(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=VALID_COMPONENT_XML,
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    environment = {
        "BOOMI_ACCOUNT_ID": "TEST_ACCOUNT",
        "BOOMI_USERNAME": "test.user@example.invalid",
        "BOOMI_API_TOKEN": "SYNTHETIC_TOKEN",
    }

    result = adapter.get_component_definition(
        workspace=paths.data_root,
        component_id=COMPONENT_ID,
        environment=environment,
    )

    assert isinstance(
        result,
        BoomiComponentDefinitionResult,
    )

    assert result.component_id == COMPONENT_ID
    assert result.name == (
        "SP S1 - Process MR Order to ZTE"
    )
    assert result.type == "process"
    assert result.version == 7
    assert result.xml == VALID_COMPONENT_XML

    assert len(runner.calls) == 1

    (
        script_path,
        arguments,
        actual_environment,
    ) = runner.calls[0]

    assert script_path == (
        paths.boomi_cli_path
    )

    assert arguments == [
        "get-definition",
        "-Workspace",
        str(paths.data_root.resolve()),
        "-Id",
        COMPONENT_ID,
        "-OutputFormat",
        "xml",
        "-RuntimeMode",
        "app-readonly",
    ]

    assert actual_environment == environment


def test_get_component_definition_rejects_engine_failure(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=1,
            stdout="",
            stderr="Synthetic engine failure.",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineExecutionError,
        match=(
            "get-definition operation failed"
        ),
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_stderr_on_success(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=VALID_COMPONENT_XML,
            stderr="Unexpected stderr.",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="wrote to stderr",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_empty_stdout(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout="",
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="empty stdout",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_invalid_xml(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout="<Component>",
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="invalid component XML",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_wrong_root(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=(
                '<?xml version="1.0"?>'
                '<NotComponent />'
            ),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="root must be Component",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_wrong_component_id(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    xml = VALID_COMPONENT_XML.replace(
        COMPONENT_ID,
        "00000000-1111-2222-3333-444444444444",
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=xml,
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="different component ID",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_missing_name(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    xml = VALID_COMPONENT_XML.replace(
        ' name="SP S1 - Process MR Order to ZTE"',
        "",
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=xml,
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="attribute 'name' is missing",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_missing_type(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    xml = VALID_COMPONENT_XML.replace(
        ' type="process"',
        "",
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=xml,
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="attribute 'type' is missing",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_invalid_version(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    xml = VALID_COMPONENT_XML.replace(
        'version="7"',
        'version="not-an-int"',
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=xml,
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="must be an integer",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_missing_object(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    xml = VALID_COMPONENT_XML.replace(
        """\
  <object>
    <process>
      <shapes>
        <shape
            name="shape1"
            shapetype="start" />
      </shapes>
    </process>
  </object>
""",
        "",
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=xml,
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="object element is missing",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )


def test_get_component_definition_rejects_empty_object(
    tmp_path: Path,
) -> None:
    paths = build_paths(
        tmp_path
    )

    xml = VALID_COMPONENT_XML.replace(
        """\
  <object>
    <process>
      <shapes>
        <shape
            name="shape1"
            shapetype="start" />
      </shapes>
    </process>
  </object>
""",
        "  <object />\n",
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=xml,
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="contains no definition",
    ):
        adapter.get_component_definition(
            workspace=paths.data_root,
            component_id=COMPONENT_ID,
            environment={},
        )