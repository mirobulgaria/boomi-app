from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from boomi_builder.settings import get_app_paths


def _run_inventory_harness(
    *,
    reported_count: int,
) -> subprocess.CompletedProcess[str]:
    paths = get_app_paths()
    read_file = paths.engine_root / "lib" / "Boomi.Read.ps1"

    script = f"""
$ErrorActionPreference = "Stop"

. "{read_file}"

$script:BaseUrl = "https://example.invalid/api/rest/v1/test-account"
$script:JsonHeaders = @{{
    "Accept" = "application/json"
    "Content-Type" = "application/json"
}}

$script:InventoryMockCallCount = 0
$script:InventoryMockUris = @()

function Invoke-RestMethod {{

    param(
        [Parameter(Mandatory=$true)]
        [string]$Method,

        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$true)]
        [hashtable]$Headers,

        [Parameter(Mandatory=$true)]
        $Body
    )

    $script:InventoryMockCallCount++
    $script:InventoryMockUris += $Uri

    if ($Method -ne "Post") {{
        throw "Unexpected HTTP method: $Method"
    }}

    $bodyText = [Text.Encoding]::UTF8.GetString(
        [byte[]]$Body
    )

    if ($script:InventoryMockCallCount -eq 1) {{

        if (
            $Uri -ne
            "$script:BaseUrl/ComponentMetadata/query"
        ) {{
            throw "Unexpected initial query URI."
        }}

        $parsedBody = $bodyText |
            ConvertFrom-Json

        if ($null -eq $parsedBody.QueryFilter) {{
            throw "Initial query has no QueryFilter."
        }}

        $queryFilterProperties = @(
            $parsedBody.QueryFilter.PSObject.Properties
        )

        if ($queryFilterProperties.Count -ne 0) {{
            throw "Initial QueryFilter is not empty."
        }}

        return [pscustomobject]@{{
            numberOfResults = {reported_count}
            queryToken = "TOKEN-1"
            result = @(
                [pscustomobject]@{{
                    type = "process"
                    deleted = $false
                }},
                [pscustomobject]@{{
                    type = "profile.xml"
                    deleted = $false
                }}
            )
        }}
    }}

    if ($script:InventoryMockCallCount -eq 2) {{

        if (
            $Uri -ne
            "$script:BaseUrl/ComponentMetadata/queryMore"
        ) {{
            throw "Unexpected first queryMore URI."
        }}

        if (
            $Headers["Content-Type"] -ne
            "text/plain; charset=utf-8"
        ) {{
            throw "Wrong queryMore Content-Type."
        }}

        if ($bodyText -ne "TOKEN-1") {{
            throw "Wrong first queryMore token."
        }}

        return [pscustomobject]@{{
            queryToken = "TOKEN-2"
            result = @(
                [pscustomobject]@{{
                    type = "process"
                    deleted = $true
                }},
                [pscustomobject]@{{
                    type = "process"
                    deleted = $false
                }}
            )
        }}
    }}

    if ($script:InventoryMockCallCount -eq 3) {{

        if (
            $Uri -ne
            "$script:BaseUrl/ComponentMetadata/queryMore"
        ) {{
            throw "Unexpected second queryMore URI."
        }}

        if (
            $Headers["Content-Type"] -ne
            "text/plain; charset=utf-8"
        ) {{
            throw "Wrong second queryMore Content-Type."
        }}

        if ($bodyText -ne "TOKEN-2") {{
            throw "Wrong second queryMore token."
        }}

        return [pscustomobject]@{{
            queryToken = ""
            result = @(
                [pscustomobject]@{{
                    type = "connector-action"
                    deleted = $false
                }}
            )
        }}
    }}

    throw "Unexpected fourth REST call."
}}

try {{

    Invoke-BoomiCapabilityInventoryProbe

    Write-Host ""
    Write-Host "===== MOCK OBSERVATION ====="
    Write-Host (
        "Mock REST calls          : " +
        $script:InventoryMockCallCount
    )

    Write-Host (
        "Observed URI count       : " +
        $script:InventoryMockUris.Count
    )

    $componentGetCalls = @(
        $script:InventoryMockUris |
            Where-Object {{
                $_ -match '/Component/'
            }}
    ).Count

    Write-Host (
        "Observed Component GET   : " +
        $componentGetCalls
    )

    if ($componentGetCalls -ne 0) {{
        throw "Component GET was observed."
    }}

    if ($script:InventoryMockCallCount -ne 3) {{
        throw "Unexpected REST call count."
    }}

    Write-Host "HARNESS RESULT            : PASS"

    exit 0
}}
catch {{

    Write-Error $_

    exit 41
}}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "capability_inventory_harness.ps1"
        script_path.write_text(
            script,
            encoding="utf-8",
        )

        return subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )


def test_capability_inventory_paginates_and_classifies() -> None:
    result = _run_inventory_harness(
        reported_count=5,
    )

    assert result.returncode == 0, (
        "Capability inventory harness failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    output = result.stdout

    assert "ComponentMetadata/query  : ACCEPTED" in output

    assert "Initial page objects     : 2" in output
    assert "Metadata objects scanned : 5" in output
    assert "Query pages              : 3" in output
    assert "queryMore calls          : 2" in output
    assert "API reported results     : 5" in output
    assert "Result count match       : PASS" in output
    assert "Pagination terminated    : PASS" in output

    assert "Process components       : 3" in output
    assert "Deleted processes        : 1" in output
    assert "Active processes         : 2" in output
    assert "Process count integrity  : PASS" in output

    assert "Component GET calls      : 0" in output
    assert "Definitions requested    : 0" in output
    assert "Mutation calls            : 0" in output

    assert "Mock REST calls          : 3" in output
    assert "Observed URI count       : 3" in output
    assert "Observed Component GET   : 0" in output
    assert "HARNESS RESULT            : PASS" in output


def test_capability_inventory_rejects_result_count_mismatch() -> None:
    result = _run_inventory_harness(
        reported_count=6,
    )

    assert result.returncode != 0

    combined = result.stdout + result.stderr

    assert "Metadata objects scanned : 5" in combined
    assert "API reported results     : 6" in combined

    normalized = "".join(
        combined.split()
    )

    assert (
        "CAPABILITYINVENTORY:"
        "Accumulatedmetadatacount5doesnotmatch"
        "API-reportedcount6."
        in normalized
    )

    assert "CAPABILITY INVENTORY : PASS" not in combined
    assert "HARNESS RESULT            : PASS" not in combined