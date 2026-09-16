from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from boomi_builder.settings import get_app_paths


def _run_corpus_producer_harness(
    *,
    mock_script: str,
) -> subprocess.CompletedProcess[str]:
    paths = get_app_paths()
    engine_root = paths.engine_root

    script = f"""
$ErrorActionPreference = "Stop"

$script:CliRoot = "{engine_root}"
$script:WorkspaceRoot = "{tempfile.gettempdir()}"

. "{engine_root / 'lib' / 'Boomi.Common.ps1'}"
. "{engine_root / 'lib' / 'Boomi.Read.ps1'}"
. "{engine_root / 'lib' / 'Boomi.Corpus.ps1'}"

$script:BaseUrl = "https://example.invalid/api/rest/v1/test-account"
$script:JsonHeaders = @{{
    "Authorization" = "Basic dGVzdDp0ZXN0"
    "Accept" = "application/json"
    "Content-Type" = "application/json"
}}
$script:XmlHeaders = @{{
    "Authorization" = "Basic dGVzdDp0ZXN0"
    "Accept" = "application/xml"
}}

{mock_script}
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
        return subprocess.run(
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


_METADATA_MOCK = """
$script:MetadataItems = @()

function Invoke-RestMethod {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        $Body
    )

    return [PSCustomObject]@{
        result = $script:MetadataItems
        numberOfResults = $script:MetadataItems.Count
        queryToken = $null
    }
}
"""


def _metadata_item(
    component_id: str,
    *,
    component_type: str = "process",
    deleted: bool = False,
) -> str:
    deleted_text = "true" if deleted else "false"
    return (
        "[PSCustomObject]@{ "
        f'componentId = "{component_id}"; '
        f'type = "{component_type}"; '
        f'deleted = "{deleted_text}"; '
        'name = "synthetic" '
        "}"
    )


def _component_xml_ps(
    component_id: str,
    name: str = "Synthetic",
) -> str:
    return (
        "'<?xml version=\"1.0\" encoding=\"UTF-8\"?>' + \"`n\" + "
        "'<Component xmlns=\"http://api.platform.boomi.com/\" ' + "
        f"'componentId=\"{component_id}\" name=\"{name}\" ' + "
        "'type=\"process\" version=\"1\" deleted=\"false\">' + "
        "'<object><process><shapes>' + "
        "'<shape name=\"s1\" shapetype=\"start\" />' + "
        "'</shapes></process></object></Component>'"
    )


def _webrequest_mock_for_ids(
    component_ids: list[str],
) -> str:
    cases = "\n".join(
        f"""
        "{cid}" {{
            $xml = {_component_xml_ps(cid)}
            [IO.File]::WriteAllText(
                $OutFile,
                $xml,
                [Text.Encoding]::UTF8
            )
        }}
"""
        for cid in component_ids
    )

    return f"""
function Invoke-WebRequest {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        [Parameter(Mandatory=$true)]
        [string]$OutFile,

        [switch]$UseBasicParsing
    )

    $componentId = $Uri.Substring(
        $Uri.LastIndexOf('/') + 1
    )

    switch ($componentId) {{
{cases}
        default {{
            throw "Unexpected component GET"
        }}
    }}
}}
"""


def test_producer_returns_single_definition_envelope() -> None:
    cid = "aaaaaaaa-1111-4111-8111-111111111111"

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(cid)}
)

{_webrequest_mock_for_ids([cid])}

$envelopeJson = Get-BoomiProcessDefinitionCorpus
[Console]::Out.Write($envelopeJson)
"""
    )

    assert result.returncode == 0

    envelope = json.loads(result.stdout)

    assert set(envelope.keys()) == {"version", "definitions"}
    assert envelope["version"] == 1
    assert isinstance(envelope["definitions"], list)
    assert len(envelope["definitions"]) == 1
    assert cid in envelope["definitions"][0]


def test_producer_returns_ten_definitions() -> None:
    ids = [
        f"{i:08d}-0000-4000-8000-000000000000"
        for i in range(10)
    ]

    items = "\n".join(
        f"    {_metadata_item(cid)},"
        for cid in ids
    ).rstrip(",")

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
{items}
)

{_webrequest_mock_for_ids(ids)}

