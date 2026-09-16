from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from boomi_builder.settings import get_app_paths


def _run_component_xml_helper_harness(
    *,
    mock_script: str,
) -> subprocess.CompletedProcess[str]:
    paths = get_app_paths()
    common_file = paths.engine_root / "lib" / "Boomi.Common.ps1"

    script = f"""
$ErrorActionPreference = "Stop"

# Initialize CLI roots (required by Boomi.Common.ps1)
$script:CliRoot = "{paths.engine_root}"
$script:WorkspaceRoot = "{tempfile.gettempdir()}"

$script:BaseUrl = "https://example.invalid/api/rest/v1/test-account"
$script:XmlHeaders = @{{
    "Authorization" = "Basic dGVzdDp0ZXN0"
    "Accept" = "application/xml"
}}

. "{common_file}"

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
            ["powershell", "-NoProfile", "-File", temp_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    finally:
        Path(temp_script).unlink(missing_ok=True)


def test_get_boomi_component_xml_removes_temp_file_on_success() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
$script:TempFileCreated = $false
$script:TempFilePath = $null
$script:TempFileRemoved = $false

function Invoke-WebRequest {
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

    $script:TempFileCreated = $true
    $script:TempFilePath = $OutFile

    # Create synthetic XML file
    $syntheticXml = '<?xml version="1.0" encoding="UTF-8"?><Component id="test-component"><name>Test</name></Component>'
    [IO.File]::WriteAllText($OutFile, $syntheticXml, [Text.Encoding]::UTF8)
}

# Execute the function
$result = Get-BoomiComponentXml -ComponentId "test-component-id"

# Verify temp file was created during execution
if (-not $script:TempFileCreated) {
    throw "Temp file was not created"
}

# Verify temp file was removed after function returns
if (Test-Path -LiteralPath $script:TempFilePath) {
    throw "Temp file still exists after function returns"
}

Write-Output "SUCCESS: Temp file removed"
"""
    )

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: Temp file removed" in result.stdout


def test_get_boomi_component_xml_preserves_utf8_content() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
$script:TempFileCreated = $false

function Invoke-WebRequest {
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

    $script:TempFileCreated = $true

    # Create XML with non-ASCII characters (use character codes for encoding safety)
    $testString = [char]0x0422 + [char]0x0435 + [char]0x0441 + [char]0x0442 + " UTF8 Test"
    $syntheticXml = '<?xml version="1.0" encoding="UTF-8"?><Component><name>' + $testString + '</name></Component>'
    [IO.File]::WriteAllText($OutFile, $syntheticXml, [Text.Encoding]::UTF8)
}

$result = Get-BoomiComponentXml -ComponentId "test-component-id"

# Verify UTF-8 content preserved
$expectedString = [char]0x0422 + [char]0x0435 + [char]0x0441 + [char]0x0442 + " UTF8 Test"
if (-not $result.Content.Contains($expectedString)) {
    throw "UTF-8 content not preserved correctly"
}

Write-Output "SUCCESS: UTF-8 preserved"
"""
    )

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: UTF-8 preserved" in result.stdout


def test_get_boomi_component_xml_removes_bom() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
function Invoke-WebRequest {
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

    # Create XML with UTF-8 BOM
    $syntheticXml = '<?xml version="1.0" encoding="UTF-8"?><Component><name>BOM Test</name></Component>'
    $utf8 = New-Object System.Text.UTF8Encoding $true
    $bytes = $utf8.GetBytes($syntheticXml)
    [IO.File]::WriteAllBytes($OutFile, $bytes)
}

$result = Get-BoomiComponentXml -ComponentId "test-component-id"

# Verify BOM removed (first char should not be U+FEFF)
if ($result.Content.Length -gt 0 -and [int][char]$result.Content[0] -eq 0xFEFF) {
    throw "BOM was not removed from content"
}

Write-Output "SUCCESS: BOM removed"
"""
    )

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: BOM removed" in result.stdout


def test_get_boomi_component_xml_returns_bytes_property() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
function Invoke-WebRequest {
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

    $syntheticXml = '<?xml version="1.0" encoding="UTF-8"?><Component><name>Bytes Test</name></Component>'
    [IO.File]::WriteAllText($OutFile, $syntheticXml, [Text.Encoding]::UTF8)
}

