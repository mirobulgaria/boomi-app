# ============================================================
# Boomi.Map.ps1
# boomi-cli v1 SAFE Map reference update
#
# HARD SAFETY BOUNDARY:
#   Write access is controlled by the external CLI
#   write policy.
#
# Capability:
#   Set-BoomiMapTarget
#
# Changes ONLY:
#   configuration/map/@mapId
#
# Does NOT:
#   - modify source or target Map component
#   - modify Display Name
#   - add/remove shapes
#   - modify other component references
#   - deploy
#   - execute
#   - delete
# ============================================================


function Get-BoomiMapReferenceSnapshot {

    param(
        [Parameter(Mandatory=$true)]
        [xml]$Xml
    )

    $result = New-Object System.Collections.Generic.List[string]

    $shapes = @(
        $Xml.SelectNodes(
            "//*[local-name()='shape'][@shapetype='map']"
        )
    )

    foreach ($shape in $shapes) {

        $node = $shape.SelectSingleNode(
            "./*[local-name()='configuration']/*[local-name()='map']"
        )

        if ($node) {
            $result.Add(
                "$([string]$shape.name)|$([string]$node.mapId)"
            )
        }
    }

    return @($result | Sort-Object)
}


function Set-BoomiMapTarget {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id,

        [Parameter(Mandatory=$true)]
        [string]$Shape,

        [Parameter(Mandatory=$true)]
        [string]$TargetMapId
    )

    Write-Host ""
    Write-Host "SAFE UPDATE - Map Target"
    Write-Host "========================"
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
    # STEP 2 - Hard safety boundary
    # ========================================================

    Assert-BoomiWriteFolder `
        -Folder ([string]$source.folderFullPath)

    Write-Host "STEP 2 - Safety boundary"
    Write-Host "========================"
    Write-Host "Write folder : OK"
    Write-Host ""

    # ========================================================
    # STEP 3 - Locate exact Map shape
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

    if ($shapeType -ne "map") {
        throw "UPDATE BLOCKED: Shape '$Shape' is '$shapeType', not 'map'."
    }

    $mapNode = $shapeNode.SelectSingleNode(
        "./*[local-name()='configuration']/*[local-name()='map']"
    )

    if (-not $mapNode) {
        throw "UPDATE BLOCKED: Map configuration was not found."
    }

    $oldMapId = [string]$mapNode.mapId

    if ([string]::IsNullOrWhiteSpace($oldMapId)) {
        throw "UPDATE BLOCKED: Current Map shape contains no mapId."
    }

    # ========================================================
    # STEP 4 - Resolve current Map
    # ========================================================

    Write-Host "STEP 4 - Resolve current Map"
    Write-Host "============================"

    $oldMap = Get-BoomiComponentInfo `
        -ComponentId $oldMapId

    Write-Host "Shape        : $Shape"
    Write-Host "Display Name : $([string]$shapeNode.userlabel)"
    Write-Host ""
    Write-Host "Current Map:"
    Write-Host "  Name    : $($oldMap.Name)"
    Write-Host "  ID      : $($oldMap.Id)"
    Write-Host "  Type    : $($oldMap.Type)"
    Write-Host "  Folder  : $($oldMap.Folder)"
    Write-Host "  Version : $($oldMap.Version)"
    Write-Host ""

    # ========================================================
    # STEP 5 - Validate new target Map
    # ========================================================

    Write-Host "STEP 5 - Validate new Map"
    Write-Host "========================="

    $targetResponse = Get-BoomiComponentXml `
        -ComponentId $TargetMapId

    [xml]$targetXml = $targetResponse.Content
    $target = $targetXml.Component

    if ($target.componentId -ne $TargetMapId) {
        throw "UPDATE BLOCKED: Target Map Component ID mismatch."
    }

    if ($target.type -ne "transform.map") {
        throw "UPDATE BLOCKED: Target component is not type 'transform.map'."
    }

    Write-Host "New Map:"
    Write-Host "  Name    : $($target.name)"
    Write-Host "  ID      : $($target.componentId)"
    Write-Host "  Type    : $($target.type)"
    Write-Host "  Folder  : $($target.folderFullPath)"
    Write-Host "  Version : $($target.version)"
    Write-Host ""

    if ($oldMapId -eq $TargetMapId) {
        Write-Host "NO CHANGE REQUIRED."
        Write-Host "The Map shape already points to the requested Map."
        return
    }

    # ========================================================
    # STEP 6 - Snapshot original topology and Map references
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

    $originalMaps = @(
        Get-BoomiMapReferenceSnapshot `
            -Xml $sourceXml
    )

    # ========================================================
    # STEP 7 - Backup
    # ========================================================

    $backupPath = Save-BoomiBackup `
        -ComponentName ([string]$source.name) `
        -XmlContent $sourceResponse.Content `
        -Reason "before_set_map"

    Write-Host "STEP 7 - Backup"
    Write-Host "==============="
    Write-Host "Authoritative pre-update XML:"
    Write-Host "  $backupPath"
    Write-Host ""

    # ========================================================
    # STEP 8 - Change ONLY mapId locally
    # ========================================================

    $mapNode.SetAttribute(
        "mapId",
        $TargetMapId
    )

    $safeName = Get-BoomiSafeFileName `
        -Value ([string]$source.name)

    $previewPath = Join-Path `
        "$script:WorkspaceRoot\templates" `
        "preview_set_map_${safeName}_${Shape}.xml"

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
    # STEP 9 - Validate preview
    # ========================================================

    [xml]$previewXml = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $previewTargetShapes = @(
        $previewXml.SelectNodes(
            "//*[local-name()='shape'][@name='$Shape']"
        )
    )

    if ($previewTargetShapes.Count -ne 1) {
        throw "UPDATE BLOCKED: Preview target shape validation failed."
    }

    $previewShape = $previewTargetShapes[0]

    if ([string]$previewShape.shapetype -ne "map") {
        throw "UPDATE BLOCKED: Preview target is no longer a Map shape."
    }

    $previewMap = $previewShape.SelectSingleNode(
        "./*[local-name()='configuration']/*[local-name()='map']"
    )

    if (-not $previewMap) {
        throw "UPDATE BLOCKED: Preview Map configuration is missing."
    }

    if ([string]$previewMap.mapId -ne $TargetMapId) {
        throw "UPDATE BLOCKED: Preview mapId validation failed."
    }

    # Shape topology must remain identical.
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

    # All Map references except the selected shape must remain
    # unchanged.
    $previewMaps = @(
        Get-BoomiMapReferenceSnapshot `
            -Xml $previewXml
    )

    $expectedMaps = New-Object System.Collections.Generic.List[string]

    foreach ($item in $originalMaps) {

        $parts = $item -split "\|", 2

        if ($parts[0] -eq $Shape) {
            $expectedMaps.Add(
                "$Shape|$TargetMapId"
            )
        }
        else {
            $expectedMaps.Add($item)
        }
    }

    $mapDiff = @(
        Compare-Object `
            -ReferenceObject @($expectedMaps | Sort-Object) `
            -DifferenceObject @($previewMaps | Sort-Object)
    )

    if ($mapDiff.Count -ne 0) {
        throw "UPDATE BLOCKED: Unexpected Map reference changes detected."
    }

    Write-Host "STEP 9 - Preview validation"
    Write-Host "==========================="
    Write-Host "Target shape   : OK"
    Write-Host "New mapId      : OK"
    Write-Host "Shape topology : OK"
    Write-Host "Other Maps     : OK"
    Write-Host ""
    Write-Host "Preview:"
    Write-Host "  $previewPath"
    Write-Host ""

    # ========================================================
    # STEP 10 - Explicit confirmation
    # ========================================================

    Write-Host "MAP UPDATE"
    Write-Host "=========="
    Write-Host ""
    Write-Host "Process being modified:"
    Write-Host "  $($source.name)"
    Write-Host "  $($source.componentId)"
    Write-Host ""
    Write-Host "Shape:"
    Write-Host "  $Shape"
    Write-Host ""
    Write-Host "FROM:"
    Write-Host "  $($oldMap.Name)"
    Write-Host "  $oldMapId"
    Write-Host ""
    Write-Host "TO:"
    Write-Host "  $($target.name)"
    Write-Host "  $TargetMapId"
    Write-Host ""
    Write-Host "ONLY configuration/map/@mapId"
    Write-Host "is intended to change."
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
    # STEP 11 - Component UPDATE
    # ========================================================

    $updatePayload = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $writeHeaders = Get-BoomiWriteHeaders

    Write-Host ""
    Write-Host "STEP 11 - Updating Map reference..."
    Write-Host "==================================="

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
        Write-Host "MAP UPDATE FAILED."
        Write-Host "Do not retry automatically."
        throw
    }

    Write-Host "Boomi accepted the Component UPDATE."
    Write-Host ""

    # ========================================================
    # STEP 12 - Authoritative verification
    # ========================================================

    Write-Host "STEP 12 - Verify authoritative result"
    Write-Host "====================================="

    $verifyResponse = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$verifyXml = $verifyResponse.Content
    $actual = $verifyXml.Component

    $actualTargetShapes = @(
        $verifyXml.SelectNodes(
            "//*[local-name()='shape'][@name='$Shape']"
        )
    )

    $failed = $false

    if ($actual.componentId -eq $Id) {
        Write-Host "Component ID   : OK"
    }
    else {
        Write-Host "Component ID   : FAILED"
        $failed = $true
    }

    if (
        [string]$actual.folderFullPath -ceq
        [string]$component.folderFullPath
    ) {
        Write-Host "Safety folder  : OK"
    }
    else {
        Write-Host "Safety folder  : FAILED"
        Write-Host "Expected        : $($component.folderFullPath)"
        Write-Host "Actual          : $($actual.folderFullPath)"
        $failed = $true
    }

    if ($actualTargetShapes.Count -ne 1) {

        Write-Host "Target shape   : FAILED"
        $failed = $true
    }
    else {

        $actualShape = $actualTargetShapes[0]

        if ([string]$actualShape.shapetype -eq "map") {
            Write-Host "Shape type     : OK"
        }
        else {
            Write-Host "Shape type     : FAILED"
            $failed = $true
        }

        $actualMap = $actualShape.SelectSingleNode(
            "./*[local-name()='configuration']/*[local-name()='map']"
        )

        if (-not $actualMap) {

            Write-Host "Map config     : FAILED"
            $failed = $true
        }
        elseif ([string]$actualMap.mapId -eq $TargetMapId) {

            Write-Host "New mapId      : OK"
        }
        else {

            Write-Host "New mapId      : FAILED"
            Write-Host "Actual         : $([string]$actualMap.mapId)"
            $failed = $true
        }
    }

    # Verify topology again.
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
        Write-Host "Shape topology : OK"
    }
    else {
        Write-Host "Shape topology : FAILED"
        $failed = $true
    }

    if (-not $failed) {

        $resolvedMap = Get-BoomiComponentInfo `
            -ComponentId $TargetMapId

        Write-Host "Resolved Map   : $($resolvedMap.Name)"
    }

    # ========================================================
    # STEP 13 - Save authoritative result
    # ========================================================

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $verifiedPath = Join-Path `
        "$script:WorkspaceRoot\exports" `
        "${timestamp}_verified_set_map_${safeName}_${Shape}.xml"

    [IO.File]::WriteAllText(
        $verifiedPath,
        $verifyResponse.Content,
        [Text.UTF8Encoding]::new($false)
    )

    Write-Host ""
    Write-Host "Authoritative post-update XML:"
    Write-Host "  $verifiedPath"
    Write-Host ""

    if ($failed) {

        Write-Host "RESULT: UPDATE REQUIRES INVESTIGATION"
        Write-Host "Do NOT rerun automatically."
    }
    else {

        Write-Host "RESULT: MAP UPDATE VERIFIED SUCCESSFULLY"
        Write-Host ""
        Write-Host "New Version:"
        Write-Host "  $($actual.version)"
        Write-Host ""
        Write-Host "No deployment or execution was performed."
    }
}