$envelopeJson = Get-BoomiProcessDefinitionCorpus
[Console]::Out.Write($envelopeJson)
"""
    )

    assert result.returncode == 0

    envelope = json.loads(result.stdout)

    assert len(envelope["definitions"]) == 10
    for cid in ids:
        assert any(
            cid in d
            for d in envelope["definitions"]
        )


def test_producer_never_emits_more_than_ten() -> None:
    ids = [
        f"{i:08d}-0000-4000-8000-000000000000"
        for i in range(15)
    ]

    items = "\n".join(
        f"    {_metadata_item(cid)},"
        for cid in ids
    ).rstrip(",")

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
{items}
)

{_webrequest_mock_for_ids(ids)}

$envelopeJson = Get-BoomiProcessDefinitionCorpus
[Console]::Out.Write($envelopeJson)
"""
    )

    assert result.returncode == 0

    envelope = json.loads(result.stdout)

    assert len(envelope["definitions"]) == 10


def test_producer_selection_is_deterministic() -> None:
    ids = [
        "cccccccc-0000-4000-8000-000000000000",
        "aaaaaaaa-0000-4000-8000-000000000000",
        "bbbbbbbb-0000-4000-8000-000000000000",
    ]

    items = "\n".join(
        f"    {_metadata_item(cid)},"
        for cid in ids
    ).rstrip(",")

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
{items}
)

{_webrequest_mock_for_ids(sorted(ids))}

$envelopeJson = Get-BoomiProcessDefinitionCorpus
[Console]::Out.Write($envelopeJson)
"""
    )

    assert result.returncode == 0

    envelope = json.loads(result.stdout)

    # Deterministic order = sorted by componentId
    ordered_ids = [
        json.loads('"' + d.split('componentId=\\"')[1].split('\\"')[0] + '"')
        if False else d
        for d in envelope["definitions"]
    ]

    # Check the componentId order within the raw XML strings
    import re
    extracted = [
        re.search(
            r'componentId="([^"]+)"', d
        ).group(1)
        for d in envelope["definitions"]
    ]

    assert extracted == sorted(ids)


def test_producer_preserves_xml_declaration_and_cyrillic() -> None:
    cid = "aaaaaaaa-2222-4222-8222-222222222222"
    cyrillic_name = "".join(
        chr(c) for c in (0x0422, 0x0435, 0x0441, 0x0442)
    )

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(cid)}
)

function Invoke-WebRequest {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        [Parameter(Mandatory=$true)]
        [string]$OutFile,

        [switch]$UseBasicParsing
    )

    $name = [char]0x0422 + [char]0x0435 + [char]0x0441 + [char]0x0442
    $xml = '<?xml version="1.0" encoding="UTF-8"?>' + "`n" +
        '<Component xmlns="http://api.platform.boomi.com/" ' +
        'componentId="{cid}" name="' + $name + '" ' +
        'type="process" version="1" deleted="false">' +
        '<object><process><shapes>' +
        '<shape name="s1" shapetype="start" />' +
        '</shapes></process></object></Component>'

    [IO.File]::WriteAllText(
        $OutFile,
        $xml,
        [Text.Encoding]::UTF8
    )
}}

$envelopeJson = Get-BoomiProcessDefinitionCorpus
[Console]::Out.Write($envelopeJson)
"""
    )

    assert result.returncode == 0

    envelope = json.loads(result.stdout)

    definition = envelope["definitions"][0]
    assert '<?xml version="1.0" encoding="UTF-8"?>' in definition
    assert cyrillic_name in definition
    assert 'xmlns="http://api.platform.boomi.com/"' in definition


def test_producer_second_get_failure_emits_nothing() -> None:
    cid1 = "11111111-0000-4000-8000-000000000000"
    cid2 = "22222222-0000-4000-8000-000000000000"

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(cid1)},
    {_metadata_item(cid2)}
)

function Invoke-WebRequest {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        [Parameter(Mandatory=$true)]
        [string]$OutFile,

        [switch]$UseBasicParsing
    )

    $componentId = $Uri.Substring(
        $Uri.LastIndexOf('/') + 1
    )

    if ($componentId -eq "{cid1}") {{
        $xml = {_component_xml_ps(cid1, "SYNTHETIC_FIRST_XML_MUST_NOT_LEAK")}
        [IO.File]::WriteAllText(
            $OutFile,
            $xml,
            [Text.Encoding]::UTF8
        )
        return
    }}

    throw "Simulated GET failure"
}}