$result = Get-BoomiComponentXml -ComponentId "test-component-id"

# Verify Bytes property exists and contains data
if ($null -eq $result.Bytes) {
    throw "Bytes property is null"
}

if ($result.Bytes.Length -eq 0) {
    throw "Bytes property is empty"
}

Write-Output "SUCCESS: Bytes property available"
"""
    )

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: Bytes property available" in result.stdout


def test_get_boomi_component_xml_removes_temp_file_on_http_failure() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
$script:TempFilePath = $null

function Invoke-WebRequest {
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

    $script:TempFilePath = $OutFile

    # Simulate HTTP failure by throwing
    throw "Simulated HTTP failure"
}

try {
    $result = Get-BoomiComponentXml -ComponentId "test-component-id"
    throw "Should have thrown HTTP error"
}
catch {
    # Expected HTTP error
    if ($_.Exception.Message -notlike "*HTTP*") {
        throw "Wrong error message: $($_.Exception.Message)"
    }
}

# Verify temp file was removed even after HTTP failure
if (Test-Path -LiteralPath $script:TempFilePath) {
    throw "Temp file still exists after HTTP failure"
}

Write-Output "SUCCESS: Cleanup after HTTP failure"
"""
    )

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: Cleanup after HTTP failure" in result.stdout


def test_get_boomi_component_xml_removes_temp_file_on_empty_response() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
$script:TempFilePath = $null

function Invoke-WebRequest {
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

    $script:TempFilePath = $OutFile

    # Create empty file (simulate empty response)
    [IO.File]::WriteAllText($OutFile, "")
}

try {
    $result = Get-BoomiComponentXml -ComponentId "test-component-id"
    throw "Should have thrown empty response error"
}
catch {
    # Expected empty response error
    if ($_.Exception.Message -notlike "*empty*") {
        throw "Wrong error message: $($_.Exception.Message)"
    }
}

# Verify temp file was removed even after empty response error
if (Test-Path -LiteralPath $script:TempFilePath) {
    throw "Temp file still exists after empty response error"
}

Write-Output "SUCCESS: Cleanup after empty response"
"""
    )

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: Cleanup after empty response" in result.stdout


def test_get_boomi_component_xml_removes_temp_file_on_malformed_xml() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
$script:TempFilePath = $null

function Invoke-WebRequest {
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

    $script:TempFilePath = $OutFile

    # Create malformed XML
    $syntheticXml = '<Component><unclosed-tag>'
    [IO.File]::WriteAllText($OutFile, $syntheticXml, [Text.Encoding]::UTF8)
}

try {
    $result = Get-BoomiComponentXml -ComponentId "test-component-id"
    throw "Should have thrown XML parsing error"
}
catch {
    # Expected XML parsing error
    if ($_.Exception.Message -notlike "*XML*") {
        throw "Wrong error message: $($_.Exception.Message)"
    }
}

# Verify temp file was removed even after XML parsing error
if (Test-Path -LiteralPath $script:TempFilePath) {
    throw "Temp file still exists after XML parsing error"
}

Write-Output "SUCCESS: Cleanup after malformed XML"
"""
    )

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: Cleanup after malformed XML" in result.stdout


def test_get_boomi_component_xml_cleanup_failure_throws_generic_error() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
$script:TempFilePath = $null

function Invoke-WebRequest {
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

    $script:TempFilePath = $OutFile

    # Create synthetic XML file
    $syntheticXml = '<?xml version="1.0" encoding="UTF-8"?><Component><name>SYNTHETIC_COMPONENT_XML_MUST_NOT_LEAK</name></Component>'
    [IO.File]::WriteAllText($OutFile, $syntheticXml, [Text.Encoding]::UTF8)
}

# Mock Remove-Item to simulate deletion failure
function Remove-Item {
    param(
        [Parameter(Mandatory=$true)]
        [string]$LiteralPath,

        [switch]$Force,

        [ValidateSet("SilentlyContinue", "Stop")]
        [string]$ErrorAction
    )

    # Do not actually remove the file
    # Simulate a deletion failure
}

