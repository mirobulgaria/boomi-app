from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from boomi_builder.adapters.boomi_engine import (
    BoomiEngineAdapter,
    BoomiEngineExecutionError,
)
from boomi_builder.adapters.powershell_runner import (
    ProcessResult,
)
from boomi_builder.services.boomi_process_analyzer import (
    BoomiProcessAnalysisError,
    BoomiProcessAnalyzer,
)
from boomi_builder.services.boomi_shape_contract_catalog_service import (
    BoomiShapeContractCatalogError,
    BoomiShapeContractCatalogService,
)
from boomi_builder.services.boomi_shape_contract_extractor import (
    BoomiShapeContractExtractor,
    ShapeContractCatalogAggregator,
    ShapeContractCatalogRenderer,
)
from boomi_builder.settings import AppPaths, get_app_paths


SENSITIVE_MARKERS = (
    "SYNTHETIC_PASSWORD_MUST_NOT_LEAK",
    "SYNTHETIC_CUSTOMER_MUST_NOT_LEAK",
    "SYNTHETIC_PRIVATE_KEY_MUST_NOT_LEAK",
    "SYNTHETIC_TOKEN_MUST_NOT_LEAK",
)

COMPONENT_ID_A = "aaaaaaaa-0000-4000-8000-000000000001"
COMPONENT_ID_B = "bbbbbbbb-0000-4000-8000-000000000002"
COMPONENT_ID_C = "cccccccc-0000-4000-8000-000000000003"

PROCESS_NAME_A = "Synthetic Process Alpha"
PROCESS_NAME_B = "Synthetic Process Beta"
PROCESS_NAME_C = "Synthetic Process Gamma"

FOLDER_A = "Synthetic Folder Alpha"
FOLDER_B = "Synthetic Folder Beta"
FOLDER_C = "Synthetic Folder Gamma"


def _component_xml(
    component_id: str,
    name: str,
    folder: str,
    shapes_xml: str,
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
        'deleted="false" '
        f'folderFullPath="{folder}">'
        "<object>"
        "<process>"
        "<shapes>"
        f"{shapes_xml}"
        "</shapes>"
        "</process>"
        "</object>"
        "</Component>"
    )


# Message structural variant V1 (shared by Process A and Process B)
_MESSAGE_V1 = (
    '<shape name="m1" shapetype="message">'
    "<configuration>"
    '<message combined="true" truncate="false" />'
    "</configuration>"
    '<dragpoints>'
    '<dragpoint toShape="NEXT" />'
    "</dragpoints>"
    "</shape>"
)

# Message structural variant V2 (different structure + markers in
# attribute values, element text and userlabel)
_MESSAGE_V2 = (
    '<shape name="m2" shapetype="message" '
    'userlabel="SYNTHETIC_CUSTOMER_MUST_NOT_LEAK">'
    "<configuration>"
    '<message combined="SYNTHETIC_PASSWORD_MUST_NOT_LEAK">'
    "<variables>"
    '<variable name="v1" type="string">'
    "SYNTHETIC_PRIVATE_KEY_MUST_NOT_LEAK"
    "</variable>"
    "</variables>"
    "</message>"
    "</configuration>"
    "</shape>"
)

_STOP = '<shape name="s1" shapetype="stop" />'

_UNKNOWN = (
    '<shape name="u1" shapetype="synthetic-unknown">'
    "<configuration>"
    '<syntheticcfg note="SYNTHETIC_TOKEN_MUST_NOT_LEAK" />'
    "</configuration>"
    "</shape>"
)

PROCESS_A_XML = _component_xml(
    COMPONENT_ID_A,
    PROCESS_NAME_A,
    FOLDER_A,
    _MESSAGE_V1.replace("NEXT", "s1") + _STOP,
)

PROCESS_B_XML = _component_xml(
    COMPONENT_ID_B,
    PROCESS_NAME_B,
    FOLDER_B,
    _MESSAGE_V1.replace("NEXT", "m2") + _MESSAGE_V2,
)

PROCESS_C_XML = _component_xml(
    COMPONENT_ID_C,
    PROCESS_NAME_C,
    FOLDER_C,
    _UNKNOWN,
)

SYNTHETIC_CORPUS = [PROCESS_A_XML, PROCESS_B_XML, PROCESS_C_XML]