try {{
    Get-BoomiProcessDefinitionCorpus
    throw "Should have failed"
}}
catch {{
    # expected
}}
"""
    )

    assert result.returncode == 0
    assert "SYNTHETIC_FIRST_XML_MUST_NOT_LEAK" not in result.stdout
    assert not result.stdout.strip() or "version" not in result.stdout


def test_producer_middle_get_failure_emits_nothing() -> None:
    ids = [
        f"{i:08d}-0000-4000-8000-000000000000"
        for i in range(1, 6)
    ]
    fail_id = ids[2]

    items = "\n".join(
        f"    {_metadata_item(cid)},"
        for cid in ids
    ).rstrip(",")

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
{items}
)

function Invoke-WebRequest {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        [Parameter(Mandatory=$true)]
        [string]$OutFile,

        [switch]$UseBasicParsing
    )

    $componentId = $Uri.Substring(
        $Uri.LastIndexOf('/') + 1
    )

    if ($componentId -eq "{fail_id}") {{
        throw "Simulated middle GET failure"
    }}

    $xml = {_component_xml_ps('PLACEHOLDER')}
    $xml = $xml.Replace(
        'PLACEHOLDER',
        $componentId
    ).Replace(
        'Synthetic',
        'SYNTHETIC_SECOND_XML_MUST_NOT_LEAK'
    )
    [IO.File]::WriteAllText(
        $OutFile,
        $xml,
        [Text.Encoding]::UTF8
    )
}}

try {{
    Get-BoomiProcessDefinitionCorpus
    throw "Should have failed"
}}
catch {{
    # expected
}}
"""
    )

    assert result.returncode == 0
    assert "SYNTHETIC_SECOND_XML_MUST_NOT_LEAK" not in result.stdout
    assert not result.stdout.strip() or "version" not in result.stdout


def test_producer_final_get_failure_emits_nothing() -> None:
    ids = [
        f"{i:08d}-0000-4000-8000-000000000000"
        for i in range(1, 4)
    ]
    fail_id = ids[-1]

    items = "\n".join(
        f"    {_metadata_item(cid)},"
        for cid in ids
    ).rstrip(",")

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
{items}
)

function Invoke-WebRequest {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        [Parameter(Mandatory=$true)]
        [string]$OutFile,

        [switch]$UseBasicParsing
    )

    $componentId = $Uri.Substring(
        $Uri.LastIndexOf('/') + 1
    )

    if ($componentId -eq "{fail_id}") {{
        throw "Simulated final GET failure"
    }}

    $xml = {_component_xml_ps('PLACEHOLDER')}
    $xml = $xml.Replace(
        'PLACEHOLDER',
        $componentId
    )
    [IO.File]::WriteAllText(
        $OutFile,
        $xml,
        [Text.Encoding]::UTF8
    )
}}

try {{
    Get-BoomiProcessDefinitionCorpus
    throw "Should have failed"
}}
catch {{
    # expected
}}
"""
    )

    assert result.returncode == 0
    assert not result.stdout.strip()


def test_producer_component_id_mismatch_fails() -> None:
    requested = "aaaaaaaa-3333-4333-8333-333333333333"
    wrong = "bbbbbbbb-3333-4333-8333-333333333333"

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(requested)}
)

function Invoke-WebRequest {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        [Parameter(Mandatory=$true)]
        [string]$OutFile,

        [switch]$UseBasicParsing
    )

    $xml = {_component_xml_ps(wrong)}
    [IO.File]::WriteAllText(
        $OutFile,
        $xml,
        [Text.Encoding]::UTF8
    )
}}

try {{
    Get-BoomiProcessDefinitionCorpus
    throw "Should have failed"
}}
catch {{
    if ($_.Exception.Message -notmatch "mismatched") {{
        throw "Wrong error: $($_.Exception.Message)"
    }}
}}
"""
    )

    assert result.returncode == 0
    assert not result.stdout.strip()


