# ============================================================
# Boomi.Delete.ps1
# boomi-cli - Controlled Component Delete
#
# Purpose:
#   Safely soft-delete an existing Boomi component through
#   the ComponentMetadata API.
#
# SAFETY MODEL:
#   - Component ID is mandatory.
#   - Authoritative Component GET before delete.
#   - Target folder must pass configured write policy.
#   - Component must be current and not already deleted.
#   - Authoritative XML backup before delete.
#   - Explicit DELETE confirmation.
#   - DELETE is sent only to ComponentMetadata/{id}.
#   - Post-delete verification uses ComponentMetadata GET.
#   - No automatic retry after a DELETE request.
#
# IMPORTANT:
#   Deleting ComponentMetadata does not delete dependent
#   components.
#
#   This module does NOT implement bulk delete.
# ============================================================


function Get-BoomiComponentMetadataById {

    param(
        [Parameter(Mandatory=$true)]
        [string]$ComponentId
    )

    if ([string]::IsNullOrWhiteSpace($ComponentId)) {
        throw "DELETE ERROR: ComponentId is empty."
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
DELETE ERROR: Failed to retrieve ComponentMetadata.

Component ID:
$ComponentId

No delete was performed by this operation.
"@
    }

    if ($null -eq $metadata) {
        throw "DELETE ERROR: ComponentMetadata GET returned no object."
    }

    return $metadata
}


