# ============================================================
# Boomi.Validate.ps1
# boomi-cli - Generic Specification Validation Layer
#
# Purpose:
#   Validate normalized component specifications BEFORE
#   reference resolution, XML generation or Boomi CREATE.
#
# IMPORTANT:
#   - NO project-specific logic
#   - NO hard-coded Component IDs
#   - NO Boomi API writes
#   - NO XML generation
#
# Initially supported:
#   component.type = process
#
# Proven process shape contracts currently supported by the
# generic validator:
#   start / connectoraction / LISTEN
#   start / passthroughaction
#   map
#   connectoraction / EXECUTE
#   processcall
#   returndocuments
#
# Additional shape types will be added as their generic
# contracts are proven.
# ============================================================


function Test-BoomiRequiredProperty {

    param(
        [Parameter(Mandatory=$true)]
        [object]$Object,

        [Parameter(Mandatory=$true)]
        [string]$PropertyName,

        [Parameter(Mandatory=$true)]
        [string]$Context
    )

    $property = $Object.PSObject.Properties[$PropertyName]

    if ($null -eq $property) {
        throw "SPEC VALIDATION ERROR: '$Context.$PropertyName' is missing."
    }

    return $property.Value
}


function Test-BoomiRequiredString {

    param(
        [Parameter(Mandatory=$true)]
        [object]$Object,

        [Parameter(Mandatory=$true)]
        [string]$PropertyName,

        [Parameter(Mandatory=$true)]
        [string]$Context,

        [switch]$AllowEmpty
    )

    $value = Test-BoomiRequiredProperty `
        -Object $Object `
        -PropertyName $PropertyName `
        -Context $Context

    if ($null -eq $value) {
        throw "SPEC VALIDATION ERROR: '$Context.$PropertyName' is null."
    }

    $text = [string]$value

    if (
        -not $AllowEmpty -and
        [string]::IsNullOrWhiteSpace($text)
    ) {
        throw "SPEC VALIDATION ERROR: '$Context.$PropertyName' is empty."
    }

    return $text
}


function Test-BoomiRequiredBoolean {

    param(
        [Parameter(Mandatory=$true)]
        [object]$Object,

        [Parameter(Mandatory=$true)]
        [string]$PropertyName,

        [Parameter(Mandatory=$true)]
        [string]$Context
    )

    $value = Test-BoomiRequiredProperty `
        -Object $Object `
        -PropertyName $PropertyName `
        -Context $Context

    if ($value -isnot [bool]) {
        throw "SPEC VALIDATION ERROR: '$Context.$PropertyName' must be boolean."
    }

    return [bool]$value
}


