from __future__ import annotations

import json
from pathlib import Path

import pytest

from boomi_builder.adapters.boomi_engine import (
    BoomiEngineAdapter,
    BoomiEngineContractError,
    BoomiEngineExecutionError,
)
from boomi_builder.adapters.powershell_runner import (
    ProcessResult,
)
from boomi_builder.settings import AppPaths


CORPUS_COMPONENT_ID_1 = (
    "11111111-1111-4111-8111-111111111111"
)

CORPUS_COMPONENT_ID_2 = (
    "22222222-2222-4222-8222-222222222222"
)


def _component_xml(
    component_id: str,
    name: str = "Synthetic Process",
) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Component '
        'xmlns="http://api.platform.boomi.com/" '
        f'componentId="{component_id}" '
        f'name="{name}" '
        'type="process" '
        'version="1" '
        'currentVersion="true" '
        'deleted="false">'
        "<object>"
        "<process>"
        "<shapes>"
        '<shape name="s1" shapetype="start" />'
        "</shapes>"
        "</process>"
        "</object>"
        "</Component>"
    )


def _envelope(
    definitions: list[str],
    *,
    version: object = 1,
    extra_keys: dict[str, object] | None = None,
) -> str:
    envelope: dict[str, object] = {
        "version": version,
        "definitions": definitions,
    }

    if extra_keys:
        envelope.update(extra_keys)

    return json.dumps(envelope)


class FakeRunner:
    def __init__(
        self,
        result: ProcessResult,
    ) -> None:
        self.result = result
        self.calls = []

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
    engine_root = (
        tmp_path
        / "engine"
        / "boomi-cli"
    )

    engine_root.mkdir(
        parents=True
    )

    corpus_path = (
        engine_root
        / "get-process-definition-corpus.ps1"
    )

    corpus_path.write_text(
        "# synthetic",
        encoding="utf-8",
    )

    cli_path = engine_root / "boomi.ps1"
    cli_path.write_text(
        "# synthetic",
        encoding="utf-8",
    )

    data_root = tmp_path / "data"
    data_root.mkdir()

    return AppPaths(
        app_root=tmp_path,
        backend_root=tmp_path / "backend",
        engine_root=engine_root,
        boomi_cli_path=cli_path,
        data_root=data_root,
        connections_path=(
            data_root / "connections.json"
        ),
        secrets_root=data_root / "secrets",
        dpapi_helper_path=(
            tmp_path / "dpapi.ps1"
        ),
    )


