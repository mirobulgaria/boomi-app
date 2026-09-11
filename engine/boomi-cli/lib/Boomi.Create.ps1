# ============================================================
# Boomi.Create.ps1
# boomi-cli - Generic Component Create Orchestrator
#
# Capabilities:
#   PREVIEW
#   verified Component CREATE
#
# Pipeline:
#   Spec
#     -> Validate
#     -> Resolve references
#     -> Resolve folder
#     -> Resolve configured target branch
#     -> Validate dependency branch compatibility
#     -> Build fresh XML
#     -> Verify XML
#     -> Save UTF-8 preview
#
# IMPORTANT:
#   - NO S1/S2/S3/S4 logic
#   - NO hard-coded Component IDs
#   - NO deployment
#   - NO execution
# ============================================================


function Get-BoomiTargetBranch {

    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [object[]]$ResolvedReferences
    )

    $configuredBranch = Get-BoomiConfiguredBranchContext

    if ([string]::IsNullOrWhiteSpace([string]$configuredBranch.Id)) {
        throw "CREATE PREVIEW ERROR: Configured target branch ID is empty."
    }

    if ([string]::IsNullOrWhiteSpace([string]$configuredBranch.Name)) {
        throw "CREATE PREVIEW ERROR: Configured target branch name is empty."
    }

    $referenceBranches = @()

    foreach ($reference in @($ResolvedReferences)) {

        if ($null -eq $reference) {
            throw "CREATE PREVIEW ERROR: Resolved references contain a null item."
        }

        if ([string]::IsNullOrWhiteSpace([string]$reference.Id)) {
            throw "CREATE PREVIEW ERROR: Resolved reference contains no Component ID."
        }

        $response = Get-BoomiComponentXml `
            -ComponentId ([string]$reference.Id)

        [xml]$referenceXml = $response.Content
        $component = $referenceXml.Component

        if (
            [string]$component.componentId -ne
            [string]$reference.Id
        ) {
            throw "CREATE PREVIEW ERROR: Authoritative reference Component ID mismatch."
        }

        $branchId = [string]$component.branchId
        $branchName = [string]$component.branchName

        if ([string]::IsNullOrWhiteSpace($branchId)) {
            throw "CREATE PREVIEW ERROR: Reference '$($reference.Name)' has no branchId."
        }

        if ([string]::IsNullOrWhiteSpace($branchName)) {
            throw "CREATE PREVIEW ERROR: Reference '$($reference.Name)' has no branchName."
        }

        $referenceBranches += [PSCustomObject]@{
            Shape      = [string]$reference.Shape
            Role       = [string]$reference.Role
            Name       = [string]$reference.Name
            Id         = [string]$reference.Id
            BranchName = $branchName
            BranchId   = $branchId
        }
    }

    $conflicts = @(
        $referenceBranches |
            Where-Object {
                [string]$_.BranchId -cne [string]$configuredBranch.Id -or
                [string]$_.BranchName -cne [string]$configuredBranch.Name
            }
    )

    if ($conflicts.Count -gt 0) {

        $displayText = $conflicts |
            Format-Table `
                Shape,
                Role,
                Name,
                BranchName,
                BranchId `
                -AutoSize |
            Out-String

        Write-Host ""
        Write-Host "BRANCH CONFLICT"
        Write-Host "==============="
        Write-Host "Configured target branch:"
        Write-Host "  Name : $($configuredBranch.Name)"
        Write-Host "  ID   : $($configuredBranch.Id)"
        Write-Host ""
        Write-Host $displayText.TrimEnd()
        Write-Host ""

        throw "CREATE PREVIEW ERROR: One or more component references do not belong to the configured target branch."
    }

    return [PSCustomObject]@{
        Id         = [string]$configuredBranch.Id
        Name       = [string]$configuredBranch.Name
        References = $referenceBranches
    }
}


function New-BoomiComponentCreatePreview {

    param(
        [Parameter(Mandatory=$true)]
        [string]$SpecPath
    )

    Write-Host ""
    Write-Host "GENERIC COMPONENT CREATE - PREVIEW ONLY"
    Write-Host "======================================="
    Write-Host ""

    # ========================================================
    # STEP 1 - Read spec
    # ========================================================

    Write-Host "STEP 1 - Read specification"
    Write-Host "==========================="

    $specResult = Read-BoomiComponentSpec `
        -SpecPath $SpecPath

    Write-Host "File   : $($specResult.Path)"
    Write-Host "Name   : $($specResult.ComponentName)"
    Write-Host "Type   : $($specResult.ComponentType)"
    Write-Host "Folder : $($specResult.Folder)"
    Write-Host ""

    # ========================================================
    # STEP 2 - Validate spec
    # ========================================================

    Write-Host "STEP 2 - Validate specification"
    Write-Host "==============================="

    $validationResult = Test-BoomiComponentSpec `
        -SpecResult $specResult

    if ($validationResult -ne $true) {
        throw "CREATE PREVIEW ERROR: Specification validation did not return True."
    }

    # ========================================================
    # STEP 3 - Resolve named references
    # ========================================================

    Write-Host "STEP 3 - Resolve component references"
    Write-Host "====================================="

    $resolvedReferences = @(
        Resolve-BoomiComponentSpecReferences `
            -SpecResult $specResult
    )

    # Machine-output safety check.
    foreach ($reference in $resolvedReferences) {

        if (
            $reference.GetType().FullName -ne
            "System.Management.Automation.PSCustomObject"
        ) {
            throw "CREATE PREVIEW ERROR: Reference resolver returned a non-PSCustomObject pipeline item."
        }

        if ([string]::IsNullOrWhiteSpace([string]$reference.Id)) {
            throw "CREATE PREVIEW ERROR: Resolved reference contains an empty ID."
        }
    }

    # ========================================================
    # STEP 4 - Resolve target folder
    # ========================================================

    Write-Host "STEP 4 - Resolve target folder"
    Write-Host "=============================="

    # Safety boundary is deliberately checked again here.
    Assert-BoomiWriteFolder `
        -Folder $specResult.Folder |
        Out-Null

    $folderInfo = Get-BoomiFolderByFullPath `
        -FullPath $specResult.Folder

    if (
        [string]$folderInfo.fullPath -ne
        [string]$specResult.Folder
    ) {
        throw "CREATE PREVIEW ERROR: Resolved target folder path mismatch."
    }

    if ([string]::IsNullOrWhiteSpace([string]$folderInfo.id)) {
        throw "CREATE PREVIEW ERROR: Resolved target folder has no ID."
    }

    Write-Host "Folder    : $($folderInfo.fullPath)"
    Write-Host "Folder ID : $($folderInfo.id)"
    Write-Host ""

    # ========================================================
    # STEP 5 - Resolve configured target branch and
    # validate dependency branch compatibility.
    # ========================================================

    Write-Host "STEP 5 - Resolve target branch"
    Write-Host "=============================="

    $branch = Get-BoomiTargetBranch `
        -ResolvedReferences $resolvedReferences

    Write-Host "Branch Name : $($branch.Name)"
    Write-Host "Branch ID   : $($branch.Id)"
    Write-Host "References  : $(@($branch.References).Count)"
    Write-Host ""

    # ========================================================
    # STEP 6 - Duplicate protection
    #
    # This is a preview but we already perform the same
    # duplicate guard that CREATE will use.
    # ========================================================

    Write-Host "STEP 6 - Duplicate protection"
    Write-Host "============================="

    if (
        Test-BoomiComponentNameExists `
            -Name $specResult.ComponentName
    ) {
        throw "CREATE PREVIEW BLOCKED: A component named '$($specResult.ComponentName)' already exists."
    }

    Write-Host "Duplicate check : OK"
    Write-Host ""

    # ========================================================
    # STEP 7 - Build fresh XML
    # ========================================================

    Write-Host "STEP 7 - Build fresh Component XML"
    Write-Host "=================================="

    $generatedXml = New-BoomiComponentXml `
        -SpecResult $specResult `
        -ResolvedReferences $resolvedReferences `
        -FolderId ([string]$folderInfo.id) `
        -BranchId ([string]$branch.Id)

    if ($null -eq $generatedXml) {
        throw "CREATE PREVIEW ERROR: XML builder returned null."
    }

    Write-Host "Fresh XML DOM : OK"
    Write-Host ""

    # ========================================================
    # STEP 8 - Generic verification
    # ========================================================

    Write-Host "STEP 8 - Verify generated XML"
    Write-Host "============================="

    $verifyResult = Test-BoomiGeneratedComponentXml `
        -SpecResult $specResult `
        -ResolvedReferences $resolvedReferences `
        -Xml $generatedXml `
        -FolderId ([string]$folderInfo.id) `
        -BranchId ([string]$branch.Id)

    if ($verifyResult -ne $true) {
        throw "CREATE PREVIEW ERROR: Generated XML verification did not return True."
    }

    # ========================================================
    # STEP 9 - Save UTF-8 preview
    # ========================================================

    Write-Host "STEP 9 - Save preview"
    Write-Host "====================="

    $safeName = Get-BoomiSafeFileName `
        -Value ([string]$specResult.ComponentName)

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $previewPath = Join-Path `
        "$script:WorkspaceRoot\templates" `
        "${timestamp}_generic_create_preview_${safeName}.xml"

    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
    $settings.Indent = $true
    $settings.OmitXmlDeclaration = $false

    $writer = [System.Xml.XmlWriter]::Create(
        $previewPath,
        $settings
    )

    try {
        $generatedXml.Save($writer)
    }
    finally {
        $writer.Close()
    }

    # ========================================================
    # STEP 10 - Re-read saved preview and verify again
    # ========================================================

    [xml]$savedXml = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $savedVerifyResult = Test-BoomiGeneratedComponentXml `
        -SpecResult $specResult `
        -ResolvedReferences $resolvedReferences `
        -Xml $savedXml `
        -FolderId ([string]$folderInfo.id) `
        -BranchId ([string]$branch.Id)

    if ($savedVerifyResult -ne $true) {
        throw "CREATE PREVIEW ERROR: Saved UTF-8 preview failed verification."
    }

    Write-Host "Preview file : $previewPath"
    Write-Host "UTF-8 re-read: OK"
    Write-Host ""

    # ========================================================
    # RESULT
    # ========================================================

    Write-Host "GENERIC CREATE PREVIEW: VERIFIED SUCCESSFULLY"
    Write-Host "============================================="
    Write-Host ""
    Write-Host "Component:"
    Write-Host "  Name   : $($specResult.ComponentName)"
    Write-Host "  Type   : $($specResult.ComponentType)"
    Write-Host "  Folder : $($specResult.Folder)"
    Write-Host ""
    Write-Host "Resolved dependencies:"
    Write-Host "  $($resolvedReferences.Count)"
    Write-Host ""
    Write-Host "Branch:"
    Write-Host "  $($branch.Name)"
    Write-Host "  $($branch.Id)"
    Write-Host ""
    Write-Host "NO COMPONENT CREATE WAS PERFORMED."
    Write-Host "NO DEPLOYMENT OR EXECUTION WAS PERFORMED."
    Write-Host ""

    return [PSCustomObject]@{
        SpecResult          = $specResult
        ResolvedReferences  = $resolvedReferences
        FolderInfo          = $folderInfo
        Branch              = $branch
        Xml                 = $savedXml
        PreviewPath         = $previewPath
    }
}

function Invoke-BoomiComponentCreateFromSpec {

    param(
        [Parameter(Mandatory=$true)]
        [string]$SpecPath
    )

    Write-Host ""
    Write-Host "GENERIC COMPONENT CREATE"
    Write-Host "========================"
    Write-Host ""

    # ========================================================
    # STEP 1 - Run complete verified preview pipeline
    # ========================================================

    $preview = New-BoomiComponentCreatePreview `
        -SpecPath $SpecPath

    if ($null -eq $preview) {
        throw "CREATE ERROR: Generic preview returned no result."
    }

    if ($null -eq $preview.Xml) {
        throw "CREATE ERROR: Generic preview returned no verified XML."
    }

    $specResult = $preview.SpecResult
    $resolvedReferences = @($preview.ResolvedReferences)
    $folderInfo = $preview.FolderInfo
    $branch = $preview.Branch
    [xml]$createXml = $preview.Xml

    # ========================================================
    # STEP 2 - Final safety checks
    # ========================================================

    Write-Host ""
    Write-Host "STEP 10 - Final CREATE safety checks"
    Write-Host "===================================="

    Assert-BoomiWriteFolder `
        -Folder $specResult.Folder |
        Out-Null

    if (
        Test-BoomiComponentNameExists `
            -Name $specResult.ComponentName
    ) {
        throw "CREATE BLOCKED: Component '$($specResult.ComponentName)' already exists."
    }

    $root = $createXml.DocumentElement

    if ($root.HasAttribute("componentId")) {
        throw "CREATE BLOCKED: CREATE XML contains componentId."
    }

    if ($root.HasAttribute("version")) {
        throw "CREATE BLOCKED: CREATE XML contains version."
    }

    $finalVerify = Test-BoomiGeneratedComponentXml `
        -SpecResult $specResult `
        -ResolvedReferences $resolvedReferences `
        -Xml $createXml `
        -FolderId ([string]$folderInfo.id) `
        -BranchId ([string]$branch.Id)

    if ($finalVerify -ne $true) {
        throw "CREATE BLOCKED: Final XML verification did not return True."
    }

    Write-Host "Safety folder      : OK"
    Write-Host "Duplicate check    : OK"
    Write-Host "Fresh identity     : OK"
    Write-Host "Final verification : OK"
    Write-Host ""

    # ========================================================
    # STEP 3 - Confirmation
    # ========================================================

    Write-Host "READY TO CREATE"
    Write-Host "==============="
    Write-Host ""
    Write-Host "Name:"
    Write-Host "  $($specResult.ComponentName)"
    Write-Host ""
    Write-Host "Type:"
    Write-Host "  $($specResult.ComponentType)"
    Write-Host ""
    Write-Host "Folder:"
    Write-Host "  $($specResult.Folder)"
    Write-Host ""
    Write-Host "Branch:"
    Write-Host "  $($branch.Name)"
    Write-Host "  $($branch.Id)"
    Write-Host ""
    Write-Host "Dependencies:"
    Write-Host "  $($resolvedReferences.Count)"
    Write-Host ""
    Write-Host "Specification:"
    Write-Host "  $($specResult.Path)"
    Write-Host ""
    Write-Host "Verified preview:"
    Write-Host "  $($preview.PreviewPath)"
    Write-Host ""
    Write-Host "A NEW Component will be created."
    Write-Host "This is NOT a clone operation."
    Write-Host ""
    Write-Host "No deployment or execution will occur."
    Write-Host ""

    $confirmation = Read-Host "Type CREATE exactly to continue"

    if ($confirmation -cne "CREATE") {

        Write-Host ""
        Write-Host "CREATE cancelled."
        Write-Host "No Boomi write was performed."
        Write-Host ""

        return
    }

    # ========================================================
# STEP 4 - Serialize verified DOM directly to UTF-8 bytes
#
# IMPORTANT:
# Do NOT use StringWriter here.
# StringWriter is UTF-16 and causes the XML declaration
# to become encoding="utf-16", even if XmlWriterSettings
# requests UTF-8.
#
# The HTTP request body must be the exact bytes produced
# by an UTF-8 XmlWriter.
# ========================================================

$memoryStream = New-Object System.IO.MemoryStream

$xmlSettings = New-Object System.Xml.XmlWriterSettings
$xmlSettings.Encoding = New-Object System.Text.UTF8Encoding($false)
$xmlSettings.Indent = $false
$xmlSettings.OmitXmlDeclaration = $false

$xmlWriter = [System.Xml.XmlWriter]::Create(
    $memoryStream,
    $xmlSettings
)

try {

    $createXml.Save($xmlWriter)
    $xmlWriter.Flush()
}
finally {

    $xmlWriter.Close()
}

$payloadBytes = $memoryStream.ToArray()
$memoryStream.Close()

if (
    $null -eq $payloadBytes -or
    $payloadBytes.Length -eq 0
) {
    throw "CREATE BLOCKED: Serialized CREATE payload is empty."
}

# Defensive verification of the exact bytes that will be sent.
$payloadCheck = [Text.Encoding]::UTF8.GetString(
    $payloadBytes
)

$encodingMatch = [regex]::Match(
    $payloadCheck,
    '<\?xml[^?]*encoding="([^"]+)"',
    [Text.RegularExpressions.RegexOptions]::IgnoreCase
)

if (-not $encodingMatch.Success) {
    throw "CREATE BLOCKED: Serialized payload contains no XML encoding declaration."
}

$declaredEncoding = $encodingMatch.Groups[1].Value

if ($declaredEncoding -ine "utf-8") {

    throw @"
CREATE BLOCKED: XML encoding mismatch.

Expected declaration:
UTF-8

Actual declaration:
$declaredEncoding
"@
}

Write-Host "Payload encoding : UTF-8"
Write-Host "Payload bytes    : $($payloadBytes.Length)"
Write-Host ""

    # ========================================================
    # STEP 5 - Component CREATE
    # ========================================================

    Write-Host ""
    Write-Host "STEP 11 - Creating Component..."
    Write-Host "==============================="

    $writeHeaders = Get-BoomiWriteHeaders

    try {

        $createResponse = Invoke-WebRequest `
            -Method Post `
            -Uri "$script:BaseUrl/Component" `
            -Headers $writeHeaders `
            -Body $payloadBytes `
            -UseBasicParsing
    }
    catch {

        Write-Host ""
        Write-Host "GENERIC COMPONENT CREATE FAILED."
        Write-Host "Do NOT retry automatically."
        Write-Host ""

        throw
    }

    # ========================================================
    # STEP 6 - Obtain new identity
    # ========================================================

    [xml]$createResponseXml = $createResponse.Content

    $newId = [string]$createResponseXml.Component.componentId

    if ([string]::IsNullOrWhiteSpace($newId)) {
        throw "CREATE ERROR: Boomi returned no Component ID. Manual verification required."
    }

    Write-Host "Boomi returned new Component ID:"
    Write-Host "  $newId"
    Write-Host ""

    # ========================================================
    # STEP 7 - Authoritative GET
    # ========================================================

    Write-Host "STEP 12 - Authoritative post-CREATE verification"
    Write-Host "==============================================="

    $verifyResponse = Get-BoomiComponentXml `
        -ComponentId $newId

    [xml]$actualXml = $verifyResponse.Content
    $actual = $actualXml.Component

    if ([string]$actual.componentId -ne $newId) {
        throw "POST-CREATE VERIFY ERROR: Component ID mismatch."
    }

    if ([string]$actual.name -cne [string]$specResult.ComponentName) {
        throw "POST-CREATE VERIFY ERROR: Component name mismatch."
    }

    if ([string]$actual.type -ne [string]$specResult.ComponentType) {
        throw "POST-CREATE VERIFY ERROR: Component type mismatch."
    }

    if ([string]$actual.folderFullPath -ne [string]$specResult.Folder) {
        throw "POST-CREATE VERIFY ERROR: Component folder mismatch."
    }

    if ([string]$actual.branchId -ne [string]$branch.Id) {
        throw "POST-CREATE VERIFY ERROR: Component branch mismatch."
    }

    # ========================================================
    # STEP 8 - Verify authoritative object against spec
    #
    # GET adds Component identity metadata, therefore
    # AllowComponentIdentity is intentional here.
    # ========================================================

    $postVerify = Test-BoomiGeneratedComponentXml `
        -SpecResult $specResult `
        -ResolvedReferences $resolvedReferences `
        -Xml $actualXml `
        -FolderId ([string]$folderInfo.id) `
        -BranchId ([string]$branch.Id) `
        -AllowComponentIdentity

    if ($postVerify -ne $true) {
        throw "POST-CREATE VERIFY ERROR: Authoritative Component object does not match specification."
    }

    Write-Host "Component ID       : OK"
    Write-Host "Name               : OK"
    Write-Host "Type               : OK"
    Write-Host "Folder             : OK"
    Write-Host "Branch             : OK"
    Write-Host "Object vs spec     : OK"
    Write-Host ""

    # ========================================================
    # STEP 9 - Save authoritative result
    # ========================================================

    $safeName = Get-BoomiSafeFileName `
        -Value ([string]$specResult.ComponentName)

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $verifiedPath = Join-Path `
        "$script:WorkspaceRoot\exports" `
        "${timestamp}_verified_generic_create_${safeName}.xml"

    Write-BoomiUtf8File `
        -Path $verifiedPath `
        -Content $verifyResponse.Content

    # ========================================================
    # RESULT
    # ========================================================

    Write-Host "GENERIC COMPONENT CREATE: VERIFIED SUCCESSFULLY"
    Write-Host "==============================================="
    Write-Host ""
    Write-Host "Name:"
    Write-Host "  $($actual.name)"
    Write-Host ""
    Write-Host "Component ID:"
    Write-Host "  $newId"
    Write-Host ""
    Write-Host "Version:"
    Write-Host "  $($actual.version)"
    Write-Host ""
    Write-Host "Authoritative XML:"
    Write-Host "  $verifiedPath"
    Write-Host ""
    Write-Host "No clone operation was performed."
    Write-Host "No deployment or execution was performed."
    Write-Host ""

    return [PSCustomObject]@{
        Name         = [string]$actual.name
        Id           = $newId
        Version      = [string]$actual.version
        Type         = [string]$actual.type
        Folder       = [string]$actual.folderFullPath
        BranchName   = [string]$actual.branchName
        BranchId     = [string]$actual.branchId
        SpecPath     = [string]$specResult.Path
        VerifiedPath = $verifiedPath
    }
}
