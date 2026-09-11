# ============================================================
# Boomi.Clone.ps1
# boomi-cli v1 SAFE PROCESS CLONE
#
# HARD SAFETY BOUNDARY:
#   The target folder must be explicitly allowed by the
#   external CLI write policy.
#
# Current capability:
#   Copy-BoomiProcess
#
# Behaviour:
#   - GET authoritative source XML
#   - validate source is a process
#   - resolve target folderId
#   - duplicate protection
#   - preserve process definition and references
#   - remove source identity/version metadata
#   - set new name and target folderId
#   - local preview
#   - explicit CLONE confirmation
#   - Component CREATE
#   - authoritative GET verification
#   - structural/reference comparison
#
# NO deployment.
# NO execution.
# NO delete.
# NO modification of source.
# ============================================================


function Get-BoomiCloneReferenceSnapshot {

    param(
        [Parameter(Mandatory=$true)]
        [xml]$Xml
    )

    $references = New-Object System.Collections.Generic.List[string]

    # Process Calls
    $nodes = @(
        $Xml.SelectNodes(
            "//*[local-name()='processcall'][@processId]"
        )
    )

    foreach ($node in $nodes) {
        $references.Add(
            "processId=$([string]$node.processId)"
        )
    }

    # Maps
    $nodes = @(
        $Xml.SelectNodes(
            "//*[local-name()='map'][@mapId]"
        )
    )

    foreach ($node in $nodes) {
        $references.Add(
            "mapId=$([string]$node.mapId)"
        )
    }

    # Connector references
    $nodes = @(
        $Xml.SelectNodes(
            "//*[local-name()='connectoraction']"
        )
    )

    foreach ($node in $nodes) {

        if (
            -not [string]::IsNullOrWhiteSpace(
                [string]$node.connectionId
            )
        ) {
            $references.Add(
                "connectionId=$([string]$node.connectionId)"
            )
        }

        if (
            -not [string]::IsNullOrWhiteSpace(
                [string]$node.operationId
            )
        ) {
            $references.Add(
                "operationId=$([string]$node.operationId)"
            )
        }
    }

    return @(
        $references |
            Sort-Object
    )
}


function Get-BoomiCloneShapeSnapshot {

    param(
        [Parameter(Mandatory=$true)]
        [xml]$Xml
    )

    $shapes = @(
        $Xml.SelectNodes(
            "//*[local-name()='shape']"
        )
    )

    $snapshot = New-Object System.Collections.Generic.List[string]

    foreach ($shape in $shapes) {

        $snapshot.Add(
            "$([string]$shape.name)|$([string]$shape.shapetype)"
        )
    }

    return @(
        $snapshot |
            Sort-Object
    )
}


function Compare-BoomiStringSets {

    param(
        [Parameter(Mandatory=$true)]
        [object[]]$Expected,

        [Parameter(Mandatory=$true)]
        [object[]]$Actual
    )

    $difference = @(
        Compare-Object `
            -ReferenceObject @($Expected) `
            -DifferenceObject @($Actual)
    )

    return [PSCustomObject]@{
        Equal      = ($difference.Count -eq 0)
        Difference = $difference
    }
}