def test_producer_malformed_component_fails() -> None:
    cid = "aaaaaaaa-4444-4444-8444-444444444444"

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(cid)}
)

function Invoke-WebRequest {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        [Parameter(Mandatory=$true)]
        [string]$OutFile,

        [switch]$UseBasicParsing
    )

    [IO.File]::WriteAllText(
        $OutFile,
        '<NotComponent />',
        [Text.Encoding]::UTF8
    )
}}

try {{
    Get-BoomiProcessDefinitionCorpus
    throw "Should have failed"
}}
catch {{
    if ($_.Exception.Message -notmatch "non-Component") {{
        throw "Wrong error: $($_.Exception.Message)"
    }}
}}
"""
    )

    assert result.returncode == 0
    assert not result.stdout.strip()


def test_producer_empty_component_fails() -> None:
    cid = "aaaaaaaa-5555-4555-8555-555555555555"

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(cid)}
)

function Invoke-WebRequest {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        [Parameter(Mandatory=$true)]
        [string]$OutFile,

        [switch]$UseBasicParsing
    )

    [IO.File]::WriteAllText($OutFile, "", [Text.Encoding]::UTF8)
}}

try {{
    Get-BoomiProcessDefinitionCorpus
    throw "Should have failed"
}}
catch {{
    if ($_.Exception.Message -notmatch "empty") {{
        throw "Wrong error: $($_.Exception.Message)"
    }}
}}
"""
    )

    assert result.returncode == 0
    assert not result.stdout.strip()


def test_producer_zero_active_processes_fails() -> None:
    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item("x", component_type="process", deleted=True)},
    {_metadata_item("y", component_type="connector")}
)

function Invoke-WebRequest {{
    throw "Should not be called"
}}

try {{
    Get-BoomiProcessDefinitionCorpus
    throw "Should have failed"
}}
catch {{
    if ($_.Exception.Message -notmatch "no active process") {{
        throw "Wrong error: $($_.Exception.Message)"
    }}
}}
"""
    )

    assert result.returncode == 0
    assert not result.stdout.strip()


def test_producer_envelope_has_no_metadata_fields() -> None:
    cid = "aaaaaaaa-6666-4666-8666-666666666666"

    result = _run_corpus_producer_harness(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(cid)}
)

{_webrequest_mock_for_ids([cid])}

$envelopeJson = Get-BoomiProcessDefinitionCorpus
[Console]::Out.Write($envelopeJson)
"""
    )

    assert result.returncode == 0

    envelope = json.loads(result.stdout)

    # Exactly two keys
    assert set(envelope.keys()) == {"version", "definitions"}

    # No metadata keys
    forbidden = {
        "count",
        "timestamp",
        "environment",
        "account",
        "componentIds",
        "names",
        "ids",
        "metadata",
        "diagnostics",
    }
    assert not (set(envelope.keys()) & forbidden)


# ============================================================
# Private entry-script failure boundary
#
# These tests exercise the REAL get-process-definition-corpus.ps1
# failure boundary. Mock transport functions are defined before
# the entry script is dot-sourced so that they shadow the real
# Invoke-RestMethod / Invoke-WebRequest cmdlets.
#
# External contract under test:
#   failure -> non-zero exit, empty stdout, one fixed generic
#              stderr diagnostic, no underlying error detail.
# ============================================================

_ENTRY_FAILURE_DIAGNOSTIC = (
    "Boomi process-definition corpus acquisition failed."
)

_SYNTHETIC_ENV = {
    "BOOMI_ACCOUNT_ID": "SYNTHETIC_ACCOUNT_MUST_NOT_LEAK",
    "BOOMI_USERNAME": "SYNTHETIC_USER_MUST_NOT_LEAK",
    "BOOMI_API_TOKEN": "SYNTHETIC_TOKEN_MUST_NOT_LEAK",
}


def _run_entry_dot_sourced(
    *,
    mock_script: str,
) -> subprocess.CompletedProcess[str]:
    paths = get_app_paths()
    entry_script = (
        paths.engine_root / "get-process-definition-corpus.ps1"
    )
    workspace = Path(tempfile.mkdtemp())

    script = f"""
$ErrorActionPreference = "Stop"

{mock_script}

. "{entry_script}" `
    -Workspace "{workspace}" `
    -RuntimeMode "app-readonly"
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
        return subprocess.run(
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
            env={**os.environ, **_SYNTHETIC_ENV},
        )
    finally:
        Path(temp_script).unlink(missing_ok=True)


def test_entry_metadata_http_failure_generic_stderr() -> None:
    result = _run_entry_dot_sourced(
        mock_script="""