function Test-BoomiRequiredNumber {

    param(
        [Parameter(Mandatory=$true)]
        [object]$Object,

        [Parameter(Mandatory=$true)]
        [string]$PropertyName,

        [Parameter(Mandatory=$true)]
        [string]$Context
    )

    $value = Test-BoomiRequiredProperty `
        -Object $Object `
        -PropertyName $PropertyName `
        -Context $Context

    if (
        $value -isnot [byte] -and
        $value -isnot [int16] -and
        $value -isnot [int32] -and
        $value -isnot [int64] -and
        $value -isnot [single] -and
        $value -isnot [double] -and
        $value -isnot [decimal]
    ) {
        throw "SPEC VALIDATION ERROR: '$Context.$PropertyName' must be numeric."
    }

    return $value
}


function Test-BoomiNamedReference {

    param(
        [Parameter(Mandatory=$true)]
        [object]$Reference,

        [Parameter(Mandatory=$true)]
        [string]$Context,

        [Parameter(Mandatory=$true)]
        [string]$ExpectedType
    )

    $name = Test-BoomiRequiredString `
        -Object $Reference `
        -PropertyName "name" `
        -Context $Context

    $type = Test-BoomiRequiredString `
        -Object $Reference `
        -PropertyName "expectedType" `
        -Context $Context

    if ($type -ne $ExpectedType) {
        throw @"
SPEC VALIDATION ERROR: '$Context.expectedType' is incompatible.

Expected:
$ExpectedType

Actual:
$type
"@
    }

    return $name
}


function Test-BoomiConnectorActionConfiguration {

    param(
        [Parameter(Mandatory=$true)]
        [object]$Configuration,

        [Parameter(Mandatory=$true)]
        [string]$Context,

        [Parameter(Mandatory=$true)]
        [string]$ExpectedActionType
    )

    $kind = Test-BoomiRequiredString `
        -Object $Configuration `
        -PropertyName "kind" `
        -Context $Context

    if ($kind -ne "connectoraction") {
        throw "SPEC VALIDATION ERROR: '$Context.kind' must be 'connectoraction'."
    }

    $actionType = Test-BoomiRequiredString `
        -Object $Configuration `
        -PropertyName "actionType" `
        -Context $Context

    if ($actionType -ne $ExpectedActionType) {

        throw @"
SPEC VALIDATION ERROR: '$Context.actionType' is not supported for this shape contract.

Expected:
$ExpectedActionType

Actual:
$actionType
"@
    }

    Test-BoomiRequiredString `
        -Object $Configuration `
        -PropertyName "allowDynamicCredentials" `
        -Context $Context |
        Out-Null

    Test-BoomiRequiredBoolean `
        -Object $Configuration `
        -PropertyName "hideSettings" `
        -Context $Context |
        Out-Null

    $connector = Test-BoomiRequiredProperty `
        -Object $Configuration `
        -PropertyName "connector" `
        -Context $Context

    Test-BoomiRequiredString `
        -Object $connector `
        -PropertyName "expectedSubType" `
        -Context "$Context.connector" |
        Out-Null

    $connection = Test-BoomiRequiredProperty `
        -Object $Configuration `
        -PropertyName "connection" `
        -Context $Context

    Test-BoomiNamedReference `
        -Reference $connection `
        -Context "$Context.connection" `
        -ExpectedType "connector-settings" |
        Out-Null

    $operation = Test-BoomiRequiredProperty `
        -Object $Configuration `
        -PropertyName "operation" `
        -Context $Context

    Test-BoomiNamedReference `
        -Reference $operation `
        -Context "$Context.operation" `
        -ExpectedType "connector-action" |
        Out-Null
}


function Test-BoomiProcessSpec {

    param(
        [Parameter(Mandatory=$true)]
        [object]$SpecResult
    )

    if ($SpecResult.ComponentType -ne "process") {
        throw "SPEC VALIDATION ERROR: Test-BoomiProcessSpec received a non-process specification."
    }

    $spec = $SpecResult.Raw
    $process = $spec.process

    Write-Host ""
    Write-Host "Generic Process Specification Validation"
    Write-Host "========================================"
    Write-Host "Name   : $($SpecResult.ComponentName)"
    Write-Host "Folder : $($SpecResult.Folder)"
    Write-Host ""

    # ========================================================
    # 1 - Safety folder
    # ========================================================

    Assert-BoomiWriteFolder `
        -Folder $SpecResult.Folder |
        Out-Null

    Write-Host "Safety folder           : OK"

    # ========================================================
    # 2 - Process settings
    # ========================================================

    $settings = Test-BoomiRequiredProperty `
        -Object $process `
        -PropertyName "settings" `
        -Context "process"

    Test-BoomiRequiredBoolean `
        -Object $settings `
        -PropertyName "allowSimultaneous" `
        -Context "process.settings" |
        Out-Null

    Test-BoomiRequiredBoolean `
        -Object $settings `
        -PropertyName "enableUserLog" `
        -Context "process.settings" |
        Out-Null

    Test-BoomiRequiredBoolean `
        -Object $settings `
        -PropertyName "processLogOnErrorOnly" `
        -Context "process.settings" |
        Out-Null

    Test-BoomiRequiredBoolean `
        -Object $settings `
        -PropertyName "purgeDataImmediately" `
        -Context "process.settings" |
        Out-Null

    Test-BoomiRequiredBoolean `
        -Object $settings `
        -PropertyName "stopProcessingIfZeroDocuments" `
        -Context "process.settings" |
        Out-Null

    Test-BoomiRequiredBoolean `
        -Object $settings `
        -PropertyName "updateRunDates" `
        -Context "process.settings" |
        Out-Null

    $workload = Test-BoomiRequiredString `
        -Object $settings `
        -PropertyName "workload" `
        -Context "process.settings"

    if ($workload -ne "general") {
        throw "SPEC VALIDATION ERROR: process.settings.workload='$workload' is not currently proven. Supported: general"
    }

    Write-Host "Process settings        : OK"

    # ========================================================
    # 3 - Shapes collection
    # ========================================================

    $shapeProperty = $process.PSObject.Properties["shapes"]

    if ($null -eq $shapeProperty) {
        throw "SPEC VALIDATION ERROR: process.shapes is missing."
    }

    $shapes = @($shapeProperty.Value)

    if ($shapes.Count -eq 0) {
        throw "SPEC VALIDATION ERROR: process.shapes is empty."
    }

    Write-Host "Shape count             : OK ($($shapes.Count))"

    # ========================================================
    # 4 - Unique shape names and generic shape properties
    # ========================================================

    $shapeNames = @()

    foreach ($shape in $shapes) {

        $shapeName = Test-BoomiRequiredString `
            -Object $shape `
            -PropertyName "name" `
            -Context "process.shapes[]"

        if ($shapeNames -contains $shapeName) {
            throw "SPEC VALIDATION ERROR: Duplicate shape name '$shapeName'."
        }

        $shapeNames += $shapeName

        $shapeType = Test-BoomiRequiredString `
            -Object $shape `
            -PropertyName "type" `
            -Context "process.shapes[$shapeName]"

        $supportedShapeTypes = @(
            "start",
            "map",
            "connectoraction",
            "processcall",
            "returndocuments",
            "stop",
            "branch",
            "catcherrors"
        )

        if ($supportedShapeTypes -notcontains $shapeType) {
            throw "SPEC VALIDATION ERROR: Shape '$shapeName' type '$shapeType' is not currently supported."
        }

        Test-BoomiRequiredString `
            -Object $shape `
            -PropertyName "image" `
            -Context "process.shapes[$shapeName]" |
            Out-Null

        Test-BoomiRequiredString `
            -Object $shape `
            -PropertyName "label" `
            -Context "process.shapes[$shapeName]" `
            -AllowEmpty |
            Out-Null

        Test-BoomiRequiredNumber `
            -Object $shape `
            -PropertyName "x" `
            -Context "process.shapes[$shapeName]" |
            Out-Null

        Test-BoomiRequiredNumber `
            -Object $shape `
            -PropertyName "y" `
            -Context "process.shapes[$shapeName]" |
            Out-Null

        $configuration = Test-BoomiRequiredProperty `
            -Object $shape `
            -PropertyName "configuration" `
            -Context "process.shapes[$shapeName]"

        $kind = Test-BoomiRequiredString `
            -Object $configuration `
            -PropertyName "kind" `
            -Context "process.shapes[$shapeName].configuration"

        # ====================================================
        # Type-specific generic contracts
        # ====================================================

        switch ($shapeType) {

            "start" {

                $supportedStartKinds = @(
                    "connectoraction",
                    "passthroughaction"
                )

                if ($supportedStartKinds -notcontains $kind) {

                    throw @"
SPEC VALIDATION ERROR: start shape '$shapeName'
has unsupported configuration.kind '$kind'.

Supported:
$($supportedStartKinds -join ", ")
"@
                }

                if ($kind -eq "connectoraction") {

                    Test-BoomiConnectorActionConfiguration `
                        -Configuration $configuration `
                        -Context "process.shapes[$shapeName].configuration" `
                        -ExpectedActionType "LISTEN"
                }

                if ($kind -eq "passthroughaction") {

                    # Proven generic contract:
                    #
                    # <configuration>
                    #   <passthroughaction />
                    # </configuration>
                }
            }

            "map" {

                if ($kind -ne "map") {
                    throw "SPEC VALIDATION ERROR: map shape '$shapeName' requires configuration.kind='map'."
                }

                $mapReference = Test-BoomiRequiredProperty `
                    -Object $configuration `
                    -PropertyName "map" `
                    -Context "process.shapes[$shapeName].configuration"

                Test-BoomiNamedReference `
                    -Reference $mapReference `
                    -Context "process.shapes[$shapeName].configuration.map" `
                    -ExpectedType "transform.map" |
                    Out-Null
            }

            "connectoraction" {

                Test-BoomiConnectorActionConfiguration `
                    -Configuration $configuration `
                    -Context "process.shapes[$shapeName].configuration" `
                    -ExpectedActionType "EXECUTE"
            }

            "processcall" {

                if ($kind -ne "processcall") {
                    throw "SPEC VALIDATION ERROR: processcall shape '$shapeName' requires configuration.kind='processcall'."
                }

                Test-BoomiRequiredBoolean `
                    -Object $configuration `
                    -PropertyName "abort" `
                    -Context "process.shapes[$shapeName].configuration" |
                    Out-Null

                Test-BoomiRequiredBoolean `
                    -Object $configuration `
                    -PropertyName "wait" `
                    -Context "process.shapes[$shapeName].configuration" |
                    Out-Null

                $processReference = Test-BoomiRequiredProperty `
                    -Object $configuration `
                    -PropertyName "process" `
                    -Context "process.shapes[$shapeName].configuration"

                Test-BoomiNamedReference `
                    -Reference $processReference `
                    -Context "process.shapes[$shapeName].configuration.process" `
                    -ExpectedType "process" |
                    Out-Null

                $returnPathsProperty = $configuration.PSObject.Properties["returnPaths"]

                if ($null -eq $returnPathsProperty) {
                    throw "SPEC VALIDATION ERROR: processcall '$shapeName' requires returnPaths."
                }

                foreach ($returnPath in @($returnPathsProperty.Value)) {

                    Test-BoomiRequiredString `
                        -Object $returnPath `
                        -PropertyName "childShapeName" `
                        -Context "process.shapes[$shapeName].configuration.returnPaths[]" |
                        Out-Null

                    Test-BoomiRequiredString `
                        -Object $returnPath `
                        -PropertyName "returnLabel" `
                        -Context "process.shapes[$shapeName].configuration.returnPaths[]" `
                        -AllowEmpty |
                        Out-Null
                }
            }

            "returndocuments" {

                if ($kind -ne "returndocuments") {
                    throw "SPEC VALIDATION ERROR: returndocuments shape '$shapeName' requires configuration.kind='returndocuments'."
                }

                Test-BoomiRequiredString `
                    -Object $configuration `
                    -PropertyName "label" `
                    -Context "process.shapes[$shapeName].configuration" `
                    -AllowEmpty |
                    Out-Null
            }

            "stop" {

                if ($kind -ne "stop") {
                    throw "SPEC VALIDATION ERROR: stop shape '$shapeName' requires configuration.kind='stop'."
                }

                Test-BoomiRequiredBoolean `
                    -Object $configuration `
                    -PropertyName "continue" `
                    -Context "process.shapes[$shapeName].configuration" |
                    Out-Null
            }

            "branch" {

                if ($kind -ne "branch") {
                    throw "SPEC VALIDATION ERROR: branch shape '$shapeName' requires configuration.kind='branch'."
                }

                Test-BoomiRequiredNumber `
                    -Object $configuration `
                    -PropertyName "numBranches" `
                    -Context "process.shapes[$shapeName].configuration" |
                    Out-Null
            }

            "catcherrors" {

                if ($kind -ne "catcherrors") {
                    throw "SPEC VALIDATION ERROR: catcherrors shape '$shapeName' requires configuration.kind='catcherrors'."
                }

                Test-BoomiRequiredBoolean `
                    -Object $configuration `
                    -PropertyName "catchAll" `
                    -Context "process.shapes[$shapeName].configuration" |
                    Out-Null

                Test-BoomiRequiredNumber `
                    -Object $configuration `
                    -PropertyName "retryCount" `
                    -Context "process.shapes[$shapeName].configuration" |
                    Out-Null
            }
        }

        # ====================================================
        # Connections property
        # ====================================================

        $connectionsProperty = $shape.PSObject.Properties["connections"]

        if ($null -eq $connectionsProperty) {
            throw "SPEC VALIDATION ERROR: Shape '$shapeName' requires a connections array."
        }

        foreach ($connectionSpec in @($connectionsProperty.Value)) {

            Test-BoomiRequiredString `
                -Object $connectionSpec `
                -PropertyName "name" `
                -Context "process.shapes[$shapeName].connections[]" |
                Out-Null

            Test-BoomiRequiredString `
                -Object $connectionSpec `
                -PropertyName "toShape" `
                -Context "process.shapes[$shapeName].connections[]" |
                Out-Null

            Test-BoomiRequiredNumber `
                -Object $connectionSpec `
                -PropertyName "x" `
                -Context "process.shapes[$shapeName].connections[]" |
                Out-Null

            Test-BoomiRequiredNumber `
                -Object $connectionSpec `
                -PropertyName "y" `
                -Context "process.shapes[$shapeName].connections[]" |
                Out-Null
        }
    }

    Write-Host "Shape definitions       : OK"
    Write-Host "Unique shape names      : OK"

    # ========================================================
    # 5 - Topology validation
    # ========================================================

    foreach ($shape in $shapes) {

        $shapeName = [string]$shape.name

        foreach ($connectionSpec in @($shape.connections)) {

            $toShape = [string]$connectionSpec.toShape

            if ($shapeNames -notcontains $toShape) {
                throw "SPEC VALIDATION ERROR: Shape '$shapeName' points to unknown toShape '$toShape'."
            }
        }

        if ([string]$shape.type -eq "processcall") {

            foreach ($returnPath in @($shape.configuration.returnPaths)) {

                $childShapeName = [string]$returnPath.childShapeName

                if ($shapeNames -notcontains $childShapeName) {
                    throw "SPEC VALIDATION ERROR: Process Call '$shapeName' returnPath points to unknown shape '$childShapeName'."
                }
            }
        }
    }

    Write-Host "Topology references     : OK"

    # ========================================================
    # 6 - Start shape cardinality
    # ========================================================

    $startShapes = @(
        $shapes |
            Where-Object {
                [string]$_.type -eq "start"
            }
    )

    if ($startShapes.Count -ne 1) {
        throw "SPEC VALIDATION ERROR: Process requires exactly one start shape. Found: $($startShapes.Count)"
    }

    Write-Host "Start shape cardinality : OK (1)"
    Write-Host ""
    Write-Host "SPEC VALIDATION: OK"
    Write-Host ""
    Write-Host "No Boomi API write was performed."
    Write-Host ""

    return $true
}


function Test-BoomiComponentSpec {

    param(
        [Parameter(Mandatory=$true)]
        [object]$SpecResult
    )

    switch ($SpecResult.ComponentType) {

        "process" {

            return Test-BoomiProcessSpec `
                -SpecResult $SpecResult
        }

        default {

            throw "SPEC VALIDATION ERROR: No validator exists for component type '$($SpecResult.ComponentType)'."
        }
    }
}