# ============================================================
# Boomi.Restore.ps1
# boomi-cli - Controlled Component Restore
#
# Purpose:
#   Safely restore an existing soft-deleted Boomi component
#   through the ComponentMetadata API.
#
# SAFETY MODEL:
#   - Component ID is mandatory.
#   - Authoritative ComponentMetadata GET before restore.
#   - Component must be current and deleted.
#   - Target folder must pass configured write policy.
#   - Pre-restore metadata snapshot is saved locally.
#   - Explicit RESTORE confirmation is required.
#   - Restore is sent only through ComponentMetadata.
#   - No automatic retry after a restore request.
#   - Post-restore ComponentMetadata verification is required.
#   - Authoritative Component GET verifies the restored state.
#
# IMPORTANT:
#   This module implements single-component restore only.
# ============================================================


function Get-BoomiRestoreComponentMetadataById {

    param(
        [Parameter(Mandatory=$true)]
        [string]$ComponentId
    )

    if ([string]::IsNullOrWhiteSpace($ComponentId)) {
        throw "RESTORE ERROR: ComponentId is empty."
    }

    try {

        $metadata = Invoke-RestMethod `
            -Method Get `
            -Uri "$script:BaseUrl/ComponentMetadata/$ComponentId" `
            -Headers $script:JsonHeaders `
            -ErrorAction Stop
    }
    catch {

        throw @"
RESTORE ERROR: Failed to retrieve ComponentMetadata.

Component ID:
$ComponentId

No restore was performed by this operation.
"@
    }

    if ($null -eq $metadata) {
        throw "RESTORE ERROR: ComponentMetadata GET returned no object."
    }

    return $metadata
}


function Save-BoomiPreRestoreMetadataSnapshot {

    param(
        [Parameter(Mandatory=$true)]
        [object]$Metadata
    )

    $backupDirectory = Join-Path `
        $script:WorkspaceRoot `
        "backups"

    if (-not (Test-Path -LiteralPath $backupDirectory -PathType Container)) {

        New-Item `
            -ItemType Directory `
            -Force `
            -Path $backupDirectory |
            Out-Null
    }

    $componentId = [string]$Metadata.componentId
    $componentName = [string]$Metadata.name

    if ([string]::IsNullOrWhiteSpace($componentId)) {
        throw "RESTORE ERROR: Metadata snapshot has no componentId."
    }

    if ([string]::IsNullOrWhiteSpace($componentName)) {
        throw "RESTORE ERROR: Metadata snapshot has no component name."
    }

    $safeName = $componentName -replace '[\\/:*?"<>|]', '_'
    $safeName = $safeName -replace '\s+', '_'

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $snapshotPath = Join-Path `
        $backupDirectory `
        ("{0}_before_restore_{1}_{2}.json" -f `
            $timestamp,
            $safeName,
            $componentId)

    $snapshot = [ordered]@{
        capturedAtUtc = [DateTime]::UtcNow.ToString("o")
        componentId = [string]$Metadata.componentId
        version = $Metadata.version
        name = [string]$Metadata.name
        type = [string]$Metadata.type
        deleted = $Metadata.deleted
        currentVersion = $Metadata.currentVersion
        folderName = [string]$Metadata.folderName
        folderId = [string]$Metadata.folderId
        branchName = [string]$Metadata.branchName
        branchId = [string]$Metadata.branchId
        createdDate = [string]$Metadata.createdDate
        createdBy = [string]$Metadata.createdBy
        modifiedDate = [string]$Metadata.modifiedDate
        modifiedBy = [string]$Metadata.modifiedBy
    }

    $json = $snapshot |
        ConvertTo-Json -Depth 10

    [IO.File]::WriteAllText(
        $snapshotPath,
        $json,
        [Text.UTF8Encoding]::new($false)
    )

    if (-not (Test-Path -LiteralPath $snapshotPath -PathType Leaf)) {
        throw "RESTORE ERROR: Pre-restore metadata snapshot was not created."
    }

    return $snapshotPath
}


