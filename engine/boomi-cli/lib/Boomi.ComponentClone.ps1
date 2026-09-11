# ============================================================
# Boomi.ComponentClone.ps1
# boomi-cli v1 SAFE component clone
#
# CURRENT ALLOW-LIST:
#   transform.map
#   connector-action
#
# EXPLICITLY NOT ALLOWED:
#   connector-settings
#
# Reason:
#   connector-settings may contain environment-specific
#   endpoint/security/user configuration and GET does not
#   necessarily expose secrets such as passwords.
#
# HARD TARGET SAFETY BOUNDARY:
#   The target folder must be explicitly allowed by the
#   external CLI write policy.
#
# NO source modification.
# NO deployment.
# NO execution.
# NO delete.
# ============================================================


function Get-BoomiComponentDefinitionFingerprint {

    param(
        [Parameter(Mandatory=$true)]
        [xml]$Xml
    )

    $objectNode = $Xml.SelectSingleNode(
        "/*[local-name()='Component']/*[local-name()='object']"
    )

    if (-not $objectNode) {
        throw "Component object definition was not found."
    }

    return [string]$objectNode.InnerXml
}


function Test-BoomiAllowedCloneType {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Type
    )

    $allowedTypes = @(
        "transform.map",
        "connector-action"
    )

    return ($allowedTypes -contains $Type)
}


function Test-BoomiConnectorActionCloneSource {

    param(
        [Parameter(Mandatory=$true)]
        [xml]$Xml
    )

    $component = $Xml.Component

    if ([string]$component.type -ne "connector-action") {
        return
    }

    # --------------------------------------------------------
    # Current evidence-supported connector-action subtype:
    # wssoapclientsdk
    #
    # Do not generalize to other connector subtypes yet.
    # --------------------------------------------------------

    if ([string]$component.subType -ne "wssoapclientsdk") {
        throw @"
CLONE BLOCKED.

connector-action subtype is not currently proven for cloning.

Actual subtype:
$($component.subType)

Currently proven subtype:
wssoapclientsdk
"@
    }

    $genericConfig = $Xml.SelectSingleNode(
        "/*[local-name()='Component']/*[local-name()='object']//*[local-name()='GenericOperationConfig']"
    )

    if (-not $genericConfig) {
        throw "CLONE BLOCKED: GenericOperationConfig was not found."
    }

    $operationType = [string]$genericConfig.operationType
    $requestProfileType = [string]$genericConfig.requestProfileType
    $responseProfileType = [string]$genericConfig.responseProfileType

    # --------------------------------------------------------
    # Current evidence-supported operation:
    # EXECUTE / xml / xml
    # --------------------------------------------------------

    if ($operationType -ne "EXECUTE") {
        throw @"
CLONE BLOCKED.

connector-action operationType is not currently proven.

Actual:
$operationType

Currently proven:
EXECUTE
"@
    }

    if ($requestProfileType -ne "xml") {
        throw @"
CLONE BLOCKED.

connector-action requestProfileType is not currently proven.

Actual:
$requestProfileType

Currently proven:
xml
"@
    }

    if ($responseProfileType -ne "xml") {
        throw @"
CLONE BLOCKED.

connector-action responseProfileType is not currently proven.

Actual:
$responseProfileType

Currently proven:
xml
"@
    }

    Write-Host "Connector subtype    : OK (wssoapclientsdk)"
    Write-Host "Operation type       : OK (EXECUTE)"
    Write-Host "Request profile type : OK (xml)"
    Write-Host "Response profile type: OK (xml)"
}