function Invoke-RestMethod {
    param($Method, $Uri, $Headers, $Body)
    throw "SYNTHETIC_METADATA_BODY_MUST_NOT_LEAK"
}
"""
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == _ENTRY_FAILURE_DIAGNOSTIC
    assert "SYNTHETIC_METADATA_BODY_MUST_NOT_LEAK" not in result.stderr


def test_entry_component_get_http_failure_leaks_nothing() -> None:
    cid = "SYNTHETIC_COMPONENT_ID_MUST_NOT_LEAK"

    result = _run_entry_dot_sourced(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(cid)}
)

function Invoke-WebRequest {{
    param($Method, $Uri, $Headers, $OutFile, [switch]$UseBasicParsing)
    throw "SYNTHETIC_HTTP_BODY_MUST_NOT_LEAK"
}}
"""
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == _ENTRY_FAILURE_DIAGNOSTIC
    assert "SYNTHETIC_HTTP_BODY_MUST_NOT_LEAK" not in result.stderr
    assert cid not in result.stderr


def test_entry_mid_corpus_failure_leaks_nothing() -> None:
    cid1 = "11111111-0000-4000-8000-000000000000"
    cid2 = "22222222-0000-4000-8000-000000000000"

    result = _run_entry_dot_sourced(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(cid1)},
    {_metadata_item(cid2)}
)

function Invoke-WebRequest {{
    param($Method, $Uri, $Headers, $OutFile, [switch]$UseBasicParsing)

    $componentId = $Uri.Substring(
        $Uri.LastIndexOf('/') + 1
    )

    if ($componentId -eq "{cid1}") {{
        $xml = {_component_xml_ps(cid1, "SYNTHETIC_ACQUIRED_XML_MUST_NOT_LEAK")}
        [IO.File]::WriteAllText(
            $OutFile,
            $xml,
            [Text.Encoding]::UTF8
        )
        return
    }}

    throw "SYNTHETIC_SECOND_HTTP_BODY_MUST_NOT_LEAK"
}}
"""
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == _ENTRY_FAILURE_DIAGNOSTIC
    assert "SYNTHETIC_ACQUIRED_XML_MUST_NOT_LEAK" not in result.stderr
    assert "SYNTHETIC_SECOND_HTTP_BODY_MUST_NOT_LEAK" not in result.stderr


def test_entry_init_failure_generic_stderr(tmp_path: Path) -> None:
    entry_script = (
        get_app_paths().engine_root
        / "get-process-definition-corpus.ps1"
    )

    env = {
        **os.environ,
        "BOOMI_ACCOUNT_ID": "SYNTHETIC_ACCOUNT_MUST_NOT_LEAK",
        "BOOMI_USERNAME": "SYNTHETIC_USER_MUST_NOT_LEAK",
        "BOOMI_API_TOKEN": "",
    }

    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(entry_script),
            "-Workspace",
            str(tmp_path),
            "-RuntimeMode",
            "app-readonly",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == _ENTRY_FAILURE_DIAGNOSTIC
    assert "SYNTHETIC_ACCOUNT_MUST_NOT_LEAK" not in result.stderr
    assert "SYNTHETIC_USER_MUST_NOT_LEAK" not in result.stderr


def test_entry_success_one_envelope_empty_stderr() -> None:
    cid = "aaaaaaaa-7777-4777-8777-777777777777"

    result = _run_entry_dot_sourced(
        mock_script=f"""
{_METADATA_MOCK}

$script:MetadataItems = @(
    {_metadata_item(cid)}
)

{_webrequest_mock_for_ids([cid])}
"""
    )

    assert result.returncode == 0
    assert result.stderr == ""

    envelope = json.loads(result.stdout)

    assert set(envelope.keys()) == {"version", "definitions"}
    assert len(envelope["definitions"]) == 1
    assert cid in envelope["definitions"][0]
