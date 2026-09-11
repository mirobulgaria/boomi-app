# ============================================================
# Boomi.Connector.ps1
# boomi-cli v1 SAFE Connector reference update
#
# HARD SAFETY BOUNDARY:
#   Write access is controlled by the external CLI
#   write policy.
#
# Current proven connector:
#   connectorType = wssoapclientsdk
#   actionType    = EXECUTE
#
# Capability:
#   Set-BoomiConnectorTarget
#
# Intended changes:
#   configuration/connectoraction/@connectionId
#   configuration/connectoraction/@operationId
#
# Does NOT:
#   - modify Connection component
#   - modify Operation component
#   - modify connectorType
#   - modify actionType
#   - modify parameters
#   - modify dynamicProperties
#   - modify Display Name
#   - add/remove shapes
#   - deploy
#   - execute
#   - delete
# ============================================================


function Get-BoomiConnectorReferenceSnapshot {

    param(
        [Parameter(Mandatory=$true)]
        [xml]$Xml
    )

    $result = New-Object System.Collections.Generic.List[string]

    $shapes = @(
        $Xml.SelectNodes(
            "//*[local-name()='shape'][@shapetype='connectoraction']"
        )
    )

    foreach ($shape in $shapes) {

        $node = $shape.SelectSingleNode(
            "./*[local-name()='configuration']/*[local-name()='connectoraction']"
        )

        if ($node) {

            $result.Add(
                "$([string]$shape.name)|$([string]$node.connectorType)|$([string]$node.actionType)|$([string]$node.connectionId)|$([string]$node.operationId)"
            )
        }
    }

    return @($result | Sort-Object)
}


function Get-BoomiSoapOperationMetadata {

    param(
        [Parameter(Mandatory=$true)]
        [xml]$Xml
    )

    $component = $Xml.Component

    if ([string]$component.type -ne "connector-action") {
        throw "Target Operation is not type 'connector-action'."
    }

    $genericConfig = $Xml.SelectSingleNode(
        "/*[local-name()='Component']/*[local-name()='object']//*[local-name()='GenericOperationConfig']"
    )

    if (-not $genericConfig) {
        throw "GenericOperationConfig was not found in target Operation."
    }

    return [PSCustomObject]@{
        Type                = [string]$component.type
        SubType             = [string]$component.subType
        OperationType       = [string]$genericConfig.operationType
        RequestProfileType  = [string]$genericConfig.requestProfileType
        ResponseProfileType = [string]$genericConfig.responseProfileType
    }
}