def test_get_process_definition_corpus_returns_single_definition(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    xml = _component_xml(
        CORPUS_COMPONENT_ID_1
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope([xml]),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    definitions = adapter.get_process_definition_corpus(
        workspace=paths.data_root,
        environment={},
    )

    assert isinstance(definitions, list)
    assert len(definitions) == 1
    assert definitions[0] == xml

    assert len(runner.calls) == 1

    (
        script_path,
        arguments,
        _environment,
    ) = runner.calls[0]

    assert script_path == (
        paths.engine_root
        / "get-process-definition-corpus.ps1"
    )

    assert arguments == [
        "-Workspace",
        str(paths.data_root.resolve()),
        "-RuntimeMode",
        "app-readonly",
    ]


def test_get_process_definition_corpus_returns_ten_definitions(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    definitions_in = [
        _component_xml(
            f"{i:08d}-0000-4000-8000-000000000000"
        )
        for i in range(10)
    ]

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(definitions_in),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    definitions = adapter.get_process_definition_corpus(
        workspace=paths.data_root,
        environment={},
    )

    assert len(definitions) == 10
    assert definitions == definitions_in


def test_get_process_definition_corpus_rejects_engine_failure(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=1,
            stdout="",
            stderr="synthetic engine failure",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineExecutionError,
        match="operation failed",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_stderr_on_success(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(
                [_component_xml(CORPUS_COMPONENT_ID_1)]
            ),
            stderr="unexpected stderr",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="stderr",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_empty_stdout(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout="   ",
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
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_malformed_json(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout="{not json",
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="invalid.*envelope",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_non_object_root(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout='["a", "b"]',
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="root must be an object",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_missing_version(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=json.dumps(
                {"definitions": ["x"]}
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
        match="only 'version' and 'definitions'",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_missing_definitions(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=json.dumps({"version": 1}),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="only 'version' and 'definitions'",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_unexpected_field(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(
                [_component_xml(CORPUS_COMPONENT_ID_1)],
                extra_keys={"count": 1},
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
        match="only 'version' and 'definitions'",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_bool_version(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(
                [_component_xml(CORPUS_COMPONENT_ID_1)],
                version=True,
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
        match="integer 1",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_float_version(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(
                [_component_xml(CORPUS_COMPONENT_ID_1)],
                version=1.0,
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
        match="integer 1",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_wrong_version(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(
                [_component_xml(CORPUS_COMPONENT_ID_1)],
                version=2,
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
        match="integer 1",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_definitions_not_list(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope("not-a-list"),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="must be an array",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_zero_definitions(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope([]),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="no definitions",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_over_limit(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    definitions_in = [
        _component_xml(
            f"{i:08d}-0000-4000-8000-000000000000"
        )
        for i in range(11)
    ]

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(definitions_in),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="maximum of 10",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_non_string_entry(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope([123]),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="must be strings",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_empty_entry(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(["   "]),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="must not be empty",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_malformed_xml_entry(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(["<Component>"]),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
        match="not.*valid XML",
    ):
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_rejects_wrong_root(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope(["<NotComponent />"]),
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
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )


def test_get_process_definition_corpus_preserves_utf8_and_declaration(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    cyrillic = "Тест"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Component '
        'xmlns="http://api.platform.boomi.com/" '
        f'componentId="{CORPUS_COMPONENT_ID_1}" '
        f'name="{cyrillic}" '
        'type="process" version="1">'
        "<object><process><shapes>"
        '<shape name="s1" shapetype="start" />'
        "</shapes></process></object>"
        "</Component>"
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope([xml]),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    definitions = adapter.get_process_definition_corpus(
        workspace=paths.data_root,
        environment={},
    )

    assert len(definitions) == 1
    assert definitions[0] == xml
    assert cyrillic in definitions[0]
    assert '<?xml version="1.0" encoding="UTF-8"?>' in definitions[0]
    assert 'xmlns="http://api.platform.boomi.com/"' in definitions[0]


def test_get_process_definition_corpus_preserves_quotes_backslashes_newlines(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\r\n'
        '<Component '
        'xmlns="http://api.platform.boomi.com/" '
        f'componentId="{CORPUS_COMPONENT_ID_1}" '
        'name="a &quot;b&quot; c\\d" '
        'type="process" version="1">'
        "<object><process><shapes>"
        '<shape name="s1" shapetype="start" />'
        "</shapes></process></object>"
        "</Component>"
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope([xml]),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    definitions = adapter.get_process_definition_corpus(
        workspace=paths.data_root,
        environment={},
    )

    assert len(definitions) == 1
    assert definitions[0] == xml


def test_get_process_definition_corpus_no_envelope_metadata_leakage(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    xml = _component_xml(
        CORPUS_COMPONENT_ID_1,
        name="Synthetic Only",
    )

    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope([xml]),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    definitions = adapter.get_process_definition_corpus(
        workspace=paths.data_root,
        environment={},
    )

    # The adapter returns only raw XML strings.
    # No identity/name metadata objects are exposed.
    assert all(
        isinstance(d, str) for d in definitions
    )


def test_get_process_definition_corpus_error_messages_do_not_contain_xml(
    tmp_path: Path,
) -> None:
    paths = build_paths(tmp_path)

    sensitive_marker = (
        "SYNTHETIC_PRIVATE_KEY_MUST_NOT_LEAK"
    )

    xml = _component_xml(
        CORPUS_COMPONENT_ID_1
    ).replace(
        "Synthetic Process",
        sensitive_marker,
    )

    # Malformed envelope where a valid definition precedes
    # a malformed one - failure must not leak earlier XML.
    runner = FakeRunner(
        ProcessResult(
            exit_code=0,
            stdout=_envelope([xml, "<bad>"]),
            stderr="",
        )
    )

    adapter = BoomiEngineAdapter(
        paths=paths,
        runner=runner,
    )

    with pytest.raises(
        BoomiEngineContractError,
    ) as excinfo:
        adapter.get_process_definition_corpus(
            workspace=paths.data_root,
            environment={},
        )

    assert sensitive_marker not in str(
        excinfo.value
    )
    assert CORPUS_COMPONENT_ID_1 not in str(
        excinfo.value
    )
