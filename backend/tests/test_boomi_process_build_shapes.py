from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def _app_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_batch1_harness() -> subprocess.CompletedProcess[str]:
    app_root = _app_root()
    cli_root = app_root / "engine" / "boomi-cli"
    workspace_root = app_root / "data"
    lib_root = cli_root / "lib"

    script = rf"""
$ErrorActionPreference = "Stop"

$script:CliRoot = "{cli_root}"
$script:WorkspaceRoot = "{workspace_root}"

try {{

    . "{lib_root / 'Boomi.Common.ps1'}"
    . "{lib_root / 'Boomi.Validate.ps1'}"
    . "{lib_root / 'Boomi.Build.ps1'}"
    . "{lib_root / 'Boomi.Verify.ps1'}"

    function Assert-BoomiWriteFolder {{
        param(
            [Parameter(Mandatory=$true)]
            [string]$Folder
        )

        if ([string]::IsNullOrWhiteSpace($Folder)) {{
            throw "TEST ERROR: Synthetic folder is empty."
        }}

        return $true
    }}

    $Raw = [PSCustomObject]@{{
        component = [PSCustomObject]@{{
            name = "Synthetic Batch 1 Process"
            type = "process"
            folder = "Synthetic/Test"
        }}

        process = [PSCustomObject]@{{
            settings = [PSCustomObject]@{{
                allowSimultaneous = $false
                enableUserLog = $false
                processLogOnErrorOnly = $false
                purgeDataImmediately = $false
                stopProcessingIfZeroDocuments = $true
                updateRunDates = $false
                workload = "general"
            }}

            shapes = @(
                [PSCustomObject]@{{
                    name = "shape1"
                    type = "start"
                    image = "start"
                    label = ""
                    x = 96
                    y = 96
                    configuration = [PSCustomObject]@{{
                        kind = "passthroughaction"
                    }}
                    connections = @(
                        [PSCustomObject]@{{
                            name = "shape1.dragpoint1"
                            toShape = "shape2"
                            x = 176
                            y = 96
                        }}
                    )
                }},

                [PSCustomObject]@{{
                    name = "shape2"
                    type = "branch"
                    image = "branch_icon"
                    label = "Synthetic Branch"
                    x = 272
                    y = 96
                    configuration = [PSCustomObject]@{{
                        kind = "branch"
                        numBranches = 2
                    }}
                    connections = @(
                        [PSCustomObject]@{{
                            identifier = "1"
                            text = "Path 1"
                            name = "shape2.dragpoint1"
                            toShape = "shape3"
                            x = 368
                            y = 64
                        }},
                        [PSCustomObject]@{{
                            identifier = "2"
                            text = "Path 2"
                            name = "shape2.dragpoint2"
                            toShape = "shape4"
                            x = 368
                            y = 160
                        }}
                    )
                }},

                [PSCustomObject]@{{
                    name = "shape3"
                    type = "catcherrors"
                    image = "catcherrors_icon"
                    label = "Synthetic Catch Errors"
                    x = 464
                    y = 64
                    configuration = [PSCustomObject]@{{
                        kind = "catcherrors"
                        catchAll = $true
                        retryCount = 0
                    }}
                    connections = @(
                        [PSCustomObject]@{{
                            identifier = "1"
                            text = "Success"
                            name = "shape3.dragpoint1"
                            toShape = "shape4"
                            x = 560
                            y = 64
                        }},
                        [PSCustomObject]@{{
                            identifier = "2"
                            text = "Error"
                            name = "shape3.dragpoint2"
                            toShape = "shape5"
                            x = 560
                            y = 160
                        }}
                    )
                }},

                [PSCustomObject]@{{
                    name = "shape4"
                    type = "stop"
                    image = "stop_icon"
                    label = "Synthetic Stop 1"
                    x = 656
                    y = 64
                    configuration = [PSCustomObject]@{{
                        kind = "stop"
                        continue = $true
                    }}
                    connections = @()
                }},

                [PSCustomObject]@{{
                    name = "shape5"
                    type = "stop"
                    image = "stop_icon"
                    label = "Synthetic Stop 2"
                    x = 656
                    y = 160
                    configuration = [PSCustomObject]@{{
                        kind = "stop"
                        continue = $true
                    }}
                    connections = @()
                }}
            )
        }}
    }}

    $SpecResult = [PSCustomObject]@{{
        Path = "<synthetic>"
        SpecVersion = "test"
        ComponentName = "Synthetic Batch 1 Process"
        ComponentType = "process"
        Folder = "Synthetic/Test"
        Raw = $Raw
    }}

    $validation = Test-BoomiProcessSpec `
        -SpecResult $SpecResult

    if ($validation -ne $true) {{
        throw "Validation did not return True."
    }}

    $FolderId = "00000000-0000-0000-0000-000000000001"
    $BranchId = "00000000-0000-0000-0000-000000000002"

    $Xml = New-BoomiProcessXml `
        -SpecResult $SpecResult `
        -ResolvedReferences @() `
        -FolderId $FolderId `
        -BranchId $BranchId

    if ($null -eq $Xml) {{
        throw "Builder returned null."
    }}

    $verify = Test-BoomiGeneratedProcessXml `
        -SpecResult $SpecResult `
        -ResolvedReferences @() `
        -Xml $Xml `
        -FolderId $FolderId `
        -BranchId $BranchId

    if ($verify -ne $true) {{
        throw "Verification did not return True."
    }}

    $ProcessNode = $Xml.SelectSingleNode(
        "/*[local-name()='Component']/*[local-name()='object']/*[local-name()='process']"
    )

    if ($null -eq $ProcessNode) {{
        throw "Generated process node missing."
    }}

    $StopNodes = @(
        $ProcessNode.SelectNodes(
            "./*[local-name()='shapes']/*[local-name()='shape']/*[local-name()='configuration']/*[local-name()='stop']"
        )
    )

    $BranchNodes = @(
        $ProcessNode.SelectNodes(
            "./*[local-name()='shapes']/*[local-name()='shape']/*[local-name()='configuration']/*[local-name()='branch']"
        )
    )

    $CatchNodes = @(
        $ProcessNode.SelectNodes(
            "./*[local-name()='shapes']/*[local-name()='shape']/*[local-name()='configuration']/*[local-name()='catcherrors']"
        )
    )

    $TextDragpoints = @(
        $ProcessNode.SelectNodes(
            "./*[local-name()='shapes']/*[local-name()='shape']/*[local-name()='dragpoints']/*[local-name()='dragpoint'][@text]"
        )
    )

    if ($StopNodes.Count -ne 2) {{
        throw "Expected exactly two stop nodes."
    }}

    foreach ($Node in $StopNodes) {{
        if ($Node.GetAttribute("continue") -ne "true") {{
            throw "Unexpected stop continue value."
        }}
    }}

    if ($BranchNodes.Count -ne 1) {{
        throw "Expected exactly one branch node."
    }}

    if (
        $BranchNodes[0].GetAttribute("numBranches") -ne "2"
    ) {{
        throw "Unexpected branch numBranches value."
    }}

    if ($CatchNodes.Count -ne 1) {{
        throw "Expected exactly one catcherrors node."
    }}

    if (
        $CatchNodes[0].GetAttribute("catchAll") -ne "true"
    ) {{
        throw "Unexpected catchAll value."
    }}

    if (
        $CatchNodes[0].GetAttribute("retryCount") -ne "0"
    ) {{
        throw "Unexpected retryCount value."
    }}

    if ($TextDragpoints.Count -ne 4) {{
        throw "Expected exactly four text dragpoints."
    }}

    $ExpectedTexts = @(
        "Path 1",
        "Path 2",
        "Success",
        "Error"
    )

    foreach ($ExpectedText in $ExpectedTexts) {{

        $Matches = @(
            $TextDragpoints |
                Where-Object {{
                    $_.GetAttribute("text") -eq
                    $ExpectedText
                }}
        )

        if ($Matches.Count -ne 1) {{
            throw "Missing or duplicate dragpoint text: $ExpectedText"
        }}
    }}

    Write-Output "BATCH1_VALIDATE_OK"
    Write-Output "BATCH1_BUILD_OK"
    Write-Output "BATCH1_VERIFY_OK"
    Write-Output "BATCH1_STRUCTURE_OK"

    exit 0
}}
catch {{

    Write-Error $_.Exception.Message
    exit 1
}}
"""

    with tempfile.TemporaryDirectory(
        prefix="boomi-builder-batch1-"
    ) as temp_dir:
        script_path = Path(temp_dir) / "batch1_acceptance.ps1"

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
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )


