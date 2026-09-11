# ============================================================
# Boomi.ProcessCall.ps1
# boomi-cli v1 SAFE Process Call reference update
#
# HARD SAFETY BOUNDARY:
#   Write access is controlled by the external CLI
#   write policy.
#
# Capability:
#   Set-BoomiProcessCallTarget
#
# Changes ONLY:
#   configuration/processcall/@processId
#
# Does NOT:
#   - modify the target subprocess
#   - modify Display Name
#   - modify abort/wait
#   - modify parameters
#   - modify return paths
#   - add/remove shapes
#   - deploy
#   - execute
#   - delete
# ============================================================


function Get-BoomiProcessCallSnapshot {

    param(
        [Parameter(Mandatory=$true)]
        [xml]$Xml
    )

    $result = New-Object System.Collections.Generic.List[string]

    $shapes = @(
        $Xml.SelectNodes(
            "//*[local-name()='shape'][@shapetype='processcall']"
        )
    )

    foreach ($shape in $shapes) {

        $node = $shape.SelectSingleNode(
            "./*[local-name()='configuration']/*[local-name()='processcall']"
        )

        if ($node) {

            $result.Add(
                "$([string]$shape.name)|$([string]$node.processId)"
            )
        }
    }

    return @($result | Sort-Object)
}