try {
    $result = Get-BoomiComponentXml -ComponentId "test-component-id"
    throw "Should have thrown cleanup failure error"
}
catch {
    # Expected cleanup-security error
    if ($_.Exception.Message -notlike "*cleanup*failed*") {
        throw "Wrong error message: $($_.Exception.Message)"
    }

    # Verify error does not contain synthetic XML
    if ($_.Exception.Message -like "*SYNTHETIC_COMPONENT_XML_MUST_NOT_LEAK*") {
        throw "Error message contains sensitive XML content"
    }

    # Verify error does not contain full temp path
    if ($_.Exception.Message -like "*$script:TempFilePath*") {
        throw "Error message contains full temp path"
    }
}

Write-Output "SUCCESS: Cleanup failure detected"
"""
    )

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: Cleanup failure detected" in result.stdout


def test_get_boomi_component_xml_primary_failure_preserved_with_cleanup_failure() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
$script:TempFilePath = $null

function Invoke-WebRequest {
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

    $script:TempFilePath = $OutFile

    # Create synthetic XML file
    $syntheticXml = '<?xml version="1.0" encoding="UTF-8"?><Component><name>SYNTHETIC_COMPONENT_XML_MUST_NOT_LEAK</name></Component>'
    [IO.File]::WriteAllText($OutFile, $syntheticXml, [Text.Encoding]::UTF8)

    # Simulate HTTP failure
    throw "Simulated HTTP failure: SYNTHETIC_HTTP_ERROR"
}

# Mock Remove-Item to simulate deletion failure
function Remove-Item {
    param(
        [Parameter(Mandatory=$true)]
        [string]$LiteralPath,

        [switch]$Force,

        [ValidateSet("SilentlyContinue", "Stop")]
        [string]$ErrorAction
    )

    # Do not actually remove the file
}

try {
    $result = Get-BoomiComponentXml -ComponentId "test-component-id"
    throw "Should have thrown primary error"
}
catch {
    # Expected PRIMARY error (HTTP failure), not cleanup error
    $errorMsg = $_.Exception.Message
    if ($errorMsg -notmatch "SYNTHETIC_HTTP_ERROR") {
        $msg = "Wrong error message (should be HTTP error, not cleanup)"
        throw $msg
    }

    # Verify error does not contain sensitive XML
    if ($errorMsg -match "SYNTHETIC_COMPONENT_XML_MUST_NOT_LEAK") {
        throw "Error message contains sensitive XML content"
    }
}

Write-Output "SUCCESS: Primary failure preserved"
"""
    )

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: Primary failure preserved" in result.stdout


def test_get_boomi_component_xml_no_leakage_in_errors() -> None:
    result = _run_component_xml_helper_harness(
        mock_script="""
function Invoke-WebRequest {
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

    # Create XML with sensitive markers
    $syntheticXml = '<?xml version="1.0" encoding="UTF-8"?><Component><name>SYNTHETIC_COMPONENT_XML_MUST_NOT_LEAK</name><password>SYNTHETIC_PASSWORD_MUST_NOT_LEAK</password></Component>'
    [IO.File]::WriteAllText($OutFile, $syntheticXml, [Text.Encoding]::UTF8)

    # Simulate HTTP failure after creating file (do not include marker in error)
    throw "HTTP failure occurred"
}

try {
    $result = Get-BoomiComponentXml -ComponentId "test-component-id"
    throw "Should have thrown error"
}
catch {
    $errorMessage = $_.Exception.Message

    # Verify error message does not contain synthetic markers
    if ($errorMessage -match "SYNTHETIC_COMPONENT_XML_MUST_NOT_LEAK") {
        throw "Error contains component XML marker"
    }

    if ($errorMessage -match "SYNTHETIC_PASSWORD_MUST_NOT_LEAK") {
        throw "Error contains password marker"
    }

    # Verify stdout/stderr do not contain markers (check captured output)
    # This is verified by the test framework checking return code and output
}

Write-Output "SUCCESS: No leakage detected"
"""
    )

    # Verify no sensitive markers in stdout/stderr
    assert "SYNTHETIC_COMPONENT_XML_MUST_NOT_LEAK" not in result.stdout
    assert "SYNTHETIC_COMPONENT_XML_MUST_NOT_LEAK" not in result.stderr
    assert "SYNTHETIC_PASSWORD_MUST_NOT_LEAK" not in result.stdout
    assert "SYNTHETIC_PASSWORD_MUST_NOT_LEAK" not in result.stderr

    assert result.returncode == 0, (
        f"Expected success, got exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "SUCCESS: No leakage detected" in result.stdout
