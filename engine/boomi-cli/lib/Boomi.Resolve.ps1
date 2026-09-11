# ============================================================
# Boomi.Resolve.ps1
# boomi-cli - Generic Component Reference Resolver
#
# Purpose:
#   Resolve human-readable component references from a spec
#   to authoritative Boomi Component IDs.
#
# Example:
#   name = "Referenced Child Process"
#       ->
#   authoritative componentId
#
# SAFETY:
#   - READ ONLY
#   - exact name matching
#   - exactly one valid current/non-deleted result required
#   - expected type validation
#   - optional expected subType validation
#
# Supported process reference roles:
#   start / connectoraction:
#       connection
#       operation
#
#   map:
#       map
#
#   connectoraction / EXECUTE:
#       connection
#       operation
#
#   processcall:
#       process
#
# NO project-specific logic.
# NO hard-coded Component IDs.
# NO Boomi writes.
# ============================================================


function Find-BoomiComponentMetadataExact {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Name
    )

    if ([string]::IsNullOrWhiteSpace($Name)) {
        throw "RESOLVE ERROR: Component name is empty."
    }

    $body = @{
        QueryFilter = @{
            expression = @{
                property = "name"
                operator = "EQUALS"
                argument = @($Name)
            }
        }
    } | ConvertTo-Json -Depth 10

    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "$script:BaseUrl/ComponentMetadata/query" `
        -Headers $script:JsonHeaders `
        -Body ([Text.Encoding]::UTF8.GetBytes($body))

    $results = @()

    foreach ($item in @($response.result)) {

        if ($null -ne $item) {
            $results += $item
        }
    }

    return $results
}