function Set-BoomiProcessCallTarget {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id,

        [Parameter(Mandatory=$true)]
        [string]$Shape,

        [Parameter(Mandatory=$true)]
        [string]$TargetProcessId
    )

    Write-Host ""
    Write-Host "SAFE UPDATE - Process Call Target"
    Write-Host "================================="
    Write-Host ""

    # ========================================================
    # STEP 1 - GET authoritative process to modify
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
    # STEP 3 - Find exact Process Call shape
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

    if ($shapeType -ne "processcall") {
        throw "UPDATE BLOCKED: Shape '$Shape' is '$shapeType', not 'processcall'."
    }

    $processCallNode = $shapeNode.SelectSingleNode(
        "./*[local-name()='configuration']/*[local-name()='processcall']"
    )

    if (-not $processCallNode) {
        throw "UPDATE BLOCKED: Process Call configuration was not found."
    }

    $oldProcessId = [string]$processCallNode.processId

    if ([string]::IsNullOrWhiteSpace($oldProcessId)) {
        throw "UPDATE BLOCKED: Current Process Call contains no processId."
    }

    # ========================================================
    # STEP 4 - Resolve current target
    # ========================================================

    Write-Host "STEP 4 - Resolve current target"
    Write-Host "==============================="

    $oldTarget = Get-BoomiComponentInfo `
        -ComponentId $oldProcessId

    Write-Host "Shape        : $Shape"
    Write-Host "Display Name : $([string]$shapeNode.userlabel)"
    Write-Host ""
    Write-Host "Current target:"
    Write-Host "  Name    : $($oldTarget.Name)"
    Write-Host "  ID      : $($oldTarget.Id)"
    Write-Host "  Type    : $($oldTarget.Type)"
    Write-Host "  Folder  : $($oldTarget.Folder)"
    Write-Host "  Version : $($oldTarget.Version)"
    Write-Host ""

    # ========================================================
    # STEP 5 - Validate new target
    # ========================================================

    Write-Host "STEP 5 - Validate new target"
    Write-Host "============================"

    $targetResponse = Get-BoomiComponentXml `
        -ComponentId $TargetProcessId

    [xml]$targetXml = $targetResponse.Content
    $target = $targetXml.Component

    if ($target.componentId -ne $TargetProcessId) {
        throw "UPDATE BLOCKED: Target Component ID mismatch."
    }

    if ($target.type -ne "process") {
        throw "UPDATE BLOCKED: Target component is not a process."
    }

    Write-Host "New target:"
    Write-Host "  Name    : $($target.name)"
    Write-Host "  ID      : $($target.componentId)"
    Write-Host "  Type    : $($target.type)"
    Write-Host "  Folder  : $($target.folderFullPath)"
    Write-Host "  Version : $($target.version)"
    Write-Host ""

    if ($oldProcessId -eq $TargetProcessId) {
        Write-Host "NO CHANGE REQUIRED."
        Write-Host "The Process Call already points to the requested target."
        return
    }

    # ========================================================
    # STEP 6 - Snapshot original process
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

    $originalProcessCalls = @(
        Get-BoomiProcessCallSnapshot `
            -Xml $sourceXml
    )

    # ========================================================
    # STEP 7 - Backup authoritative current XML
    # ========================================================

    $backupPath = Save-BoomiBackup `
        -ComponentName ([string]$source.name) `
        -XmlContent $sourceResponse.Content `
        -Reason "before_set_process_call"

    Write-Host "STEP 7 - Backup"
    Write-Host "==============="
    Write-Host "Authoritative pre-update XML:"
    Write-Host "  $backupPath"
    Write-Host ""

    # ========================================================
    # STEP 8 - Modify ONLY processId locally
    # ========================================================

    $processCallNode.SetAttribute(
        "processId",
        $TargetProcessId
    )

    $safeName = Get-BoomiSafeFileName `
        -Value ([string]$source.name)

    $previewPath = Join-Path `
        "$script:WorkspaceRoot\templates" `
        "preview_set_process_call_${safeName}_${Shape}.xml"

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

    if ([string]$previewShape.shapetype -ne "processcall") {
        throw "UPDATE BLOCKED: Preview target is no longer a Process Call."
    }

    $previewProcessCall = $previewShape.SelectSingleNode(
        "./*[local-name()='configuration']/*[local-name()='processcall']"
    )

    if (-not $previewProcessCall) {
        throw "UPDATE BLOCKED: Preview Process Call configuration is missing."
    }

    if ([string]$previewProcessCall.processId -ne $TargetProcessId) {
        throw "UPDATE BLOCKED: Preview processId validation failed."
    }

    # Verify shape topology is unchanged.
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
        throw "UPDATE BLOCKED: Process shape topology changed unexpectedly."
    }

    # Verify all OTHER Process Call targets remain unchanged.
    $previewProcessCalls = @(
        Get-BoomiProcessCallSnapshot `
            -Xml $previewXml
    )

    $expectedProcessCalls = New-Object System.Collections.Generic.List[string]

    foreach ($item in $originalProcessCalls) {

        $parts = $item -split "\|", 2

        if ($parts[0] -eq $Shape) {
            $expectedProcessCalls.Add(
                "$Shape|$TargetProcessId"
            )
        }
        else {
            $expectedProcessCalls.Add($item)
        }
    }

    $processCallDiff = @(
        Compare-Object `
            -ReferenceObject @($expectedProcessCalls | Sort-Object) `
            -DifferenceObject @($previewProcessCalls | Sort-Object)
    )

    if ($processCallDiff.Count -ne 0) {
        throw "UPDATE BLOCKED: Unexpected Process Call reference changes detected."
    }

    Write-Host "STEP 9 - Preview validation"
    Write-Host "==========================="
    Write-Host "Target shape      : OK"
    Write-Host "New processId     : OK"
    Write-Host "Shape topology    : OK"
    Write-Host "Other ProcessCall : OK"
    Write-Host ""
    Write-Host "Preview:"
    Write-Host "  $previewPath"
    Write-Host ""

    # ========================================================
    # STEP 10 - Explicit confirmation
    # ========================================================

    Write-Host "PROCESS CALL UPDATE"
    Write-Host "==================="
    Write-Host ""
    Write-Host "Process being modified:"
    Write-Host "  $($source.name)"
    Write-Host "  $($source.componentId)"
    Write-Host ""
    Write-Host "Shape:"
    Write-Host "  $Shape"
    Write-Host ""
    Write-Host "FROM:"
    Write-Host "  $($oldTarget.Name)"
    Write-Host "  $oldProcessId"
    Write-Host ""
    Write-Host "TO:"
    Write-Host "  $($target.name)"
    Write-Host "  $TargetProcessId"
    Write-Host ""
    Write-Host "ONLY configuration/processcall/@processId"
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
    Write-Host "STEP 11 - Updating Process Call..."
    Write-Host "=================================="

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
        Write-Host "PROCESS CALL UPDATE FAILED."
        Write-Host "Do not retry automatically."
        throw
    }

    Write-Host "Boomi accepted the Component UPDATE."
    Write-Host ""

    # ========================================================
    # STEP 12 - Authoritative GET verification
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
        Write-Host "Component ID    : OK"
    }
    else {
        Write-Host "Component ID    : FAILED"
        $failed = $true
    }

    if (
        [string]$actual.folderFullPath -ceq
        [string]$component.folderFullPath
    ) {
        Write-Host "Safety folder   : OK"
    }
    else {
        Write-Host "Safety folder   : FAILED"
        Write-Host "Expected        : $($component.folderFullPath)"
        Write-Host "Actual          : $($actual.folderFullPath)"
        $failed = $true
    }

    if ($actualTargetShapes.Count -ne 1) {

        Write-Host "Target shape    : FAILED"
        $failed = $true
    }
    else {

        $actualShape = $actualTargetShapes[0]

        if ([string]$actualShape.shapetype -eq "processcall") {
            Write-Host "Shape type      : OK"
        }
        else {
            Write-Host "Shape type      : FAILED"
            $failed = $true
        }

        $actualProcessCall = $actualShape.SelectSingleNode(
            "./*[local-name()='configuration']/*[local-name()='processcall']"
        )

        if (-not $actualProcessCall) {

            Write-Host "Process Call cfg: FAILED"
            $failed = $true
        }
        elseif ([string]$actualProcessCall.processId -eq $TargetProcessId) {

            Write-Host "New processId   : OK"
        }
        else {

            Write-Host "New processId   : FAILED"
            Write-Host "Actual          : $([string]$actualProcessCall.processId)"
            $failed = $true
        }
    }

    # Verify shape topology after write.
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
        Write-Host "Shape topology  : OK"
    }
    else {
        Write-Host "Shape topology  : FAILED"
        $failed = $true
    }

    # Resolve the resulting target name.
    if (-not $failed) {

        $resolvedTarget = Get-BoomiComponentInfo `
            -ComponentId $TargetProcessId

        Write-Host "Resolved target : $($resolvedTarget.Name)"
    }

    # ========================================================
    # STEP 13 - Save authoritative result
    # ========================================================

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $verifiedPath = Join-Path `
        "$script:WorkspaceRoot\exports" `
        "${timestamp}_verified_set_process_call_${safeName}_${Shape}.xml"

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

        Write-Host "RESULT: PROCESS CALL UPDATE VERIFIED SUCCESSFULLY"
        Write-Host ""
        Write-Host "New Version:"
        Write-Host "  $($actual.version)"
        Write-Host ""
        Write-Host "No deployment or execution was performed."
    }
}