def _run_validation_failure(
    *,
    shape_type: str,
    configuration_lines: list[str],
) -> subprocess.CompletedProcess[str]:
    app_root = _app_root()
    cli_root = app_root / "engine" / "boomi-cli"
    workspace_root = app_root / "data"
    lib_root = cli_root / "lib"

    configuration = "\n".join(configuration_lines)

    script = rf"""
$ErrorActionPreference = "Stop"

$script:CliRoot = "{cli_root}"
$script:WorkspaceRoot = "{workspace_root}"

try {{

    . "{lib_root / 'Boomi.Common.ps1'}"
    . "{lib_root / 'Boomi.Validate.ps1'}"

    function Assert-BoomiWriteFolder {{
        param(
            [Parameter(Mandatory=$true)]
            [string]$Folder
        )

        return $true
    }}

    $Configuration = [PSCustomObject]@{{
{configuration}
    }}

    $Raw = [PSCustomObject]@{{
        component = [PSCustomObject]@{{
            name = "Synthetic Negative Process"
            type = "process"
            folder = "Synthetic/Test"
        }}

        process = [PSCustomObject]@{{
            settings = [PSCustomObject]@{{
                allowSimultaneous = $false
                enableUserLog = $false
                processLogOnErrorOnly = $false
                purgeDataImmediately = $false
                stopProcessingIfZeroDocuments = $true
                updateRunDates = $false
                workload = "general"
            }}

            shapes = @(
                [PSCustomObject]@{{
                    name = "shape1"
                    type = "start"
                    image = "start"
                    label = ""
                    x = 96
                    y = 96
                    configuration = [PSCustomObject]@{{
                        kind = "passthroughaction"
                    }}
                    connections = @(
                        [PSCustomObject]@{{
                            name = "shape1.dragpoint1"
                            toShape = "shape2"
                            x = 176
                            y = 96
                        }}
                    )
                }},

                [PSCustomObject]@{{
                    name = "shape2"
                    type = "{shape_type}"
                    image = "{shape_type}_icon"
                    label = "Negative Shape"
                    x = 272
                    y = 96
                    configuration = $Configuration
                    connections = @()
                }}
            )
        }}
    }}

    $SpecResult = [PSCustomObject]@{{
        Path = "<synthetic>"
        SpecVersion = "test"
        ComponentName = "Synthetic Negative Process"
        ComponentType = "process"
        Folder = "Synthetic/Test"
        Raw = $Raw
    }}

    Test-BoomiProcessSpec `
        -SpecResult $SpecResult |
        Out-Null

    Write-Output "UNEXPECTED_VALIDATION_SUCCESS"
    exit 0
}}
catch {{

    Write-Output "EXPECTED_VALIDATION_FAILURE"
    Write-Output $_.Exception.Message
    exit 23
}}
"""

    with tempfile.TemporaryDirectory(
        prefix="boomi-builder-negative-"
    ) as temp_dir:
        script_path = Path(temp_dir) / "negative_validation.ps1"

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
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )


def _assert_validation_rejected(
    result: subprocess.CompletedProcess[str],
) -> None:
    assert result.returncode == 23, (
        "Invalid shape specification was not rejected "
        "as expected.\n"
        f"returncode: {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    assert "EXPECTED_VALIDATION_FAILURE" in result.stdout
    assert "UNEXPECTED_VALIDATION_SUCCESS" not in result.stdout


def test_stop_rejects_non_boolean_continue() -> None:
    result = _run_validation_failure(
        shape_type="stop",
        configuration_lines=[
            '        kind = "stop"',
            '        continue = "not-a-boolean"',
        ],
    )

    _assert_validation_rejected(result)


def test_branch_rejects_non_numeric_num_branches() -> None:
    result = _run_validation_failure(
        shape_type="branch",
        configuration_lines=[
            '        kind = "branch"',
            '        numBranches = "not-a-number"',
        ],
    )

    _assert_validation_rejected(result)


def test_catcherrors_rejects_non_boolean_catch_all() -> None:
    result = _run_validation_failure(
        shape_type="catcherrors",
        configuration_lines=[
            '        kind = "catcherrors"',
            '        catchAll = "not-a-boolean"',
            '        retryCount = 0',
        ],
    )

    _assert_validation_rejected(result)

def test_batch1_stop_branch_catcherrors_build_contract() -> None:
    result = _run_batch1_harness()

    assert result.returncode == 0, (
        "Batch 1 PowerShell harness failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    assert "BATCH1_VALIDATE_OK" in result.stdout
    assert "BATCH1_BUILD_OK" in result.stdout
    assert "BATCH1_VERIFY_OK" in result.stdout
    assert "BATCH1_STRUCTURE_OK" in result.stdout

def _run_batch2a_decision_harness() -> subprocess.CompletedProcess[str]:
    app_root = _app_root()
    cli_root = app_root / "engine" / "boomi-cli"
    lib_root = cli_root / "lib"

    harness = rf"""
$ErrorActionPreference = "Stop"

$script:CliRoot = "{cli_root}"
$script:WorkspaceRoot = "{app_root / "data"}"

. "{lib_root / "Boomi.Common.ps1"}"
. "{lib_root / "Boomi.Validate.ps1"}"
. "{lib_root / "Boomi.Build.ps1"}"
. "{lib_root / "Boomi.Verify.ps1"}"

function Assert-BoomiWriteFolder {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Folder
    )

    if ($Folder -ne "Synthetic/Test") {{
        throw "Unexpected synthetic folder."
    }}

    return $true
}}

function New-DecisionSpec {{
    param(
        [Parameter(Mandatory=$true)]
        [object[]]$Values
    )

    $raw = [PSCustomObject]@{{
        component = [PSCustomObject]@{{
            name = "Synthetic Decision Process"
            type = "process"
            folder = "Synthetic/Test"
        }}

        process = [PSCustomObject]@{{
            settings = [PSCustomObject]@{{
                allowSimultaneous = $false
                enableUserLog = $false
                processLogOnErrorOnly = $false
                purgeDataImmediately = $false
                stopProcessingIfZeroDocuments = $true
                updateRunDates = $false
                workload = "general"
            }}

            shapes = @(
                [PSCustomObject]@{{
                    name = "shape1"
                    type = "start"
                    image = "start"
                    label = ""
                    x = 96
                    y = 96
                    configuration = [PSCustomObject]@{{
                        kind = "passthroughaction"
                    }}
                    connections = @(
                        [PSCustomObject]@{{
                            name = "shape1.dragpoint1"
                            toShape = "shape2"
                            x = 176
                            y = 96
                        }}
                    )
                }},

                [PSCustomObject]@{{
                    name = "shape2"
                    type = "decision"
                    image = "decision_icon"
                    label = "Synthetic Decision"
                    x = 272
                    y = 96
                    configuration = [PSCustomObject]@{{
                        kind = "decision"
                        name = "Synthetic Decision"
                        comparison = "equals"
                        values = $Values
                    }}
                    connections = @(
                        [PSCustomObject]@{{
                            identifier = "1"
                            text = "True"
                            name = "shape2.dragpoint1"
                            toShape = "shape3"
                            x = 368
                            y = 64
                        }},
                        [PSCustomObject]@{{
                            identifier = "2"
                            text = "False"
                            name = "shape2.dragpoint2"
                            toShape = "shape4"
                            x = 368
                            y = 160
                        }}
                    )
                }},

                [PSCustomObject]@{{
                    name = "shape3"
                    type = "stop"
                    image = "stop_icon"
                    label = "Stop True"
                    x = 464
                    y = 64
                    configuration = [PSCustomObject]@{{
                        kind = "stop"
                        continue = $true
                    }}
                    connections = @()
                }},

                [PSCustomObject]@{{
                    name = "shape4"
                    type = "stop"
                    image = "stop_icon"
                    label = "Stop False"
                    x = 464
                    y = 160
                    configuration = [PSCustomObject]@{{
                        kind = "stop"
                        continue = $true
                    }}
                    connections = @()
                }}
            )
        }}
    }}

    return [PSCustomObject]@{{
        Path = "<synthetic>"
        SpecVersion = "test"
        ComponentName = "Synthetic Decision Process"
        ComponentType = "process"
        Folder = "Synthetic/Test"
        Raw = $raw
    }}
}}

$validValues = @(
    [PSCustomObject]@{{
        valueType = "process"
        process = [PSCustomObject]@{{
            processProperty = "synthetic.process.property"
            processPropertyDefaultValue = ""
        }}
    }},
    [PSCustomObject]@{{
        valueType = "static"
        static = [PSCustomObject]@{{
            value = "synthetic-static-value"
        }}
    }}
)

$spec = New-DecisionSpec -Values $validValues

Test-BoomiProcessSpec -SpecResult $spec | Out-Null
Write-Output "BATCH2A_VALIDATE_OK"

$xml = New-BoomiProcessXml `
    -SpecResult $spec `
    -ResolvedReferences @() `
    -FolderId "synthetic-folder-id" `
    -BranchId "synthetic-branch-id"

Write-Output "BATCH2A_BUILD_OK"

Test-BoomiGeneratedComponentXml `
    -SpecResult $spec `
    -ResolvedReferences @() `
    -Xml $xml `
    -FolderId "synthetic-folder-id" `
    -BranchId "synthetic-branch-id" |
    Out-Null

Write-Output "BATCH2A_VERIFY_OK"

$decision = $xml.SelectSingleNode(
    "//*[local-name()='shape' and @shapetype='decision']/*[local-name()='configuration']/*[local-name()='decision']"
)

if ($null -eq $decision) {{
    throw "Decision node missing."
}}

if ($decision.Attributes.Count -ne 2) {{
    throw "Decision root attribute count mismatch."
}}

$values = @(
    $decision.SelectNodes(
        "./*[local-name()='decisionvalue']"
    )
)

if ($values.Count -ne 2) {{
    throw "Decision value count mismatch."
}}

if (
    $values[0].GetAttribute("valueType") -ne "process" -or
    $values[1].GetAttribute("valueType") -ne "static"
) {{
    throw "Decision value order mismatch."
}}

$processParameter = $values[0].SelectSingleNode(
    "./*[local-name()='processparameter']"
)

$staticParameter = $values[1].SelectSingleNode(
    "./*[local-name()='staticparameter']"
)

if (
    $null -eq $processParameter -or
    $null -eq $staticParameter
) {{
    throw "Decision operand structure mismatch."
}}

if (
    $processParameter.GetAttribute("processproperty") -ne
    "synthetic.process.property"
) {{
    throw "processproperty mismatch."
}}

if (
    $staticParameter.GetAttribute("staticproperty") -ne
    "synthetic-static-value"
) {{
    throw "staticproperty mismatch."
}}

Write-Output "BATCH2A_STRUCTURE_OK"

$badXml = New-Object System.Xml.XmlDocument
$badXml.LoadXml($xml.OuterXml)

$badStatic = $badXml.SelectSingleNode(
    "//*[local-name()='shape' and @shapetype='decision']/*[local-name()='configuration']/*[local-name()='decision']/*[local-name()='decisionvalue' and @valueType='static']/*[local-name()='staticparameter']"
)

$badStatic.SetAttribute(
    "staticproperty",
    "wrong-synthetic-value"
)

$mutationRejected = $false

try {{
    Test-BoomiGeneratedComponentXml `
        -SpecResult $spec `
        -ResolvedReferences @() `
        -Xml $badXml `
        -FolderId "synthetic-folder-id" `
        -BranchId "synthetic-branch-id" |
        Out-Null
}}
catch {{
    $mutationRejected = $true
}}

if (-not $mutationRejected) {{
    throw "Verifier accepted mutated staticproperty."
}}

Write-Output "BATCH2A_MUTATION_REJECTED"

$unsupportedValues = @(
    [PSCustomObject]@{{
        valueType = "unsupported"
    }},
    [PSCustomObject]@{{
        valueType = "static"
        static = [PSCustomObject]@{{
            value = "synthetic"
        }}
    }}
)

$unsupportedRejected = $false

try {{
    Test-BoomiProcessSpec `
        -SpecResult (
            New-DecisionSpec `
                -Values $unsupportedValues
        ) |
        Out-Null
}}
catch {{
    $unsupportedRejected = (
        $_.Exception.Message -like
        "*valueType*not currently proven*"
    )
}}

if (-not $unsupportedRejected) {{
    throw "Unsupported valueType was not rejected."
}}

Write-Output "BATCH2A_UNSUPPORTED_REJECTED"

$oneValue = @(
    [PSCustomObject]@{{
        valueType = "static"
        static = [PSCustomObject]@{{
            value = "synthetic"
        }}
    }}
)

$cardinalityRejected = $false

try {{
    Test-BoomiProcessSpec `
        -SpecResult (
            New-DecisionSpec `
                -Values $oneValue
        ) |
        Out-Null
}}
catch {{
    $cardinalityRejected = (
        $_.Exception.Message -like
        "*requires exactly two values*"
    )
}}

if (-not $cardinalityRejected) {{
    throw "Invalid Decision cardinality was not rejected."
}}

Write-Output "BATCH2A_CARDINALITY_REJECTED"

$twoStatic = @(
    [PSCustomObject]@{{
        valueType = "static"
        static = [PSCustomObject]@{{
            value = "synthetic-a"
        }}
    }},
    [PSCustomObject]@{{
        valueType = "static"
        static = [PSCustomObject]@{{
            value = "synthetic-b"
        }}
    }}
)

$combinationRejected = $false

try {{
    Test-BoomiProcessSpec `
        -SpecResult (
            New-DecisionSpec `
                -Values $twoStatic
        ) |
        Out-Null
}}
catch {{
    $combinationRejected = (
        $_.Exception.Message -like
        "*exactly one process value and one static value*"
    )
}}

if (-not $combinationRejected) {{
    throw "Invalid Decision value combination was not rejected."
}}

Write-Output "BATCH2A_COMBINATION_REJECTED"
"""

    with tempfile.TemporaryDirectory(
        prefix="boomi-builder-decision-"
    ) as temp_dir:
        script_path = Path(temp_dir) / "decision_acceptance.ps1"
        script_path.write_text(
            harness,
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
            cwd=app_root,
            capture_output=True,
            text=True,
            check=False,
        )


def test_batch2a_decision_build_contract() -> None:
    result = _run_batch2a_decision_harness()

    assert result.returncode == 0, (
        "Batch 2A PowerShell harness failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    expected_markers = (
        "BATCH2A_VALIDATE_OK",
        "BATCH2A_BUILD_OK",
        "BATCH2A_VERIFY_OK",
        "BATCH2A_STRUCTURE_OK",
        "BATCH2A_MUTATION_REJECTED",
        "BATCH2A_UNSUPPORTED_REJECTED",
        "BATCH2A_CARDINALITY_REJECTED",
        "BATCH2A_COMBINATION_REJECTED",
    )

    for marker in expected_markers:
        assert marker in result.stdout