function Save-BoomiPreDeleteBackup {

    param(
        [Parameter(Mandatory=$true)]
        [string]$ComponentId,

        [Parameter(Mandatory=$true)]
        [string]$ComponentName,

        [Parameter(Mandatory=$true)]
        [string]$XmlContent
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

    $safeName = $ComponentName -replace '[\\/:*?"<>|]', '_'
    $safeName = $safeName -replace '\s+', '_'

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $backupPath = Join-Path `
        $backupDirectory `
        ("{0}_before_delete_{1}_{2}.xml" -f `
            $timestamp,
            $safeName,
            $ComponentId)

    Write-BoomiUtf8File `
        -Path $backupPath `
        -Content $XmlContent

    if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
        throw "DELETE ERROR: Pre-delete backup file was not created."
    }

    return $backupPath
}


function Remove-BoomiComponent {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id
    )

    if ([string]::IsNullOrWhiteSpace($Id)) {
        throw "delete requires -Id"
    }

    Write-Host ""
    Write-Host "CONTROLLED COMPONENT DELETE"
    Write-Host "==========================="
    Write-Host ""

    # ========================================================
    # STEP 1 - Authoritative Component GET
    # ========================================================

    Write-Host "STEP 1 - Authoritative Component GET"
    Write-Host "===================================="

    $componentResponse = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$componentXml = $componentResponse.Content
    $component = $componentXml.Component

    if ($null -eq $component) {
        throw "DELETE BLOCKED: Component GET returned no Component root."
    }

    $actualId = [string]$component.componentId
    $name = [string]$component.name
    $type = [string]$component.type
    $folder = [string]$component.folderFullPath
    $branchName = [string]$component.branchName
    $branchId = [string]$component.branchId
    $version = [string]$component.version
    $currentVersion = [string]$component.currentVersion
    $deleted = [string]$component.deleted

    if ($actualId -ne $Id) {
        throw "DELETE BLOCKED: Authoritative Component ID mismatch."
    }

    if ([string]::IsNullOrWhiteSpace($name)) {
        throw "DELETE BLOCKED: Component name is empty."
    }

    if ([string]::IsNullOrWhiteSpace($folder)) {
        throw "DELETE BLOCKED: Component folder is empty."
    }

    Write-Host "Name            : $name"
    Write-Host "Component ID    : $actualId"
    Write-Host "Type            : $type"
    Write-Host "Version         : $version"
    Write-Host "Current Version : $currentVersion"
    Write-Host "Deleted         : $deleted"
    Write-Host "Folder          : $folder"
    Write-Host "Branch          : $branchName"
    Write-Host "Branch ID       : $branchId"
    Write-Host ""

    # ========================================================
    # STEP 2 - Safety policy
    # ========================================================

    Write-Host "STEP 2 - Delete safety policy"
    Write-Host "============================="

    Assert-BoomiWriteFolder `
        -Folder $folder |
    	Out-Null

    if ($currentVersion -ne "true") {
        throw "DELETE BLOCKED: Component GET is not the current version."
    }

    if ($deleted -ne "false") {
        throw "DELETE BLOCKED: Component is already deleted."
    }

    Write-Host "Safety folder   : OK"
    Write-Host "Current version : OK"
    Write-Host "Active state    : OK"
    Write-Host ""

    # ========================================================
    # STEP 3 - ComponentMetadata pre-delete verification
    # ========================================================

    Write-Host "STEP 3 - ComponentMetadata verification"
    Write-Host "======================================="

    $metadata = Get-BoomiComponentMetadataById `
        -ComponentId $Id

    if ([string]$metadata.componentId -ne $Id) {
        throw "DELETE BLOCKED: ComponentMetadata ID mismatch."
    }

    if ([string]$metadata.name -cne $name) {
        throw "DELETE BLOCKED: ComponentMetadata name mismatch."
    }

    if ([string]$metadata.type -ne $type) {
        throw "DELETE BLOCKED: ComponentMetadata type mismatch."
    }

    if ([string]$metadata.currentVersion -ne "true") {
        throw "DELETE BLOCKED: ComponentMetadata is not current."
    }

    if ([string]$metadata.deleted -ne "false") {
        throw "DELETE BLOCKED: ComponentMetadata reports component as deleted."
    }

    if (
        -not [string]::IsNullOrWhiteSpace($branchId) -and
        [string]$metadata.branchId -ne $branchId
    ) {
        throw "DELETE BLOCKED: ComponentMetadata branch mismatch."
    }

    Write-Host "Metadata ID      : OK"
    Write-Host "Metadata name    : OK"
    Write-Host "Metadata type    : OK"
    Write-Host "Metadata current : OK"
    Write-Host "Metadata active  : OK"
    Write-Host "Metadata branch  : OK"
    Write-Host ""

    # ========================================================
    # STEP 4 - Backup
    # ========================================================

    Write-Host "STEP 4 - Pre-delete backup"
    Write-Host "=========================="

    $backupPath = Save-BoomiPreDeleteBackup `
        -ComponentId $Id `
        -ComponentName $name `
        -XmlContent $componentResponse.Content

    Write-Host "Backup:"
    Write-Host "  $backupPath"
    Write-Host ""

    # ========================================================
    # STEP 5 - Final confirmation
    # ========================================================

    Write-Host "READY TO DELETE"
    Write-Host "==============="
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
    Write-Host "Folder:"
    Write-Host "  $folder"
    Write-Host ""
    Write-Host "Branch:"
    Write-Host "  $branchName"
    Write-Host "  $branchId"
    Write-Host ""
    Write-Host "Backup:"
    Write-Host "  $backupPath"
    Write-Host ""
    Write-Host "This operation will soft-delete the Component."
    Write-Host "Dependent components will NOT be deleted automatically."
    Write-Host "No automatic retry will be performed."
    Write-Host ""

    $confirmation = Read-Host "Type DELETE exactly to continue"

    if ($confirmation -cne "DELETE") {
        throw "DELETE CANCELLED."
    }

    # ========================================================
    # STEP 6 - DELETE
    #
    # IMPORTANT:
    # Once this request is sent, do not automatically retry
    # on an ambiguous transport/verification failure.
    # ========================================================

    Write-Host ""
    Write-Host "STEP 6 - Deleting ComponentMetadata"
    Write-Host "==================================="

    try {

        Invoke-RestMethod `
            -Method Delete `
            -Uri "$script:BaseUrl/ComponentMetadata/$Id" `
            -Headers $script:JsonHeaders `
            -ErrorAction Stop |
            Out-Null
    }
    catch {

        throw @"
DELETE REQUEST ERROR.

A DELETE request was attempted for:
$Id

Do NOT automatically retry.

Check authoritative ComponentMetadata state before deciding
whether another DELETE request is safe.

Original error:
$($_.Exception.Message)
"@
    }

    Write-Host "DELETE request returned successfully."
    Write-Host ""

    # ========================================================
    # STEP 7 - Authoritative post-delete verification
    # ========================================================

    Write-Host "STEP 7 - Authoritative post-delete verification"
    Write-Host "==============================================="

    try {

        $postMetadata = Get-BoomiComponentMetadataById `
            -ComponentId $Id
    }
    catch {

        throw @"
POST-DELETE VERIFY ERROR.

The DELETE request returned successfully, but
ComponentMetadata could not be retrieved afterward.

Do NOT retry DELETE automatically.

Component ID:
$Id
"@
    }

    if ([string]$postMetadata.componentId -ne $Id) {
        throw "POST-DELETE VERIFY ERROR: ComponentMetadata ID mismatch."
    }

    if ([string]$postMetadata.deleted -ne "true") {

        throw @"
POST-DELETE VERIFY ERROR: Component is not reported as deleted.

Component ID:
$Id

Actual deleted value:
$([string]$postMetadata.deleted)

Do NOT retry DELETE automatically.
"@
    }

    Write-Host "Component ID : OK"
    Write-Host "Deleted      : true"
    Write-Host ""

    Write-Host "CONTROLLED COMPONENT DELETE: VERIFIED SUCCESSFULLY"
    Write-Host "=================================================="
    Write-Host ""
    Write-Host "Name:"
    Write-Host "  $name"
    Write-Host ""
    Write-Host "Component ID:"
    Write-Host "  $Id"
    Write-Host ""
    Write-Host "Backup:"
    Write-Host "  $backupPath"
    Write-Host ""

    return [PSCustomObject]@{
        Name       = $name
        Id         = $Id
        Type       = $type
        Folder     = $folder
        BranchName = $branchName
        BranchId   = $branchId
        Deleted    = $true
        BackupPath = $backupPath
    }
}