function Resolve-BoomiNamedComponent {

    param(
        [Parameter(Mandatory=$true)]
        [object]$Reference,

        [Parameter(Mandatory=$true)]
        [string]$Context
    )

    $name = [string]$Reference.name
    $expectedType = [string]$Reference.expectedType

    if ([string]::IsNullOrWhiteSpace($name)) {
        throw "RESOLVE ERROR: '$Context.name' is empty."
    }

    if ([string]::IsNullOrWhiteSpace($expectedType)) {
        throw "RESOLVE ERROR: '$Context.expectedType' is empty."
    }

    $expectedSubType = ""

    if ($null -ne $Reference.PSObject.Properties["expectedSubType"]) {
        $expectedSubType = [string]$Reference.expectedSubType
    }

    # ========================================================
    # STEP 1 - Exact metadata query
    # ========================================================

    $queryResults = @(
        Find-BoomiComponentMetadataExact `
            -Name $name
    )

    $exactResults = @(
        $queryResults |
            Where-Object {
                [string]$_.name -ceq $name
            }
    )

    if ($exactResults.Count -eq 0) {

        throw @"
RESOLVE ERROR: Component was not found.

Context:
$Context

Name:
$name
"@
    }

    # ========================================================
    # STEP 2 - Current / non-deleted filtering
    # ========================================================

    $validResults = @(
        $exactResults |
            Where-Object {

                $isCurrent = $false
                $isDeleted = $false

                if ($null -ne $_.PSObject.Properties["currentVersion"]) {
                    $isCurrent = [bool]$_.currentVersion
                }

                if ($null -ne $_.PSObject.Properties["deleted"]) {
                    $isDeleted = [bool]$_.deleted
                }

                $isCurrent -and -not $isDeleted
            }
    )

    if ($validResults.Count -eq 0) {

        throw @"
RESOLVE ERROR: Component exists, but no current non-deleted
version was found.

Context:
$Context

Name:
$name
"@
    }

    if ($validResults.Count -gt 1) {

        Write-Host ""
        Write-Host "AMBIGUOUS COMPONENT REFERENCE"
        Write-Host "============================="
        Write-Host "Context : $Context"
        Write-Host "Name    : $name"
        Write-Host ""

        $validResults |
            Select-Object `
                name,
                type,
                folderName,
                componentId |
            Format-Table -AutoSize

        throw "RESOLVE ERROR: More than one current non-deleted component has the exact requested name."
    }

    $metadata = $validResults[0]
    $componentId = [string]$metadata.componentId

    if ([string]::IsNullOrWhiteSpace($componentId)) {
        throw "RESOLVE ERROR: Resolved metadata contains no componentId."
    }

    # ========================================================
    # STEP 3 - Authoritative Component GET
    # ========================================================

    $componentResponse = Get-BoomiComponentXml `
        -ComponentId $componentId

    [xml]$componentXml = $componentResponse.Content
    $component = $componentXml.Component

    if ([string]$component.componentId -ne $componentId) {
        throw "RESOLVE ERROR: Authoritative Component ID mismatch."
    }

    if ([string]$component.name -cne $name) {

        throw @"
RESOLVE ERROR: Authoritative component name differs from
the requested exact name.

Requested:
$name

Actual:
$($component.name)
"@
    }

    # ========================================================
    # STEP 4 - Type validation
    # ========================================================

    $actualType = [string]$component.type

    if ($actualType -ne $expectedType) {

        throw @"
RESOLVE ERROR: Component type mismatch.

Context:
$Context

Component:
$name

Expected type:
$expectedType

Actual type:
$actualType
"@
    }

    # ========================================================
    # STEP 5 - Optional subType validation
    # ========================================================

    $actualSubType = [string]$component.subType

    if (-not [string]::IsNullOrWhiteSpace($expectedSubType)) {

        if ($actualSubType -ne $expectedSubType) {

            throw @"
RESOLVE ERROR: Component subType mismatch.

Context:
$Context

Component:
$name

Expected subType:
$expectedSubType

Actual subType:
$actualSubType
"@
        }
    }

    # ========================================================
    # STEP 6 - Return normalized authoritative reference
    # ========================================================

    return [PSCustomObject]@{
        Context = $Context
        Name    = [string]$component.name
        Id      = $componentId
        Type    = $actualType
        SubType = $actualSubType
        Folder  = [string]$component.folderFullPath
        Version = [string]$component.version
    }
}


function Add-BoomiResolvedReference {

    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [System.Collections.ArrayList]$Collection,

        [Parameter(Mandatory=$true)]
        [string]$Shape,

        [Parameter(Mandatory=$true)]
        [string]$Role,

        [Parameter(Mandatory=$true)]
        [object]$Reference
    )

    $item = [PSCustomObject]@{
        Shape   = $Shape
        Role    = $Role
        Name    = [string]$Reference.Name
        Id      = [string]$Reference.Id
        Type    = [string]$Reference.Type
        SubType = [string]$Reference.SubType
        Folder  = [string]$Reference.Folder
        Version = [string]$Reference.Version
    }

    [void]$Collection.Add($item)
}


function Resolve-BoomiConnectorActionReferences {

    param(
        [Parameter(Mandatory=$true)]
        [string]$ShapeName,

        [Parameter(Mandatory=$true)]
        [object]$Configuration,

        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [System.Collections.ArrayList]$ResolvedReferences
    )

    $connection = Resolve-BoomiNamedComponent `
        -Reference $Configuration.connection `
        -Context "shape[$ShapeName].connection"

    $operation = Resolve-BoomiNamedComponent `
        -Reference $Configuration.operation `
        -Context "shape[$ShapeName].operation"

    $expectedConnectorSubType = [string]$Configuration.connector.expectedSubType

    if ([string]::IsNullOrWhiteSpace($expectedConnectorSubType)) {
        throw "RESOLVE ERROR: Shape '$ShapeName' connector.expectedSubType is empty."
    }

    if ($connection.Type -ne "connector-settings") {
        throw "RESOLVE ERROR: Shape '$ShapeName' Connection is not connector-settings."
    }

    if ($operation.Type -ne "connector-action") {
        throw "RESOLVE ERROR: Shape '$ShapeName' Operation is not connector-action."
    }

    if ($connection.SubType -ne $expectedConnectorSubType) {

        throw @"
RESOLVE ERROR: Shape '$ShapeName' Connection subtype is
incompatible with connector.expectedSubType.

Expected:
$expectedConnectorSubType

Actual:
$($connection.SubType)
"@
    }

    if ($operation.SubType -ne $expectedConnectorSubType) {

        throw @"
RESOLVE ERROR: Shape '$ShapeName' Operation subtype is
incompatible with connector.expectedSubType.

Expected:
$expectedConnectorSubType

Actual:
$($operation.SubType)
"@
    }

    Add-BoomiResolvedReference `
        -Collection $ResolvedReferences `
        -Shape $ShapeName `
        -Role "connection" `
        -Reference $connection

    Add-BoomiResolvedReference `
        -Collection $ResolvedReferences `
        -Shape $ShapeName `
        -Role "operation" `
        -Reference $operation
}


function Resolve-BoomiProcessSpecReferences {

    param(
        [Parameter(Mandatory=$true)]
        [object]$SpecResult
    )

    if ($SpecResult.ComponentType -ne "process") {
        throw "RESOLVE ERROR: Process resolver received a non-process specification."
    }

    Write-Host ""
    Write-Host "Generic Process Reference Resolution"
    Write-Host "===================================="
    Write-Host "Process : $($SpecResult.ComponentName)"
    Write-Host ""

    $resolvedReferences = New-Object System.Collections.ArrayList

    foreach ($shape in @($SpecResult.Raw.process.shapes)) {

        $shapeName = [string]$shape.name
        $shapeType = [string]$shape.type
        $configuration = $shape.configuration

        switch ($shapeType) {

            "start" {

                if ([string]$configuration.kind -eq "connectoraction") {

                    Resolve-BoomiConnectorActionReferences `
                        -ShapeName $shapeName `
                        -Configuration $configuration `
                        -ResolvedReferences $resolvedReferences
                }
            }

            "map" {

                $mapReference = Resolve-BoomiNamedComponent `
                    -Reference $configuration.map `
                    -Context "shape[$shapeName].map"

                Add-BoomiResolvedReference `
                    -Collection $resolvedReferences `
                    -Shape $shapeName `
                    -Role "map" `
                    -Reference $mapReference
            }

            "connectoraction" {

                Resolve-BoomiConnectorActionReferences `
                    -ShapeName $shapeName `
                    -Configuration $configuration `
                    -ResolvedReferences $resolvedReferences
            }

            "processcall" {

                $processReference = Resolve-BoomiNamedComponent `
                    -Reference $configuration.process `
                    -Context "shape[$shapeName].process"

                Add-BoomiResolvedReference `
                    -Collection $resolvedReferences `
                    -Shape $shapeName `
                    -Role "process" `
                    -Reference $processReference
            }
        }
    }

    $resolvedArray = @(
        $resolvedReferences |
            ForEach-Object {
                $_
            }
    )

    Write-Host "Resolved references : $($resolvedArray.Count)"
    Write-Host ""

    $displayRows = @(
        $resolvedArray |
            Select-Object `
                Shape,
                Role,
                Name,
                Type,
                SubType,
                Folder,
                Version,
                Id
    )

    $displayText = $displayRows |
        Format-Table -AutoSize |
        Out-String

    Write-Host $displayText.TrimEnd()

    Write-Host ""
    Write-Host "REFERENCE RESOLUTION: OK"
    Write-Host ""
    Write-Host "No Boomi API write was performed."
    Write-Host ""

    return $resolvedArray
}


function Resolve-BoomiComponentSpecReferences {

    param(
        [Parameter(Mandatory=$true)]
        [object]$SpecResult
    )

    switch ($SpecResult.ComponentType) {

        "process" {

            return Resolve-BoomiProcessSpecReferences `
                -SpecResult $SpecResult
        }

        default {

            throw "RESOLVE ERROR: No reference resolver exists for component type '$($SpecResult.ComponentType)'."
        }
    }
}