function Copy-BoomiAllowedComponent {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id,

        [Parameter(Mandatory=$true)]
        [string]$Name,

        [Parameter(Mandatory=$true)]
        [string]$Folder
    )

    Write-Host ""
    Write-Host "SAFE CLONE - Component"
    Write-Host "======================"
    Write-Host ""

    # ========================================================
    # STEP 1 - Hard target safety boundary
    # ========================================================

    Assert-BoomiWriteFolder `
        -Folder $Folder

    Write-Host "Target safety boundary : OK"
    Write-Host ""

    # ========================================================
    # STEP 2 - Authoritative source GET
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
    Write-Host "Source SubType : $($source.subType)"
    Write-Host "Source Version : $($source.version)"
    Write-Host "Source Folder  : $($source.folderFullPath)"
    Write-Host "Source Branch  : $($source.branchName)"
    Write-Host ""

    if ($source.componentId -ne $Id) {
        throw "CLONE BLOCKED: Source Component ID mismatch."
    }

    # ========================================================
    # STEP 3 - Type allow-list
    # ========================================================

    if (-not (
        Test-BoomiAllowedCloneType `
            -Type ([string]$source.type)
    )) {

        throw @"
CLONE BLOCKED.

Source component type:
$($source.type)

Currently allowed:
transform.map
connector-action

connector-settings is intentionally NOT allowed.
"@
    }

    Write-Host "Component type allow-list : OK ($($source.type))"

    # Additional evidence-based validation for connector-action.
    if ([string]$source.type -eq "connector-action") {

        Test-BoomiConnectorActionCloneSource `
            -Xml $sourceXml
    }

    Write-Host ""

    # ========================================================
    # STEP 4 - Resolve target folder
    # ========================================================

    Write-Host "STEP 4 - Resolve target folder"
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
    # STEP 5 - Duplicate protection
    # ========================================================

    Write-Host "STEP 5 - Duplicate protection"
    Write-Host "============================="

    if (Test-BoomiComponentNameExists -Name $Name) {
        throw "CLONE BLOCKED: A component named '$Name' already exists."
    }

    Write-Host "Duplicate check : OK"
    Write-Host ""

    # ========================================================
    # STEP 6 - Source object definition
    # ========================================================

    $sourceDefinition = Get-BoomiComponentDefinitionFingerprint `
        -Xml $sourceXml

    if ([string]::IsNullOrWhiteSpace($sourceDefinition)) {
        throw "CLONE BLOCKED: Source component definition is empty."
    }

    Write-Host "STEP 6 - Source definition"
    Write-Host "=========================="
    Write-Host "Component object definition found : OK"
    Write-Host ""

    # ========================================================
    # STEP 7 - Backup
    # ========================================================

    $backupPath = Save-BoomiBackup `
        -ComponentName ([string]$source.name) `
        -XmlContent $sourceResponse.Content `
        -Reason "before_component_clone_source"

    Write-Host "STEP 7 - Source backup"
    Write-Host "======================"
    Write-Host "Authoritative source XML:"
    Write-Host "  $backupPath"
    Write-Host ""

    # ========================================================
    # STEP 8 - Build clone candidate
    # ========================================================

    [xml]$cloneXml = $sourceResponse.Content
    $clone = $cloneXml.Component

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

    $clone.SetAttribute(
        "name",
        $Name
    )

    $clone.SetAttribute(
        "folderId",
        [string]$folderInfo.id
    )

    $sourceBranchId = [string]$source.branchId

    if ([string]::IsNullOrWhiteSpace($sourceBranchId)) {
        throw "CLONE BLOCKED: Source GET XML contains no branchId."
    }

    $clone.SetAttribute(
        "branchId",
        $sourceBranchId
    )

    if ($clone.HasAttribute("branchName")) {
        $clone.RemoveAttribute("branchName")
    }

    # ========================================================
    # STEP 9 - Save preview as UTF-8
    # ========================================================

    $safeTargetName = Get-BoomiSafeFileName `
        -Value $Name

    $previewPath = Join-Path `
        "$script:WorkspaceRoot\templates" `
        "preview_component_clone_${safeTargetName}.xml"

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
    # STEP 10 - Preview verification
    # ========================================================

    [xml]$previewXml = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $preview = $previewXml.Component

    if ($preview.name -ne $Name) {
        throw "CLONE BLOCKED: Preview target name validation failed."
    }

    if ($preview.type -ne $source.type) {
        throw "CLONE BLOCKED: Preview component type changed."
    }

    if ($preview.subType -ne $source.subType) {
        throw "CLONE BLOCKED: Preview component subType changed."
    }

    if ($preview.folderId -ne [string]$folderInfo.id) {
        throw "CLONE BLOCKED: Preview folderId validation failed."
    }

    if (-not [string]::IsNullOrWhiteSpace(
        [string]$preview.componentId
    )) {
        throw "CLONE BLOCKED: Preview still contains source componentId."
    }

    if ([string]$preview.branchId -ne $sourceBranchId) {
        throw "CLONE BLOCKED: Preview branchId changed."
    }

    $previewDefinition = Get-BoomiComponentDefinitionFingerprint `
        -Xml $previewXml

    if ($previewDefinition -ne $sourceDefinition) {
        throw "CLONE BLOCKED: Preview component definition differs from source."
    }

    # Re-run connector-action validation against preview.
    if ([string]$preview.type -eq "connector-action") {

        Test-BoomiConnectorActionCloneSource `
            -Xml $previewXml
    }

    Write-Host "STEP 10 - Preview validation"
    Write-Host "============================"
    Write-Host "Target name       : OK"
    Write-Host "Component type    : OK"
    Write-Host "Component subType : OK"
    Write-Host "Target folderId   : OK"
    Write-Host "Source ID removed : OK"
    Write-Host "Branch ID         : OK"
    Write-Host "Object definition : OK"
    Write-Host ""
    Write-Host "Preview:"
    Write-Host "  $previewPath"
    Write-Host ""

    # ========================================================
    # STEP 11 - Explicit confirmation
    # ========================================================

    Write-Host "COMPONENT CLONE OPERATION"
    Write-Host "========================="
    Write-Host ""
    Write-Host "SOURCE:"
    Write-Host "  Name    : $($source.name)"
    Write-Host "  ID      : $($source.componentId)"
    Write-Host "  Type    : $($source.type)"
    Write-Host "  SubType : $($source.subType)"
    Write-Host "  Version : $($source.version)"
    Write-Host "  Folder  : $($source.folderFullPath)"
    Write-Host ""
    Write-Host "TARGET:"
    Write-Host "  Name    : $Name"
    Write-Host "  Type    : $($source.type)"
    Write-Host "  SubType : $($source.subType)"
    Write-Host "  Folder  : $Folder"
    Write-Host ""
    Write-Host "The source object definition will be preserved."
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
    # STEP 12 - CREATE
    # ========================================================

    $payload = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $writeHeaders = Get-BoomiWriteHeaders

    Write-Host ""
    Write-Host "STEP 12 - Creating component clone..."
    Write-Host "====================================="

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
        Write-Host "COMPONENT CLONE CREATE FAILED."
        Write-Host "The source component was not modified."
        Write-Host "Do not retry automatically."
        throw
    }

    [xml]$createdXml = $createResponse.Content
    $newId = [string]$createdXml.Component.componentId

    if ([string]::IsNullOrWhiteSpace($newId)) {
        throw "COMPONENT CLONE returned no componentId. Manual verification required."
    }

    Write-Host "Boomi returned new Component ID:"
    Write-Host "  $newId"
    Write-Host ""

    # ========================================================
    # STEP 13 - Authoritative GET verification
    # ========================================================

    Write-Host "STEP 13 - Verify authoritative clone"
    Write-Host "===================================="

    $verifyResponse = Get-BoomiComponentXml `
        -ComponentId $newId

    [xml]$verifyXml = $verifyResponse.Content
    $actual = $verifyXml.Component

    $failed = $false

    if ($actual.componentId -eq $newId) {
        Write-Host "New Component ID : OK"
    }
    else {
        Write-Host "New Component ID : FAILED"
        $failed = $true
    }

    if ($actual.componentId -ne $source.componentId) {
        Write-Host "Identity isolation: OK"
    }
    else {
        Write-Host "Identity isolation: FAILED"
        $failed = $true
    }

    if ($actual.name -eq $Name) {
        Write-Host "Target name       : OK"
    }
    else {
        Write-Host "Target name       : FAILED"
        $failed = $true
    }

    if ($actual.type -eq $source.type) {
        Write-Host "Component type    : OK ($($actual.type))"
    }
    else {
        Write-Host "Component type    : FAILED ($($actual.type))"
        $failed = $true
    }

    if ($actual.subType -eq $source.subType) {
        Write-Host "Component subType : OK ($($actual.subType))"
    }
    else {
        Write-Host "Component subType : FAILED ($($actual.subType))"
        $failed = $true
    }

    if ($actual.folderFullPath -eq $Folder) {
        Write-Host "Target folder     : OK"
    }
    else {
        Write-Host "Target folder     : FAILED"
        Write-Host "Actual folder     : $($actual.folderFullPath)"
        $failed = $true
    }

    $actualDefinition = Get-BoomiComponentDefinitionFingerprint `
        -Xml $verifyXml

    if ($actualDefinition -eq $sourceDefinition) {
        Write-Host "Object definition : OK"
    }
    else {
        Write-Host "Object definition : FAILED"
        $failed = $true
    }

    if ([string]$actual.type -eq "connector-action") {

        try {

            Test-BoomiConnectorActionCloneSource `
                -Xml $verifyXml

            Write-Host "SOAP operation validation : OK"
        }
        catch {

            Write-Host "SOAP operation validation : FAILED"
            $failed = $true
        }
    }

    # ========================================================
    # STEP 14 - Save authoritative result
    # ========================================================

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $verifiedPath = Join-Path `
        "$script:WorkspaceRoot\exports" `
        "${timestamp}_verified_component_clone_${safeTargetName}.xml"

    Write-BoomiUtf8File `
        -Path $verifiedPath `
        -Content $verifyResponse.Content

    Write-Host ""
    Write-Host "Authoritative clone XML:"
    Write-Host "  $verifiedPath"
    Write-Host ""

    if ($failed) {

        Write-Host "RESULT: COMPONENT CLONE CREATED, BUT VERIFICATION FAILED"
        Write-Host ""
        Write-Host "Do NOT rerun automatically."
        Write-Host "Inspect Component ID:"
        Write-Host "  $newId"
    }
    else {

        Write-Host "RESULT: COMPONENT CLONE VERIFIED SUCCESSFULLY"
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