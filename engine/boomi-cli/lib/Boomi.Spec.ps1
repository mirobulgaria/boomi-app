# ============================================================
# Boomi.Spec.ps1
# boomi-cli - Generic Component Specification Layer
#
# Purpose:
#   Read and perform basic validation of external JSON
#   component specification files.
#
# IMPORTANT:
#   - Contains NO S1/S2/S3/S4 logic.
#   - Contains NO Boomi Component IDs.
#   - Performs NO Boomi API writes.
#   - Does NOT build Component XML.
#
# Supported specification version:
#   1
#
# Initially supported component type:
#   process
#
# Other component types will be added only after their
# specification contracts are proven.
# ============================================================


function Read-BoomiComponentSpec {

    param(
        [Parameter(Mandatory=$true)]
        [string]$SpecPath
    )

    # ========================================================
    # STEP 1 - Resolve path
    # ========================================================

    if ([string]::IsNullOrWhiteSpace($SpecPath)) {
        throw "SPEC ERROR: SpecPath is empty."
    }

    try {
        $resolvedPath = (
            Resolve-Path `
                -LiteralPath $SpecPath `
                -ErrorAction Stop
        ).Path
    }
    catch {
        throw "SPEC ERROR: Specification file was not found: $SpecPath"
    }

    if (-not (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
        throw "SPEC ERROR: SpecPath is not a file: $resolvedPath"
    }

    # ========================================================
    # STEP 2 - Read explicitly as UTF-8
    # ========================================================

    try {

        $jsonText = [IO.File]::ReadAllText(
            $resolvedPath,
            [Text.Encoding]::UTF8
        )
    }
    catch {

        throw "SPEC ERROR: Failed to read specification file as UTF-8: $resolvedPath"
    }

    if ([string]::IsNullOrWhiteSpace($jsonText)) {
        throw "SPEC ERROR: Specification file is empty: $resolvedPath"
    }

    # Remove UTF-8 BOM character if present.
    if (
        $jsonText.Length -gt 0 -and
        [int][char]$jsonText[0] -eq 0xFEFF
    ) {
        $jsonText = $jsonText.Substring(1)
    }

    # ========================================================
    # STEP 3 - Parse JSON
    # ========================================================

    try {

        $spec = $jsonText |
            ConvertFrom-Json `
                -ErrorAction Stop
    }
    catch {

        throw "SPEC ERROR: Invalid JSON in specification file: $resolvedPath"
    }

    if ($null -eq $spec) {
        throw "SPEC ERROR: JSON produced no specification object."
    }

    # ========================================================
    # STEP 4 - Validate specification envelope
    # ========================================================

    if ($null -eq $spec.specVersion) {
        throw "SPEC ERROR: Required property 'specVersion' is missing."
    }

    $specVersion = [string]$spec.specVersion

    if ($specVersion -ne "1") {

        throw @"
SPEC ERROR: Unsupported specification version.

Actual:
$specVersion

Supported:
1
"@
    }

    if ($null -eq $spec.component) {
        throw "SPEC ERROR: Required object 'component' is missing."
    }

    # ========================================================
    # STEP 5 - Validate generic component metadata
    # ========================================================

    $componentName = [string]$spec.component.name
    $componentType = [string]$spec.component.type
    $componentFolder = [string]$spec.component.folder

    if ([string]::IsNullOrWhiteSpace($componentName)) {
        throw "SPEC ERROR: component.name is required."
    }

    if ([string]::IsNullOrWhiteSpace($componentType)) {
        throw "SPEC ERROR: component.type is required."
    }

    if ([string]::IsNullOrWhiteSpace($componentFolder)) {
        throw "SPEC ERROR: component.folder is required."
    }

    # ========================================================
    # STEP 6 - Current type allow-list
    #
    # We deliberately begin with process only.
    # This is NOT a permanent restriction.
    # ========================================================

    $supportedTypes = @(
        "process"
    )

    if ($supportedTypes -notcontains $componentType) {

        throw @"
SPEC ERROR: Component type is not currently supported by
the generic specification layer.

Actual:
$componentType

Currently supported:
$($supportedTypes -join ", ")
"@
    }

    # ========================================================
    # STEP 7 - Type-specific envelope check
    #
    # Detailed Process validation belongs in Boomi.Validate.ps1.
    # Here we only confirm that the required section exists.
    # ========================================================

    switch ($componentType) {

        "process" {

            if ($null -eq $spec.process) {
                throw "SPEC ERROR: component.type='process' requires a 'process' object."
            }
        }
    }

    # ========================================================
    # STEP 8 - Return normalized wrapper
    # ========================================================

    return [PSCustomObject]@{
        Path          = $resolvedPath
        SpecVersion   = $specVersion
        ComponentName = $componentName
        ComponentType = $componentType
        Folder        = $componentFolder
        Raw           = $spec
    }
}


function Show-BoomiComponentSpec {

    param(
        [Parameter(Mandatory=$true)]
        [string]$SpecPath
    )

    $result = Read-BoomiComponentSpec `
        -SpecPath $SpecPath

    Write-Host ""
    Write-Host "Boomi Component Specification"
    Write-Host "============================="
    Write-Host "File         : $($result.Path)"
    Write-Host "Spec Version : $($result.SpecVersion)"
    Write-Host "Name         : $($result.ComponentName)"
    Write-Host "Type         : $($result.ComponentType)"
    Write-Host "Folder       : $($result.Folder)"
    Write-Host ""
    Write-Host "SPEC READ: OK"
    Write-Host ""
    Write-Host "No Boomi API write was performed."
    Write-Host ""

    return $result
}