function Copy-BoomiProcess {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id,

        [Parameter(Mandatory=$true)]
        [string]$Name,

        [Parameter(Mandatory=$true)]
        [string]$Folder
    )

    Write-Host ""
    Write-Host "SAFE CLONE - Process"
    Write-Host "===================="
    Write-Host ""

    # ========================================================
    # STEP 1 - Target safety boundary
    # ========================================================

    Assert-BoomiWriteFolder `
        -Folder $Folder

    Write-Host "Target safety boundary : OK"
    Write-Host ""

    # ========================================================
    # STEP 2 - GET authoritative source
    # ========================================================

    Write-Host "STEP 2 - Read authoritative source"
    Write-Host "=================================="

    $sourceResponse = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$sourceXml = $sourceResponse.Content
    $source = $sourceXml.Component

    Write-Host "Source Name    : $($source.name)"
    Write-Host "Source ID      : $($source.componentId)"
    Write-Host "Source Type    : $($source.type)"
    Write-Host "Source Version : $($source.version)"
    Write-Host "Source Folder  : $($source.folderFullPath)"
    Write-Host "Source Branch  : $($source.branchName)"
    Write-Host ""

    if ($source.componentId -ne $Id) {
        throw "CLONE BLOCKED: Source Component ID mismatch."
    }

    if ($source.type -ne "process") {
        throw "CLONE BLOCKED: Source component is not a process."
    }

    # --------------------------------------------------------
    # IMPORTANT:
    # The source does not need to be inside an allowed
    # write folder. The clone target does.
    #
    # This allows future read-only cloning FROM a real process,
    # while preventing CREATE outside the test harness.
    # --------------------------------------------------------

    # ========================================================
    # STEP 3 - Resolve authoritative target folder
    # ========================================================

    Write-Host "STEP 3 - Resolve target folder"
    Write-Host "=============================="

    $folderInfo = Get-BoomiFolderByFullPath `
        -FullPath $Folder

    if ([string]$folderInfo.fullPath -ne $Folder) {
        throw "CLONE BLOCKED: Resolved target folder mismatch."
    }

    Write-Host "Target Folder    : $($folderInfo.fullPath)"
    Write-Host "Target Folder ID : $($folderInfo.id)"
    Write-Host ""

    # ========================================================
    # STEP 4 - Duplicate protection
    # ========================================================

    Write-Host "STEP 4 - Duplicate protection"
    Write-Host "============================="

    if (Test-BoomiComponentNameExists -Name $Name) {
        throw "CLONE BLOCKED: A component named '$Name' already exists."
    }

    Write-Host "Duplicate check : OK"
    Write-Host ""

    # ========================================================
    # STEP 5 - Snapshot source structure/references
    # ========================================================

    $sourceShapes = @(
        Get-BoomiCloneShapeSnapshot `
            -Xml $sourceXml
    )

    $sourceReferences = @(
        Get-BoomiCloneReferenceSnapshot `
            -Xml $sourceXml
    )

    Write-Host "STEP 5 - Source snapshot"
    Write-Host "========================"
    Write-Host "Shapes     : $($sourceShapes.Count)"
    Write-Host "References : $($sourceReferences.Count)"
    Write-Host ""

    Write-Host "Source shapes:"
    foreach ($item in $sourceShapes) {
        Write-Host "  $item"
    }

    Write-Host ""

    if ($sourceReferences.Count -gt 0) {

        Write-Host "References that will be preserved:"

        foreach ($item in $sourceReferences) {
            Write-Host "  $item"
        }

        Write-Host ""
    }

    # ========================================================
    # STEP 6 - Backup source authoritative XML
    # ========================================================

    $backupPath = Save-BoomiBackup `
        -ComponentName ([string]$source.name) `
        -XmlContent $sourceResponse.Content `
        -Reason "before_clone_source"

    Write-Host "STEP 6 - Source backup"
    Write-Host "======================"
    Write-Host "Source XML backup:"
    Write-Host "  $backupPath"
    Write-Host ""

    # ========================================================
    # STEP 7 - Build clone candidate from authoritative GET XML
    # ========================================================

    # Work on a separate XML object.
    [xml]$cloneXml = $sourceResponse.Content
    $clone = $cloneXml.Component

    # --------------------------------------------------------
    # Remove source identity/system metadata.
    #
    # These attributes were observed on GET responses and
    # identify/version the existing component. They must not
    # identify the source in a CREATE candidate.
    # --------------------------------------------------------

    $attributesToRemove = @(
        "componentId",
        "version",
        "createdDate",
        "createdBy",
        "modifiedDate",
        "modifiedBy",
        "deleted",
        "currentVersion",
        "folderFullPath",
        "folderName",
        "folderId"
    )

    foreach ($attributeName in $attributesToRemove) {

        if ($clone.HasAttribute($attributeName)) {
            $clone.RemoveAttribute($attributeName)
        }
    }

    # --------------------------------------------------------
    # Set new identity inputs.
    # --------------------------------------------------------

    $clone.SetAttribute(
        "name",
        $Name
    )

    $clone.SetAttribute(
        "folderId",
        [string]$folderInfo.id
    )

    # --------------------------------------------------------
    # Branch:
    # preserve source branchId exactly as returned by GET.
    # Do not invent a new branch value.
    # --------------------------------------------------------

    $sourceBranchId = [string]$source.branchId

    if ([string]::IsNullOrWhiteSpace($sourceBranchId)) {
        throw "CLONE BLOCKED: Source GET XML contains no branchId."
    }

    $clone.SetAttribute(
        "branchId",
        $sourceBranchId
    )

    # branchName is response metadata; do not use it as CREATE
    # identity input.
    if ($clone.HasAttribute("branchName")) {
        $clone.RemoveAttribute("branchName")
    }

    # ========================================================
    # STEP 8 - Save local clone preview
    # ========================================================

    $safeTargetName = Get-BoomiSafeFileName `
        -Value $Name

    $previewPath = Join-Path `
        "$script:WorkspaceRoot\templates" `
        "preview_clone_${safeTargetName}.xml"

    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
    $settings.Indent = $false
    $settings.OmitXmlDeclaration = $false

    $writer = [System.Xml.XmlWriter]::Create(
        $previewPath,
        $settings
    )

    try {
        $cloneXml.Save($writer)
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

    $preview = $previewXml.Component

    if ($preview.name -ne $Name) {
        throw "CLONE BLOCKED: Preview target name validation failed."
    }

    if ($preview.type -ne "process") {
        throw "CLONE BLOCKED: Preview component type changed."
    }

    if ($preview.folderId -ne [string]$folderInfo.id) {
        throw "CLONE BLOCKED: Preview target folderId validation failed."
    }

    if (-not [string]::IsNullOrWhiteSpace(
        [string]$preview.componentId
    )) {
        throw "CLONE BLOCKED: Preview still contains source componentId."
    }

    $previewShapes = @(
        Get-BoomiCloneShapeSnapshot `
            -Xml $previewXml
    )

    $previewReferences = @(
        Get-BoomiCloneReferenceSnapshot `
            -Xml $previewXml
    )

    $shapePreviewComparison = Compare-BoomiStringSets `
        -Expected $sourceShapes `
        -Actual $previewShapes

    if (-not $shapePreviewComparison.Equal) {
        throw "CLONE BLOCKED: Preview shape structure differs from source."
    }

    $referencePreviewComparison = Compare-BoomiStringSets `
        -Expected $sourceReferences `
        -Actual $previewReferences

    if (-not $referencePreviewComparison.Equal) {
        throw "CLONE BLOCKED: Preview references differ from source."
    }

    Write-Host "STEP 9 - Preview validation"
    Write-Host "==========================="
    Write-Host "Target name      : OK"
    Write-Host "Target folderId  : OK"
    Write-Host "Source ID removed: OK"
    Write-Host "Shape snapshot   : OK"
    Write-Host "References       : OK"
    Write-Host ""
    Write-Host "Preview:"
    Write-Host "  $previewPath"
    Write-Host ""

    # ========================================================
    # STEP 10 - Explicit confirmation
    # ========================================================

    Write-Host "CLONE OPERATION"
    Write-Host "==============="
    Write-Host ""
    Write-Host "SOURCE:"
    Write-Host "  Name    : $($source.name)"
    Write-Host "  ID      : $($source.componentId)"
    Write-Host "  Version : $($source.version)"
    Write-Host "  Folder  : $($source.folderFullPath)"
    Write-Host ""
    Write-Host "TARGET:"
    Write-Host "  Name    : $Name"
    Write-Host "  Folder  : $Folder"
    Write-Host ""
    Write-Host "The existing process definition and component"
    Write-Host "references will be preserved."
    Write-Host ""
    Write-Host "The source component will NOT be modified."
    Write-Host "No deployment or execution will occur."
    Write-Host ""

    $confirmation = Read-Host "Type CLONE exactly to continue"

    if ($confirmation -cne "CLONE") {
        Write-Host ""
        Write-Host "CLONE cancelled. No Boomi write was performed."
        return
    }

    # ========================================================
    # STEP 11 - CREATE clone
    # ========================================================

    $payload = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $writeHeaders = Get-BoomiWriteHeaders

    Write-Host ""
    Write-Host "STEP 11 - Creating clone..."
    Write-Host "==========================="

    try {

        $createResponse = Invoke-WebRequest `
            -Method Post `
            -Uri "$script:BaseUrl/Component" `
            -Headers $writeHeaders `
            -Body ([Text.Encoding]::UTF8.GetBytes($payload)) `
            -UseBasicParsing
    }
    catch {

        Write-Host ""
        Write-Host "CLONE CREATE FAILED."
        Write-Host "The source component was not modified."
        Write-Host "Do not retry automatically."
        throw
    }

    [xml]$createdXml = $createResponse.Content
    $newId = [string]$createdXml.Component.componentId

    if ([string]::IsNullOrWhiteSpace($newId)) {
        throw "CLONE CREATE returned no componentId. Manual verification required."
    }

    Write-Host "Boomi returned new Component ID:"
    Write-Host "  $newId"
    Write-Host ""

    # ========================================================
    # STEP 12 - Authoritative GET verification
    # ========================================================

    Write-Host "STEP 12 - Verify authoritative clone"
    Write-Host "===================================="

    $verifyResponse = Get-BoomiComponentXml `
        -ComponentId $newId

    [xml]$verifyXml = $verifyResponse.Content
    $actual = $verifyXml.Component

    $actualShapes = @(
        Get-BoomiCloneShapeSnapshot `
            -Xml $verifyXml
    )

    $actualReferences = @(
        Get-BoomiCloneReferenceSnapshot `
            -Xml $verifyXml
    )

    $failed = $false

    if ($actual.componentId -eq $newId) {
        Write-Host "New Component ID : OK"
    }
    else {
        Write-Host "New Component ID : FAILED"
        $failed = $true
    }

    if ($actual.componentId -eq $source.componentId) {
        Write-Host "Identity isolation : FAILED"
        $failed = $true
    }
    else {
        Write-Host "Identity isolation : OK"
    }

    if ($actual.name -eq $Name) {
        Write-Host "Target name        : OK"
    }
    else {
        Write-Host "Target name        : FAILED"
        $failed = $true
    }

    if ($actual.type -eq "process") {
        Write-Host "Component type     : OK"
    }
    else {
        Write-Host "Component type     : FAILED"
        $failed = $true
    }

    if ($actual.folderFullPath -eq $Folder) {
        Write-Host "Target folder      : OK"
    }
    else {
        Write-Host "Target folder      : FAILED"
        Write-Host "Actual folder      : $($actual.folderFullPath)"
        $failed = $true
    }

    $shapeComparison = Compare-BoomiStringSets `
        -Expected $sourceShapes `
        -Actual $actualShapes

    if ($shapeComparison.Equal) {
        Write-Host "Shape structure    : OK ($($actualShapes.Count))"
    }
    else {
        Write-Host "Shape structure    : FAILED"
        $failed = $true
    }

    $referenceComparison = Compare-BoomiStringSets `
        -Expected $sourceReferences `
        -Actual $actualReferences

    if ($referenceComparison.Equal) {
        Write-Host "References         : OK ($($actualReferences.Count))"
    }
    else {
        Write-Host "References         : FAILED"
        $failed = $true
    }

    # ========================================================
    # STEP 13 - Save authoritative clone XML
    # ========================================================

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $verifiedPath = Join-Path `
        "$script:WorkspaceRoot\exports" `
        "${timestamp}_verified_clone_${safeTargetName}.xml"

    [IO.File]::WriteAllText(
        $verifiedPath,
        $verifyResponse.Content,
        [Text.UTF8Encoding]::new($false)
    )

    Write-Host ""
    Write-Host "Authoritative clone XML:"
    Write-Host "  $verifiedPath"
    Write-Host ""

    if ($failed) {

        Write-Host "RESULT: CLONE CREATED, BUT VERIFICATION FAILED"
        Write-Host ""
        Write-Host "Do NOT rerun clone automatically."
        Write-Host "Inspect the created component:"
        Write-Host "  $newId"
    }
    else {

        Write-Host "RESULT: CLONE VERIFIED SUCCESSFULLY"
        Write-Host ""
        Write-Host "Source Component ID:"
        Write-Host "  $($source.componentId)"
        Write-Host ""
        Write-Host "Clone Component ID:"
        Write-Host "  $newId"
        Write-Host ""
        Write-Host "Clone Version:"
        Write-Host "  $($actual.version)"
        Write-Host ""
        Write-Host "No deployment or execution was performed."
    }
}