class _StubEngine:
    def __init__(
        self,
        definitions: list[str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._definitions = definitions
        self._error = error
        self.calls = 0

    def get_process_definition_corpus(
        self,
        *,
        workspace,
        environment,
    ) -> list[str]:
        self.calls += 1

        if self._error is not None:
            raise self._error

        return list(self._definitions or [])


class _CountingAnalyzer:
    def __init__(
        self,
        fail_on_call: int | None = None,
    ) -> None:
        self._inner = BoomiProcessAnalyzer()
        self.calls = 0
        self._fail_on_call = fail_on_call

    def analyze(self, xml_text: str):
        self.calls += 1

        if self.calls == self._fail_on_call:
            raise BoomiProcessAnalysisError(
                "Synthetic analysis failure."
            )

        return self._inner.analyze(xml_text)


class _CountingExtractor:
    def __init__(
        self,
        fail: bool = False,
    ) -> None:
        self._inner = BoomiShapeContractExtractor()
        self.calls = 0
        self._fail = fail

    def extract(self, analysis):
        self.calls += 1

        if self._fail:
            raise RuntimeError(
                "Synthetic extraction failure."
            )

        return self._inner.extract(analysis)


class _CountingAggregator:
    def __init__(
        self,
        fail: bool = False,
    ) -> None:
        self._inner = ShapeContractCatalogAggregator()
        self.calls = 0
        self._fail = fail

    def aggregate(self, extractions):
        self.calls += 1

        if self._fail:
            raise RuntimeError(
                "Synthetic aggregation failure."
            )

        return self._inner.aggregate(extractions)


def _build_paths(tmp_path: Path) -> AppPaths:
    engine_root = tmp_path / "engine" / "boomi-cli"
    engine_root.mkdir(parents=True)

    corpus_path = (
        engine_root / "get-process-definition-corpus.ps1"
    )
    corpus_path.write_text("# synthetic", encoding="utf-8")

    cli_path = engine_root / "boomi.ps1"
    cli_path.write_text("# synthetic", encoding="utf-8")

    data_root = tmp_path / "data"
    data_root.mkdir()

    return AppPaths(
        app_root=tmp_path,
        backend_root=tmp_path / "backend",
        engine_root=engine_root,
        boomi_cli_path=cli_path,
        data_root=data_root,
        connections_path=data_root / "connections.json",
        secrets_root=data_root / "secrets",
        dpapi_helper_path=tmp_path / "dpapi.ps1",
    )


def test_build_catalog_multi_process_corpus(
    tmp_path: Path,
) -> None:
    engine = _StubEngine(definitions=SYNTHETIC_CORPUS)
    service = BoomiShapeContractCatalogService(engine)

    catalog = service.build_catalog(
        workspace=tmp_path,
        environment={},
    )

    assert catalog.process_definitions_observed == 3
    assert catalog.shapes_observed == 5

    by_type = {
        entry.shapetype: entry
        for entry in catalog.shapetypes
    }

    assert set(by_type.keys()) == {
        "message",
        "stop",
        "synthetic-unknown",
    }

    message = by_type["message"]
    assert message.instances_observed == 3
    assert len(message.variants) == 2
    assert sorted(
        v.instances_observed for v in message.variants
    ) == [1, 2]

    assert by_type["stop"].instances_observed == 1
    assert len(by_type["stop"].variants) == 1
    assert by_type["synthetic-unknown"].instances_observed == 1
    assert len(by_type["synthetic-unknown"].variants) == 1


def test_catalog_is_order_independent(
    tmp_path: Path,
) -> None:
    renderer = ShapeContractCatalogRenderer()
    catalogs = []

    for order in (
        [PROCESS_A_XML, PROCESS_B_XML, PROCESS_C_XML],
        [PROCESS_C_XML, PROCESS_B_XML, PROCESS_A_XML],
        [PROCESS_B_XML, PROCESS_A_XML, PROCESS_C_XML],
    ):
        service = BoomiShapeContractCatalogService(
            _StubEngine(definitions=order)
        )
        catalogs.append(
            service.build_catalog(
                workspace=tmp_path,
                environment={},
            )
        )

    assert catalogs[0] == catalogs[1] == catalogs[2]

    rendered = [
        renderer.render(catalog) for catalog in catalogs
    ]
    assert rendered[0] == rendered[1] == rendered[2]

    variant_ids = [
        [
            (entry.shapetype, variant.variant_id)
            for entry in catalog.shapetypes
            for variant in entry.variants
        ]
        for catalog in catalogs
    ]
    assert variant_ids[0] == variant_ids[1] == variant_ids[2]


def test_catalog_and_renderer_contain_no_sensitive_markers(
    tmp_path: Path,
) -> None:
    service = BoomiShapeContractCatalogService(
        _StubEngine(definitions=SYNTHETIC_CORPUS)
    )
    catalog = service.build_catalog(
        workspace=tmp_path,
        environment={},
    )

    rendered = ShapeContractCatalogRenderer().render(catalog)
    catalog_text = repr(catalog) + str(catalog) + rendered

    for marker in SENSITIVE_MARKERS:
        assert marker not in catalog_text

    for identity in (
        COMPONENT_ID_A,
        COMPONENT_ID_B,
        COMPONENT_ID_C,
        PROCESS_NAME_A,
        PROCESS_NAME_B,
        PROCESS_NAME_C,
        FOLDER_A,
        FOLDER_B,
        FOLDER_C,
    ):
        assert identity not in catalog_text


def test_private_envelope_to_catalog_end_to_end(
    tmp_path: Path,
) -> None:
    envelope = json.dumps(
        {
            "version": 1,
            "definitions": SYNTHETIC_CORPUS,
        }
    )

    class FakeRunner:
        def run_script(
            self,
            script_path,
            arguments=(),
            environment=None,
            stdin_text=None,
        ) -> ProcessResult:
            return ProcessResult(
                exit_code=0,
                stdout=envelope,
                stderr="",
            )

    adapter = BoomiEngineAdapter(
        paths=_build_paths(tmp_path),
        runner=FakeRunner(),
    )
    service = BoomiShapeContractCatalogService(adapter)

    catalog = service.build_catalog(
        workspace=tmp_path,
        environment={},
    )

    assert catalog.process_definitions_observed == 3
    assert catalog.shapes_observed == 5


def test_powershell_producer_to_catalog(
    tmp_path: Path,
) -> None:
    """Full chain: real PS producer -> envelope -> adapter -> catalog.

    Uses local powershell.exe with mocked transport only.
    No authentication, no Boomi contact, no real Component XML.
    """
    engine_root = get_app_paths().engine_root

    xml_by_id = {
        COMPONENT_ID_A: PROCESS_A_XML.replace("\n", " "),
        COMPONENT_ID_B: PROCESS_B_XML.replace("\n", " "),
        COMPONENT_ID_C: PROCESS_C_XML.replace("\n", " "),
    }

    ps_cases = "\n".join(
        f"        \"{cid}\" {{ $xml = '{xml}' }}"
        for cid, xml in xml_by_id.items()
    )

    ps_items = "\n".join(
        f'    [PSCustomObject]@{{ '
        f'componentId = "{cid}"; '
        f'type = "process"; '
        f'deleted = "false"; '
        f'name = "synthetic" }},'
        for cid in xml_by_id
    ).rstrip(",")

    script = f"""
$ErrorActionPreference = "Stop"

$script:CliRoot = "{engine_root}"
$script:WorkspaceRoot = "{tempfile.gettempdir()}"

. "{engine_root / 'lib' / 'Boomi.Common.ps1'}"
. "{engine_root / 'lib' / 'Boomi.Read.ps1'}"
. "{engine_root / 'lib' / 'Boomi.Corpus.ps1'}"

$script:BaseUrl = "https://example.invalid/api/rest/v1/test"
$script:JsonHeaders = @{{
    "Authorization" = "Basic dGVzdA=="
    "Accept" = "application/json"
    "Content-Type" = "application/json"
}}
$script:XmlHeaders = @{{
    "Authorization" = "Basic dGVzdA=="
    "Accept" = "application/xml"
}}

$script:MetadataItems = @(
{ps_items}
)

function Invoke-RestMethod {{
    param($Method, $Uri, $Headers, $Body)
    return [PSCustomObject]@{{
        result = $script:MetadataItems
        numberOfResults = $script:MetadataItems.Count
        queryToken = $null
    }}
}}

function Invoke-WebRequest {{
    param($Method, $Uri, $Headers, $OutFile, [switch]$UseBasicParsing)

    $componentId = $Uri.Substring(
        $Uri.LastIndexOf('/') + 1
    )

    switch ($componentId) {{
{ps_cases}
        default {{ throw "Unexpected component GET" }}
    }}

    [IO.File]::WriteAllText(
        $OutFile,
        $xml,
        [Text.Encoding]::UTF8
    )
}}

$envelopeJson = Get-BoomiProcessDefinitionCorpus
[Console]::Out.Write($envelopeJson)
"""

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".ps1",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(script)
        temp_script = f.name

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                temp_script,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    finally:
        Path(temp_script).unlink(missing_ok=True)

    assert result.returncode == 0

    class FakeRunner:
        def __init__(self, stdout: str) -> None:
            self._stdout = stdout

        def run_script(
            self,
            script_path,
            arguments=(),
            environment=None,
            stdin_text=None,
        ) -> ProcessResult:
            return ProcessResult(
                exit_code=0,
                stdout=self._stdout,
                stderr="",
            )

    adapter = BoomiEngineAdapter(
        paths=_build_paths(tmp_path),
        runner=FakeRunner(result.stdout),
    )
    service = BoomiShapeContractCatalogService(adapter)

    catalog = service.build_catalog(
        workspace=tmp_path,
        environment={},
    )

    assert catalog.process_definitions_observed == 3
    assert catalog.shapes_observed == 5

    by_type = {
        entry.shapetype: entry
        for entry in catalog.shapetypes
    }
    assert set(by_type.keys()) == {
        "message",
        "stop",
        "synthetic-unknown",
    }


def test_engine_failure_no_analyzer_calls(
    tmp_path: Path,
) -> None:
    analyzer = _CountingAnalyzer()
    engine = _StubEngine(
        error=BoomiEngineExecutionError(
            "Synthetic engine failure."
        )
    )
    service = BoomiShapeContractCatalogService(
        engine,
        process_analyzer=analyzer,
    )

    with pytest.raises(BoomiEngineExecutionError):
        service.build_catalog(
            workspace=tmp_path,
            environment={},
        )

    assert analyzer.calls == 0


def test_analyzer_failure_on_first_definition(
    tmp_path: Path,
) -> None:
    analyzer = _CountingAnalyzer(fail_on_call=1)
    extractor = _CountingExtractor()
    service = BoomiShapeContractCatalogService(
        _StubEngine(definitions=SYNTHETIC_CORPUS),
        process_analyzer=analyzer,
        extractor=extractor,
    )

    with pytest.raises(BoomiProcessAnalysisError):
        service.build_catalog(
            workspace=tmp_path,
            environment={},
        )

    assert extractor.calls == 0


def test_analyzer_failure_on_middle_definition_no_partial_catalog(
    tmp_path: Path,
) -> None:
    analyzer = _CountingAnalyzer(fail_on_call=2)
    aggregator = _CountingAggregator()
    service = BoomiShapeContractCatalogService(
        _StubEngine(definitions=SYNTHETIC_CORPUS),
        process_analyzer=analyzer,
        aggregator=aggregator,
    )

    with pytest.raises(BoomiProcessAnalysisError):
        service.build_catalog(
            workspace=tmp_path,
            environment={},
        )

    assert aggregator.calls == 0


def test_extractor_failure_no_catalog(
    tmp_path: Path,
) -> None:
    aggregator = _CountingAggregator()
    service = BoomiShapeContractCatalogService(
        _StubEngine(definitions=SYNTHETIC_CORPUS),
        extractor=_CountingExtractor(fail=True),
        aggregator=aggregator,
    )

    with pytest.raises(RuntimeError):
        service.build_catalog(
            workspace=tmp_path,
            environment={},
        )

    assert aggregator.calls == 0


def test_aggregator_failure_no_catalog(
    tmp_path: Path,
) -> None:
    service = BoomiShapeContractCatalogService(
        _StubEngine(definitions=SYNTHETIC_CORPUS),
        aggregator=_CountingAggregator(fail=True),
    )

    with pytest.raises(RuntimeError):
        service.build_catalog(
            workspace=tmp_path,
            environment={},
        )


def test_empty_corpus_fails_closed(
    tmp_path: Path,
) -> None:
    service = BoomiShapeContractCatalogService(
        _StubEngine(definitions=[])
    )

    with pytest.raises(BoomiShapeContractCatalogError):
        service.build_catalog(
            workspace=tmp_path,
            environment={},
        )


def test_service_exceptions_do_not_contain_markers(
    tmp_path: Path,
) -> None:
    malformed = (
        "<Component><object><process><shapes>"
        "<shape "
    ) + "SYNTHETIC_PASSWORD_MUST_NOT_LEAK"

    service = BoomiShapeContractCatalogService(
        _StubEngine(
            definitions=[PROCESS_A_XML, malformed]
        )
    )

    with pytest.raises(Exception) as excinfo:
        service.build_catalog(
            workspace=tmp_path,
            environment={},
        )

    for marker in SENSITIVE_MARKERS:
        assert marker not in str(excinfo.value)


def test_each_definition_processed_exactly_once(
    tmp_path: Path,
) -> None:
    analyzer = _CountingAnalyzer()
    extractor = _CountingExtractor()
    aggregator = _CountingAggregator()
    service = BoomiShapeContractCatalogService(
        _StubEngine(definitions=SYNTHETIC_CORPUS),
        process_analyzer=analyzer,
        extractor=extractor,
        aggregator=aggregator,
    )

    service.build_catalog(
        workspace=tmp_path,
        environment={},
    )

    assert analyzer.calls == 3
    assert extractor.calls == 3
    assert aggregator.calls == 1