function Restore-BoomiComponent {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id
    )

    if ([string]::IsNullOrWhiteSpace($Id)) {
        throw "restore requires -Id"
    }

    Write-Host ""
    Write-Host "CONTROLLED COMPONENT RESTORE"
    Write-Host "============================"
    Write-Host ""

    # ========================================================
    # STEP 1 - Authoritative ComponentMetadata GET
    # ========================================================

    Write-Host "STEP 1 - Authoritative ComponentMetadata GET"
    Write-Host "============================================"

    $metadata = Get-BoomiRestoreComponentMetadataById `
        -ComponentId $Id

    $actualId = [string]$metadata.componentId
    $name = [string]$metadata.name
    $type = [string]$metadata.type
    $version = [string]$metadata.version
    $currentVersion = [bool]$metadata.currentVersion
    $deleted = [bool]$metadata.deleted
    $folderName = [string]$metadata.folderName
    $folderId = [string]$metadata.folderId
    $branchName = [string]$metadata.branchName
    $branchId = [string]$metadata.branchId

    if ($actualId -ne $Id) {
        throw "RESTORE BLOCKED: ComponentMetadata ID mismatch."
    }

    if ([string]::IsNullOrWhiteSpace($name)) {
        throw "RESTORE BLOCKED: Component name is empty."
    }

    if ([string]::IsNullOrWhiteSpace($folderId)) {
        throw "RESTORE BLOCKED: Component folderId is empty."
    }

    Write-Host "Name            : $name"
    Write-Host "Component ID    : $actualId"
    Write-Host "Type            : $type"
    Write-Host "Version         : $version"
    Write-Host "Current Version : $currentVersion"
    Write-Host "Deleted         : $deleted"
    Write-Host "Folder Name     : $folderName"
    Write-Host "Folder ID       : $folderId"
    Write-Host "Branch          : $branchName"
    Write-Host "Branch ID       : $branchId"
    Write-Host ""

    # ========================================================
    # STEP 2 - Lifecycle state validation
    # ========================================================

    Write-Host "STEP 2 - Restore lifecycle validation"
    Write-Host "====================================="

    if (-not $currentVersion) {
        throw "RESTORE BLOCKED: ComponentMetadata is not the current version."
    }

    if (-not $deleted) {
        throw "RESTORE BLOCKED: Component is not deleted."
    }

    Write-Host "Current version : OK"
    Write-Host "Deleted state   : OK"
    Write-Host ""

    # ========================================================
    # STEP 3 - Resolve authoritative folder and write policy
    #
    # ComponentMetadata exposes folderId/folderName but not the
    # full folder path required by writePolicy.allowedFolders.
    # Resolve folderId back to the authoritative full path.
    # ========================================================

    Write-Host "STEP 3 - Resolve target folder"
    Write-Host "=============================="

    $configured = Get-BoomiCliConfig

    $resolvedAllowedFolder = $null

    foreach ($allowedFolder in @($configured.AllowedFolders)) {

        $folderInfo = Get-BoomiFolderByFullPath `
            -FullPath ([string]$allowedFolder)

        if ([string]$folderInfo.id -eq $folderId) {

            $resolvedAllowedFolder = $folderInfo
            break
        }
    }

    if ($null -eq $resolvedAllowedFolder) {

        throw @"
RESTORE BLOCKED: Deleted component folder is outside the configured write policy.

Component folder ID:
$folderId

Component folder name:
$folderName
"@
    }

    $folderFullPath = [string]$resolvedAllowedFolder.fullPath

    Assert-BoomiWriteFolder `
        -Folder $folderFullPath |
        Out-Null

    Write-Host "Folder:"
    Write-Host "  $folderFullPath"
    Write-Host "Folder ID:"
    Write-Host "  $folderId"
    Write-Host "Safety folder : OK"
    Write-Host ""

    # ========================================================
    # STEP 4 - Pre-restore metadata snapshot
    # ========================================================

    Write-Host "STEP 4 - Pre-restore metadata snapshot"
    Write-Host "======================================"

    $snapshotPath = Save-BoomiPreRestoreMetadataSnapshot `
        -Metadata $metadata

    Write-Host "Snapshot:"
    Write-Host "  $snapshotPath"
    Write-Host ""

    # ========================================================
    # STEP 5 - Final confirmation
    # ========================================================

    Write-Host "READY TO RESTORE"
    Write-Host "================"
    Write-Host ""
    Write-Host "Name:"
    Write-Host "  $name"
    Write-Host ""
    Write-Host "Component ID:"
    Write-Host "  $Id"
    Write-Host ""
    Write-Host "Type:"
    Write-Host "  $type"
    Write-Host ""
    Write-Host "Current Version:"
    Write-Host "  $version"
    Write-Host ""
    Write-Host "Folder:"
    Write-Host "  $folderFullPath"
    Write-Host ""
    Write-Host "Branch:"
    Write-Host "  $branchName"
    Write-Host "  $branchId"
    Write-Host ""
    Write-Host "Pre-restore metadata snapshot:"
    Write-Host "  $snapshotPath"
    Write-Host ""
    Write-Host "This operation will restore the deleted Component."
    Write-Host "The same Component ID is expected to remain in use."
    Write-Host "No automatic retry will be performed."
    Write-Host ""

    $confirmation = Read-Host "Type RESTORE exactly to continue"

    if ($confirmation -cne "RESTORE") {
        throw "RESTORE CANCELLED."
    }

    # ========================================================
    # STEP 6 - RESTORE
    #
    # Official ComponentMetadata restore contract:
    #
    # POST /ComponentMetadata
    #
    # {
    #   "componentId": "<deleted component id>"
    # }
    #
    # Never automatically retry after this request.
    # ========================================================

    Write-Host ""
    Write-Host "STEP 6 - Restoring Component"
    Write-Host "============================"

    $restoreBody = @{
        componentId = $Id
    } | ConvertTo-Json -Depth 5

    try {

        Invoke-RestMethod `
            -Method Post `
            -Uri "$script:BaseUrl/ComponentMetadata" `
            -Headers $script:JsonHeaders `
            -Body ([Text.Encoding]::UTF8.GetBytes($restoreBody)) `
            -ErrorAction Stop |
            Out-Null
    }
    catch {

        throw @"
RESTORE REQUEST ERROR.

A restore request was attempted for:
$Id

Do NOT automatically retry.

Check authoritative ComponentMetadata state before deciding
whether another restore request is safe.

Original error:
$($_.Exception.Message)
"@
    }

    Write-Host "RESTORE request returned successfully."
    Write-Host ""

    # ========================================================
    # STEP 7 - Authoritative ComponentMetadata verification
    # ========================================================

    Write-Host "STEP 7 - ComponentMetadata post-restore verification"
    Write-Host "===================================================="

    try {

        $postMetadata = Get-BoomiRestoreComponentMetadataById `
            -ComponentId $Id
    }
    catch {

        throw @"
POST-RESTORE VERIFY ERROR.

The RESTORE request returned successfully, but
ComponentMetadata could not be retrieved afterward.

Do NOT retry RESTORE automatically.

Component ID:
$Id
"@
    }

    if ([string]$postMetadata.componentId -ne $Id) {
        throw "POST-RESTORE VERIFY ERROR: ComponentMetadata ID mismatch."
    }

    if (-not [bool]$postMetadata.currentVersion) {
        throw "POST-RESTORE VERIFY ERROR: Restored metadata is not current."
    }

    if ([bool]$postMetadata.deleted) {

        throw @"
POST-RESTORE VERIFY ERROR: Component is still reported as deleted.

Component ID:
$Id

Do NOT retry RESTORE automatically.
"@
    }

    if ([string]$postMetadata.name -cne $name) {
        throw "POST-RESTORE VERIFY ERROR: Component name changed."
    }

    if ([string]$postMetadata.type -ne $type) {
        throw "POST-RESTORE VERIFY ERROR: Component type changed."
    }

    if ([string]$postMetadata.branchId -ne $branchId) {
        throw "POST-RESTORE VERIFY ERROR: Component branch changed."
    }

    Write-Host "Component ID    : OK"
    Write-Host "Current Version : true"
    Write-Host "Deleted         : false"
    Write-Host "Name            : OK"
    Write-Host "Type            : OK"
    Write-Host "Branch          : OK"
    Write-Host ""

    # ========================================================
    # STEP 8 - Authoritative Component GET
    # ========================================================

    Write-Host "STEP 8 - Authoritative Component GET"
    Write-Host "===================================="

    $componentResponse = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$componentXml = $componentResponse.Content
    $component = $componentXml.Component

    if ($null -eq $component) {
        throw "POST-RESTORE VERIFY ERROR: Component GET returned no Component root."
    }

    if ([string]$component.componentId -ne $Id) {
        throw "POST-RESTORE VERIFY ERROR: Component GET ID mismatch."
    }

    if ([string]$component.name -cne $name) {
        throw "POST-RESTORE VERIFY ERROR: Component GET name mismatch."
    }

    if ([string]$component.type -ne $type) {
        throw "POST-RESTORE VERIFY ERROR: Component GET type mismatch."
    }

    if ([string]$component.deleted -ne "false") {
        throw "POST-RESTORE VERIFY ERROR: Component GET reports deleted state."
    }

    if ([string]$component.currentVersion -ne "true") {
        throw "POST-RESTORE VERIFY ERROR: Component GET is not current."
    }

    if ([string]$component.branchId -ne $branchId) {
        throw "POST-RESTORE VERIFY ERROR: Component GET branch mismatch."
    }

    Write-Host "Component GET ID      : OK"
    Write-Host "Component GET name    : OK"
    Write-Host "Component GET type    : OK"
    Write-Host "Component GET current : OK"
    Write-Host "Component GET active  : OK"
    Write-Host "Component GET branch  : OK"
    Write-Host ""

    Write-Host "CONTROLLED COMPONENT RESTORE: VERIFIED SUCCESSFULLY"
    Write-Host "==================================================="
    Write-Host ""
    Write-Host "Name:"
    Write-Host "  $name"
    Write-Host ""
    Write-Host "Component ID:"
    Write-Host "  $Id"
    Write-Host ""
    Write-Host "Previous Version:"
    Write-Host "  $version"
    Write-Host ""
    Write-Host "Current Version:"
    Write-Host "  $([string]$postMetadata.version)"
    Write-Host ""
    Write-Host "Pre-restore metadata snapshot:"
    Write-Host "  $snapshotPath"
    Write-Host ""

    return [PSCustomObject]@{
        Name            = $name
        Id              = $Id
        Type            = $type
        Folder          = $folderFullPath
        BranchName      = $branchName
        BranchId        = $branchId
        PreviousVersion = $version
        CurrentVersion  = [string]$postMetadata.version
        Deleted         = $false
        SnapshotPath    = $snapshotPath
    }
}