function Set-BoomiConnectorTarget {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id,

        [Parameter(Mandatory=$true)]
        [string]$Shape,

        [Parameter(Mandatory=$true)]
        [string]$TargetConnectionId,

        [Parameter(Mandatory=$true)]
        [string]$TargetOperationId
    )

    Write-Host ""
    Write-Host "SAFE UPDATE - Connector Target"
    Write-Host "=============================="
    Write-Host ""

    # ========================================================
    # STEP 1 - GET authoritative process
    # ========================================================

    Write-Host "STEP 1 - Read process to modify"
    Write-Host "==============================="

    $sourceResponse = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$sourceXml = $sourceResponse.Content
    $source = $sourceXml.Component

    Write-Host "Process : $($source.name)"
    Write-Host "ID      : $($source.componentId)"
    Write-Host "Version : $($source.version)"
    Write-Host "Folder  : $($source.folderFullPath)"
    Write-Host ""

    if ($source.componentId -ne $Id) {
        throw "UPDATE BLOCKED: Component ID mismatch."
    }

    if ($source.type -ne "process") {
        throw "UPDATE BLOCKED: Component is not a process."
    }

    # ========================================================
    # STEP 2 - Safety boundary
    # ========================================================

    Assert-BoomiWriteFolder `
        -Folder ([string]$source.folderFullPath)

    Write-Host "STEP 2 - Safety boundary"
    Write-Host "========================"
    Write-Host "Write folder : OK"
    Write-Host ""

    # ========================================================
    # STEP 3 - Locate connector shape
    # ========================================================

    $shapeNodes = @(
        $sourceXml.SelectNodes(
            "//*[local-name()='shape'][@name='$Shape']"
        )
    )

    if ($shapeNodes.Count -eq 0) {
        throw "UPDATE BLOCKED: Shape '$Shape' was not found."
    }

    if ($shapeNodes.Count -gt 1) {
        throw "UPDATE BLOCKED: Multiple shapes named '$Shape' were found."
    }

    $shapeNode = $shapeNodes[0]
    $shapeType = [string]$shapeNode.shapetype

    if ($shapeType -ne "connectoraction") {
        throw "UPDATE BLOCKED: Shape '$Shape' is '$shapeType', not 'connectoraction'."
    }

    $connectorNode = $shapeNode.SelectSingleNode(
        "./*[local-name()='configuration']/*[local-name()='connectoraction']"
    )

    if (-not $connectorNode) {
        throw "UPDATE BLOCKED: Connector configuration was not found."
    }

    $connectorType = [string]$connectorNode.connectorType
    $actionType = [string]$connectorNode.actionType
    $oldConnectionId = [string]$connectorNode.connectionId
    $oldOperationId = [string]$connectorNode.operationId

    if ($connectorType -ne "wssoapclientsdk") {
        throw @"
UPDATE BLOCKED.

Connector type is not currently proven for set-connector.

Actual:
$connectorType

Currently proven:
wssoapclientsdk
"@
    }

    if ($actionType -ne "EXECUTE") {
        throw @"
UPDATE BLOCKED.

Connector actionType is not currently proven.

Actual:
$actionType

Currently proven:
EXECUTE
"@
    }

    # ========================================================
    # STEP 4 - Resolve current pair
    # ========================================================

    Write-Host "STEP 4 - Resolve current connector pair"
    Write-Host "======================================="

    $oldConnection = Get-BoomiComponentInfo `
        -ComponentId $oldConnectionId

    $oldOperation = Get-BoomiComponentInfo `
        -ComponentId $oldOperationId

    Write-Host "Shape          : $Shape"
    Write-Host "Display Name   : $([string]$shapeNode.userlabel)"
    Write-Host "Connector Type : $connectorType"
    Write-Host "Action Type    : $actionType"
    Write-Host ""
    Write-Host "Current Connection:"
    Write-Host "  Name    : $($oldConnection.Name)"
    Write-Host "  ID      : $($oldConnection.Id)"
    Write-Host "  Type    : $($oldConnection.Type)"
    Write-Host "  Folder  : $($oldConnection.Folder)"
    Write-Host ""
    Write-Host "Current Operation:"
    Write-Host "  Name    : $($oldOperation.Name)"
    Write-Host "  ID      : $($oldOperation.Id)"
    Write-Host "  Type    : $($oldOperation.Type)"
    Write-Host "  Folder  : $($oldOperation.Folder)"
    Write-Host ""

    # ========================================================
    # STEP 5 - Validate target Connection
    # ========================================================

    Write-Host "STEP 5 - Validate target Connection"
    Write-Host "==================================="

    $targetConnectionResponse = Get-BoomiComponentXml `
        -ComponentId $TargetConnectionId

    [xml]$targetConnectionXml = $targetConnectionResponse.Content
    $targetConnection = $targetConnectionXml.Component

    if ($targetConnection.componentId -ne $TargetConnectionId) {
        throw "UPDATE BLOCKED: Target Connection ID mismatch."
    }

    if ($targetConnection.type -ne "connector-settings") {
        throw "UPDATE BLOCKED: Target Connection is not type 'connector-settings'."
    }

    if ($targetConnection.subType -ne "wssoapclientsdk") {
        throw @"
UPDATE BLOCKED.

Target Connection subType is incompatible.

Actual:
$($targetConnection.subType)

Required:
wssoapclientsdk
"@
    }

    Write-Host "Target Connection:"
    Write-Host "  Name    : $($targetConnection.name)"
    Write-Host "  ID      : $($targetConnection.componentId)"
    Write-Host "  Type    : $($targetConnection.type)"
    Write-Host "  SubType : $($targetConnection.subType)"
    Write-Host "  Folder  : $($targetConnection.folderFullPath)"
    Write-Host ""

    # ========================================================
    # STEP 6 - Validate target Operation
    # ========================================================

    Write-Host "STEP 6 - Validate target Operation"
    Write-Host "=================================="

    $targetOperationResponse = Get-BoomiComponentXml `
        -ComponentId $TargetOperationId

    [xml]$targetOperationXml = $targetOperationResponse.Content
    $targetOperation = $targetOperationXml.Component

    if ($targetOperation.componentId -ne $TargetOperationId) {
        throw "UPDATE BLOCKED: Target Operation ID mismatch."
    }

    $operationMetadata = Get-BoomiSoapOperationMetadata `
        -Xml $targetOperationXml

    if ($operationMetadata.SubType -ne "wssoapclientsdk") {
        throw "UPDATE BLOCKED: Target Operation subType is incompatible."
    }

    if ($operationMetadata.OperationType -ne "EXECUTE") {
        throw "UPDATE BLOCKED: Target Operation operationType is not EXECUTE."
    }

    if ($operationMetadata.RequestProfileType -ne "xml") {
        throw "UPDATE BLOCKED: Target Operation requestProfileType is not xml."
    }

    if ($operationMetadata.ResponseProfileType -ne "xml") {
        throw "UPDATE BLOCKED: Target Operation responseProfileType is not xml."
    }

    Write-Host "Target Operation:"
    Write-Host "  Name                 : $($targetOperation.name)"
    Write-Host "  ID                   : $($targetOperation.componentId)"
    Write-Host "  Type                 : $($targetOperation.type)"
    Write-Host "  SubType              : $($operationMetadata.SubType)"
    Write-Host "  operationType        : $($operationMetadata.OperationType)"
    Write-Host "  requestProfileType   : $($operationMetadata.RequestProfileType)"
    Write-Host "  responseProfileType  : $($operationMetadata.ResponseProfileType)"
    Write-Host "  Folder               : $($targetOperation.folderFullPath)"
    Write-Host ""

    if (
        $oldConnectionId -eq $TargetConnectionId -and
        $oldOperationId -eq $TargetOperationId
    ) {
        Write-Host "NO CHANGE REQUIRED."
        Write-Host "The connector already points to the requested Connection and Operation."
        return
    }

    # ========================================================
    # STEP 7 - Snapshot topology and connector references
    # ========================================================

    $originalShapes = @(
        $sourceXml.SelectNodes(
            "//*[local-name()='shape']"
        ) |
        ForEach-Object {
            "$([string]$_.name)|$([string]$_.shapetype)"
        } |
        Sort-Object
    )

    $originalConnectors = @(
        Get-BoomiConnectorReferenceSnapshot `
            -Xml $sourceXml
    )

    # ========================================================
    # STEP 8 - Backup
    # ========================================================

    $backupPath = Save-BoomiBackup `
        -ComponentName ([string]$source.name) `
        -XmlContent $sourceResponse.Content `
        -Reason "before_set_connector"

    Write-Host "STEP 8 - Backup"
    Write-Host "==============="
    Write-Host "Authoritative pre-update XML:"
    Write-Host "  $backupPath"
    Write-Host ""

    # ========================================================
    # STEP 9 - Modify ONLY connectionId / operationId
    # ========================================================

    $connectorNode.SetAttribute(
        "connectionId",
        $TargetConnectionId
    )

    $connectorNode.SetAttribute(
        "operationId",
        $TargetOperationId
    )

    $safeName = Get-BoomiSafeFileName `
        -Value ([string]$source.name)

    $previewPath = Join-Path `
        "$script:WorkspaceRoot\templates" `
        "preview_set_connector_${safeName}_${Shape}.xml"

    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
    $settings.Indent = $false
    $settings.OmitXmlDeclaration = $false

    $writer = [System.Xml.XmlWriter]::Create(
        $previewPath,
        $settings
    )

    try {
        $sourceXml.Save($writer)
    }
    finally {
        $writer.Close()
    }

    # ========================================================
    # STEP 10 - Preview validation
    # ========================================================

    [xml]$previewXml = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $previewShape = $previewXml.SelectSingleNode(
        "//*[local-name()='shape'][@name='$Shape']"
    )

    if (-not $previewShape) {
        throw "UPDATE BLOCKED: Preview target shape is missing."
    }

    if ([string]$previewShape.shapetype -ne "connectoraction") {
        throw "UPDATE BLOCKED: Preview target is no longer connectoraction."
    }

    $previewConnector = $previewShape.SelectSingleNode(
        "./*[local-name()='configuration']/*[local-name()='connectoraction']"
    )

    if (-not $previewConnector) {
        throw "UPDATE BLOCKED: Preview connector configuration is missing."
    }

    if ([string]$previewConnector.connectionId -ne $TargetConnectionId) {
        throw "UPDATE BLOCKED: Preview connectionId validation failed."
    }

    if ([string]$previewConnector.operationId -ne $TargetOperationId) {
        throw "UPDATE BLOCKED: Preview operationId validation failed."
    }

    if ([string]$previewConnector.connectorType -ne $connectorType) {
        throw "UPDATE BLOCKED: Preview connectorType changed."
    }

    if ([string]$previewConnector.actionType -ne $actionType) {
        throw "UPDATE BLOCKED: Preview actionType changed."
    }

    $previewShapes = @(
        $previewXml.SelectNodes(
            "//*[local-name()='shape']"
        ) |
        ForEach-Object {
            "$([string]$_.name)|$([string]$_.shapetype)"
        } |
        Sort-Object
    )

    $shapeDiff = @(
        Compare-Object `
            -ReferenceObject $originalShapes `
            -DifferenceObject $previewShapes
    )

    if ($shapeDiff.Count -ne 0) {
        throw "UPDATE BLOCKED: Shape topology changed unexpectedly."
    }

    $previewConnectors = @(
        Get-BoomiConnectorReferenceSnapshot `
            -Xml $previewXml
    )

    $expectedConnectors = New-Object System.Collections.Generic.List[string]

    foreach ($item in $originalConnectors) {

        $parts = $item -split "\|", 5

        if ($parts[0] -eq $Shape) {

            $expectedConnectors.Add(
                "$Shape|$connectorType|$actionType|$TargetConnectionId|$TargetOperationId"
            )
        }
        else {
            $expectedConnectors.Add($item)
        }
    }

    $connectorDiff = @(
        Compare-Object `
            -ReferenceObject @($expectedConnectors | Sort-Object) `
            -DifferenceObject @($previewConnectors | Sort-Object)
    )

    if ($connectorDiff.Count -ne 0) {
        throw "UPDATE BLOCKED: Unexpected connector reference changes detected."
    }

    Write-Host "STEP 10 - Preview validation"
    Write-Host "============================"
    Write-Host "Target shape        : OK"
    Write-Host "connectionId        : OK"
    Write-Host "operationId         : OK"
    Write-Host "connectorType       : OK"
    Write-Host "actionType          : OK"
    Write-Host "Shape topology      : OK"
    Write-Host "Other connectors    : OK"
    Write-Host ""
    Write-Host "Preview:"
    Write-Host "  $previewPath"
    Write-Host ""

    # ========================================================
    # STEP 11 - Confirmation
    # ========================================================

    Write-Host "CONNECTOR UPDATE"
    Write-Host "================"
    Write-Host ""
    Write-Host "Process:"
    Write-Host "  $($source.name)"
    Write-Host "  $($source.componentId)"
    Write-Host ""
    Write-Host "Shape:"
    Write-Host "  $Shape"
    Write-Host ""
    Write-Host "Connection FROM:"
    Write-Host "  $($oldConnection.Name)"
    Write-Host "  $oldConnectionId"
    Write-Host ""
    Write-Host "Connection TO:"
    Write-Host "  $($targetConnection.name)"
    Write-Host "  $TargetConnectionId"
    Write-Host ""
    Write-Host "Operation FROM:"
    Write-Host "  $($oldOperation.Name)"
    Write-Host "  $oldOperationId"
    Write-Host ""
    Write-Host "Operation TO:"
    Write-Host "  $($targetOperation.name)"
    Write-Host "  $TargetOperationId"
    Write-Host ""
    Write-Host "ONLY connectionId and operationId"
    Write-Host "are intended to change."
    Write-Host ""
    Write-Host "No deployment or execution will occur."
    Write-Host ""

    $confirmation = Read-Host "Type UPDATE exactly to continue"

    if ($confirmation -cne "UPDATE") {
        Write-Host ""
        Write-Host "UPDATE cancelled. No Boomi write was performed."
        return
    }

    # ========================================================
    # STEP 12 - Component UPDATE
    # ========================================================

    $updatePayload = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $writeHeaders = Get-BoomiWriteHeaders

    Write-Host ""
    Write-Host "STEP 12 - Updating Connector reference..."
    Write-Host "========================================="

    try {

        $updateResponse = Invoke-WebRequest `
            -Method Post `
            -Uri "$script:BaseUrl/Component/$Id/update" `
            -Headers $writeHeaders `
            -Body ([Text.Encoding]::UTF8.GetBytes($updatePayload)) `
            -UseBasicParsing
    }
    catch {

        Write-Host ""
        Write-Host "CONNECTOR UPDATE FAILED."
        Write-Host "Do not retry automatically."
        throw
    }

    Write-Host "Boomi accepted the Component UPDATE."
    Write-Host ""

    # ========================================================
    # STEP 13 - Authoritative verification
    # ========================================================

    Write-Host "STEP 13 - Verify authoritative result"
    Write-Host "====================================="

    $verifyResponse = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$verifyXml = $verifyResponse.Content
    $actual = $verifyXml.Component

    $actualShape = $verifyXml.SelectSingleNode(
        "//*[local-name()='shape'][@name='$Shape']"
    )

    $failed = $false

    if ($actual.componentId -eq $Id) {
        Write-Host "Component ID      : OK"
    }
    else {
        Write-Host "Component ID      : FAILED"
        $failed = $true
    }

    if (
        [string]$actual.folderFullPath -ceq
        [string]$component.folderFullPath
    ) {
        Write-Host "Safety folder     : OK"
    }
    else {
        Write-Host "Safety folder     : FAILED"
        Write-Host "Expected        : $($component.folderFullPath)"
        Write-Host "Actual          : $($actual.folderFullPath)"
        $failed = $true
    }

    if (-not $actualShape) {

        Write-Host "Target shape      : FAILED"
        $failed = $true
    }
    else {

        $actualConnector = $actualShape.SelectSingleNode(
            "./*[local-name()='configuration']/*[local-name()='connectoraction']"
        )

        if (-not $actualConnector) {

            Write-Host "Connector config  : FAILED"
            $failed = $true
        }
        else {

            if ([string]$actualConnector.connectionId -eq $TargetConnectionId) {
                Write-Host "connectionId      : OK"
            }
            else {
                Write-Host "connectionId      : FAILED"
                $failed = $true
            }

            if ([string]$actualConnector.operationId -eq $TargetOperationId) {
                Write-Host "operationId       : OK"
            }
            else {
                Write-Host "operationId       : FAILED"
                $failed = $true
            }

            if ([string]$actualConnector.connectorType -eq $connectorType) {
                Write-Host "connectorType     : OK"
            }
            else {
                Write-Host "connectorType     : FAILED"
                $failed = $true
            }

            if ([string]$actualConnector.actionType -eq $actionType) {
                Write-Host "actionType        : OK"
            }
            else {
                Write-Host "actionType        : FAILED"
                $failed = $true
            }
        }
    }

    $actualShapes = @(
        $verifyXml.SelectNodes(
            "//*[local-name()='shape']"
        ) |
        ForEach-Object {
            "$([string]$_.name)|$([string]$_.shapetype)"
        } |
        Sort-Object
    )

    $actualShapeDiff = @(
        Compare-Object `
            -ReferenceObject $originalShapes `
            -DifferenceObject $actualShapes
    )

    if ($actualShapeDiff.Count -eq 0) {
        Write-Host "Shape topology    : OK"
    }
    else {
        Write-Host "Shape topology    : FAILED"
        $failed = $true
    }

    if (-not $failed) {

        $resolvedConnection = Get-BoomiComponentInfo `
            -ComponentId $TargetConnectionId

        $resolvedOperation = Get-BoomiComponentInfo `
            -ComponentId $TargetOperationId

        Write-Host "Resolved Connection : $($resolvedConnection.Name)"
        Write-Host "Resolved Operation  : $($resolvedOperation.Name)"
    }

    # ========================================================
    # STEP 14 - Save authoritative result
    # ========================================================

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $verifiedPath = Join-Path `
        "$script:WorkspaceRoot\exports" `
        "${timestamp}_verified_set_connector_${safeName}_${Shape}.xml"

    Write-BoomiUtf8File `
        -Path $verifiedPath `
        -Content $verifyResponse.Content

    Write-Host ""
    Write-Host "Authoritative post-update XML:"
    Write-Host "  $verifiedPath"
    Write-Host ""

    if ($failed) {

        Write-Host "RESULT: UPDATE REQUIRES INVESTIGATION"
        Write-Host "Do NOT rerun automatically."
    }
    else {

        Write-Host "RESULT: CONNECTOR UPDATE VERIFIED SUCCESSFULLY"
        Write-Host ""
        Write-Host "New Version:"
        Write-Host "  $($actual.version)"
        Write-Host ""
        Write-Host "No deployment or execution was performed."
    }
}