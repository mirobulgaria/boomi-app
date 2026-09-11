# ============================================================
# Boomi.Write.ps1
# boomi-cli v1 SAFE WRITE functions
#
# HARD SAFETY BOUNDARY:
#   Write access is controlled by the external CLI
#   write policy.
#
# Supported:
#   New-BoomiEmptyProcess
#   Set-BoomiProcessShapeLabel
#
# NOT supported:
#   Delete
#   Deploy
#   Execute
# ============================================================

# ============================================================
# Common SAFE WRITE helpers
# ============================================================

function Assert-BoomiWriteFolder {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Folder
    )

    if ([string]::IsNullOrWhiteSpace($Folder)) {
        throw "WRITE BLOCKED: Requested folder is empty."
    }

    $config = Get-BoomiCliConfig

    $allowedFolders = @(
        $config.AllowedFolders
    )

    if ($allowedFolders.Count -eq 0) {
        throw "WRITE BLOCKED: CLI configuration contains no allowed write folders."
    }

    $isAllowed = $false

    foreach ($allowedFolder in $allowedFolders) {

        if (
            [string]$Folder -ceq
            [string]$allowedFolder
        ) {
            $isAllowed = $true
            break
        }
    }

    if (-not $isAllowed) {

        $allowedText = (
            $allowedFolders |
                ForEach-Object {
                    "  $_"
                }
        ) -join [Environment]::NewLine

        throw @"
WRITE BLOCKED.

Requested folder:
$Folder

Allowed write folders:
$allowedText
"@
    }

    return $true
}


function Get-BoomiFolderByFullPath {

    param(
        [Parameter(Mandatory=$true)]
        [string]$FullPath
    )

    $leafName = Split-Path $FullPath -Leaf

    $body = @{
        QueryFilter = @{
            expression = @{
                property = "name"
                operator = "EQUALS"
                argument = @($leafName)
            }
        }
    } | ConvertTo-Json -Depth 10

    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "$script:BaseUrl/Folder/query" `
        -Headers $script:JsonHeaders `
        -Body $body

    $matches = @(
        $response.result |
            Where-Object {
                $_.fullPath -eq $FullPath
            }
    )

    if ($matches.Count -eq 0) {
        throw "Folder not found: $FullPath"
    }

    if ($matches.Count -gt 1) {
        throw "Multiple folders matched full path: $FullPath"
    }

    return $matches[0]
}


function Test-BoomiComponentNameExists {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Name
    )

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
        -Body $body

    return ($response.numberOfResults -gt 0)
}


function Get-BoomiSafeFileName {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Value
    )

    return ($Value -replace '[\\/:*?"<>| ]', '_')
}


function Save-BoomiBackup {

    param(
        [Parameter(Mandatory=$true)]
        [string]$ComponentName,

        [Parameter(Mandatory=$true)]
        [string]$XmlContent,

        [Parameter(Mandatory=$true)]
        [string]$Reason
    )

    $safeName = Get-BoomiSafeFileName -Value $ComponentName
    $safeReason = Get-BoomiSafeFileName -Value $Reason

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $backupPath = Join-Path `
        "$script:WorkspaceRoot\backups" `
        "${timestamp}_${safeReason}_${safeName}.xml"

    [IO.File]::WriteAllText(
        $backupPath,
        $XmlContent,
        [Text.UTF8Encoding]::new($false)
    )

    return $backupPath
}


function Get-BoomiWriteHeaders {

    return @{
        Authorization  = $script:XmlHeaders.Authorization
        Accept         = "application/xml"
        "Content-Type" = "application/xml; charset=utf-8"
    }
}


# ============================================================
# CREATE EMPTY PROCESS
# ============================================================

function New-BoomiEmptyProcess {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Name,

        [Parameter(Mandatory=$true)]
        [string]$Folder
    )

    Write-Host ""
    Write-Host "SAFE CREATE - Empty Process"
    Write-Host "==========================="
    Write-Host ""

    Assert-BoomiWriteFolder -Folder $Folder

    Write-Host "Safety boundary : OK"

    $folderInfo = Get-BoomiFolderByFullPath `
        -FullPath $Folder

    Write-Host "Folder          : $($folderInfo.fullPath)"
    Write-Host "Folder ID       : $($folderInfo.id)"
    Write-Host ""

    if (Test-BoomiComponentNameExists -Name $Name) {
        throw "CREATE BLOCKED: A component named '$Name' already exists."
    }

    Write-Host "Duplicate check : OK"
    Write-Host ""

    $branchContext = Get-BoomiConfiguredBranchContext

    $BranchId = [string]$branchContext.Id

    if ([string]::IsNullOrWhiteSpace($BranchId)) {
        throw "CREATE BLOCKED: Configured branch ID is empty."
    }

    Write-Host "Branch          : $($branchContext.Name)"
    Write-Host "Branch ID       : $BranchId"
    Write-Host ""

    $escapedName = [Security.SecurityElement]::Escape($Name)

    $payload = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<bns:Component
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:bns="http://api.platform.boomi.com/"
    folderId="$($folderInfo.id)"
    name="$escapedName"
    type="process"
    branchId="$BranchId">

    <bns:encryptedValues/>

    <bns:description>
        Created by boomi-cli v1 SAFE WRITE.
    </bns:description>

    <bns:object>
        <process
            xmlns=""
            allowSimultaneous="false"
            enableUserLog="false"
            processLogOnErrorOnly="false"
            purgeDataImmediately="false"
            stopProcessingIfZeroDocuments="true"
            updateRunDates="false"
            workload="general">

            <shapes>

                <shape
                    image="start"
                    name="shape1"
                    shapetype="start"
                    userlabel=""
                    x="96.0"
                    y="94.0">

                    <configuration>
                        <passthroughaction/>
                    </configuration>

                    <dragpoints>
                        <dragpoint
                            name="shape1.dragpoint1"
                            toShape="shape2"
                            x="320.0"
                            y="104.0"/>
                    </dragpoints>

                </shape>

                <shape
                    image="returndocuments_icon"
                    name="shape2"
                    shapetype="returndocuments"
                    userlabel=""
                    x="336.0"
                    y="96.0">

                    <configuration>
                        <returndocuments label=""/>
                    </configuration>

                    <dragpoints/>

                </shape>

            </shapes>

        </process>
    </bns:object>

    <bns:processOverrides/>

</bns:Component>
"@

    try {
        [xml]$previewXml = $payload
    }
    catch {
        throw "Generated CREATE payload is not valid XML."
    }

    $shapes = @(
        $previewXml.SelectNodes(
            "//*[local-name()='shape']"
        )
    )

    if ($shapes.Count -ne 2) {
        throw "Generated process does not contain exactly 2 shapes."
    }

    Write-Host "XML validation  : OK"
    Write-Host "Shape count     : OK (2)"
    Write-Host ""

    $safeName = Get-BoomiSafeFileName -Value $Name

    $previewPath = Join-Path `
        "$script:WorkspaceRoot\templates" `
        "preview_create_${safeName}.xml"

    [IO.File]::WriteAllText(
        $previewPath,
        $payload,
        [Text.UTF8Encoding]::new($false)
    )

    Write-Host "Preview:"
    Write-Host "  $previewPath"
    Write-Host ""

    Write-Host "WRITE OPERATION"
    Write-Host "==============="
    Write-Host "Name   : $Name"
    Write-Host "Folder : $Folder"
    Write-Host "Flow   : Start - Data Passthrough -> Return Documents"
    Write-Host ""
    Write-Host "No deployment or execution will occur."
    Write-Host ""

    $confirmation = Read-Host "Type CREATE exactly to continue"

    if ($confirmation -cne "CREATE") {
        Write-Host ""
        Write-Host "CREATE cancelled."
        return
    }

    $writeHeaders = Get-BoomiWriteHeaders

    Write-Host ""
    Write-Host "Creating component..."

    $createResponse = Invoke-WebRequest `
        -Method Post `
        -Uri "$script:BaseUrl/Component" `
        -Headers $writeHeaders `
        -Body ([Text.Encoding]::UTF8.GetBytes($payload)) `
        -UseBasicParsing

    [xml]$createdXml = $createResponse.Content

    $newId = [string]$createdXml.Component.componentId

    if ([string]::IsNullOrWhiteSpace($newId)) {
        throw "CREATE returned no componentId."
    }

    Write-Host "Boomi returned Component ID:"
    Write-Host "  $newId"
    Write-Host ""

    $verifyResponse = Get-BoomiComponentXml `
        -ComponentId $newId

    [xml]$verifyXml = $verifyResponse.Content
    $actual = $verifyXml.Component

    $failed = $false

    if ($actual.name -eq $Name) {
        Write-Host "Name verification   : OK"
    }
    else {
        Write-Host "Name verification   : FAILED"
        $failed = $true
    }

    if ($actual.type -eq "process") {
        Write-Host "Type verification   : OK"
    }
    else {
        Write-Host "Type verification   : FAILED"
        $failed = $true
    }

    if ($actual.folderFullPath -eq $Folder) {
        Write-Host "Folder verification : OK"
    }
    else {
        Write-Host "Folder verification : FAILED"
        Write-Host "Actual folder       : $($actual.folderFullPath)"
        $failed = $true
    }

    $actualShapes = @(
        $verifyXml.SelectNodes(
            "//*[local-name()='shape']"
        )
    )

    if ($actualShapes.Count -eq 2) {
        Write-Host "Shape verification  : OK (2)"
    }
    else {
        Write-Host "Shape verification  : FAILED"
        $failed = $true
    }

    $exportPath = Join-Path `
        "$script:WorkspaceRoot\exports" `
        "verified_create_${safeName}.xml"

    [IO.File]::WriteAllText(
        $exportPath,
        $verifyResponse.Content,
        [Text.UTF8Encoding]::new($false)
    )

    Write-Host ""
    Write-Host "Authoritative XML:"
    Write-Host "  $exportPath"
    Write-Host ""

    if ($failed) {
        Write-Host "RESULT: CREATED, BUT VERIFICATION FAILED"
        Write-Host "Do NOT rerun CREATE."
    }
    else {
        Write-Host "RESULT: CREATE VERIFIED SUCCESSFULLY"
        Write-Host ""
        Write-Host "Component ID:"
        Write-Host "  $newId"
    }
}


# ============================================================
# SET PROCESS SHAPE LABEL
# ============================================================

function Set-BoomiProcessShapeLabel {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id,

        [Parameter(Mandatory=$true)]
        [string]$Shape,

        [Parameter(Mandatory=$true)]
        [AllowEmptyString()]
        [string]$Label
    )

    Write-Host ""
    Write-Host "SAFE UPDATE - Process Shape Label"
    Write-Host "================================="
    Write-Host ""

    $getResponse = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$xml = $getResponse.Content
    $component = $xml.Component

    Write-Host "Component : $($component.name)"
    Write-Host "ID        : $($component.componentId)"
    Write-Host "Version   : $($component.version)"
    Write-Host "Folder    : $($component.folderFullPath)"
    Write-Host ""

    Assert-BoomiWriteFolder `
        -Folder ([string]$component.folderFullPath)

    Write-Host "Safety boundary : OK"

    if ($component.type -ne "process") {
        throw "UPDATE BLOCKED: Component is not a process."
    }

    $shapeNodes = @(
        $xml.SelectNodes(
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

    $oldUserLabel = [string]$shapeNode.userlabel
    $shapeType = [string]$shapeNode.shapetype

    $oldConfigLabel = $null
    $returnConfig = $null

    if ($shapeType -eq "returndocuments") {

        $returnConfig = $shapeNode.SelectSingleNode(
            "./*[local-name()='configuration']/*[local-name()='returndocuments']"
        )

        if (-not $returnConfig) {
            throw "UPDATE BLOCKED: Return Documents configuration was not found."
        }

        $oldConfigLabel = [string]$returnConfig.label
    }

    Write-Host "Shape             : $Shape"
    Write-Host "Shape type        : $shapeType"
    Write-Host "Current userlabel : '$oldUserLabel'"

    if ($shapeType -eq "returndocuments") {
        Write-Host "Current cfg label : '$oldConfigLabel'"
    }

    Write-Host "Requested label   : '$Label'"
    Write-Host ""

    $alreadyMatches = $false

    if ($shapeType -eq "returndocuments") {
        $alreadyMatches = (
            $oldUserLabel -eq $Label -and
            $oldConfigLabel -eq $Label
        )
    }
    else {
        $alreadyMatches = ($oldUserLabel -eq $Label)
    }

    if ($alreadyMatches) {
        Write-Host "NO CHANGE REQUIRED."
        Write-Host "The requested label already matches the current stored values."
        return
    }

    $backupPath = Save-BoomiBackup `
        -ComponentName ([string]$component.name) `
        -XmlContent $getResponse.Content `
        -Reason "before_set_label"

    Write-Host "Backup:"
    Write-Host "  $backupPath"
    Write-Host ""

    # --------------------------------------------------------
    # Modify shape-level userlabel
    # --------------------------------------------------------

    $shapeNode.SetAttribute(
        "userlabel",
        $Label
    )

    # --------------------------------------------------------
    # Shape-type-aware configuration update
    #
    # CONFIRMED for Return Documents from GUI vs API XML diff:
    #
    # shape/@userlabel
    # +
    # configuration/returndocuments/@label
    #
    # are both updated by Boomi GUI Display Name save.
    # --------------------------------------------------------

    if ($shapeType -eq "returndocuments") {

        $returnConfig.SetAttribute(
            "label",
            $Label
        )
    }

    $safeName = Get-BoomiSafeFileName `
        -Value ([string]$component.name)

    $previewPath = Join-Path `
        "$script:WorkspaceRoot\templates" `
        "preview_set_label_${safeName}_${Shape}.xml"

    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
    $settings.Indent = $false
    $settings.OmitXmlDeclaration = $false

    $writer = [System.Xml.XmlWriter]::Create(
        $previewPath,
        $settings
    )

    try {
        $xml.Save($writer)
    }
    finally {
        $writer.Close()
    }

    [xml]$previewXml = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $previewTarget = @(
        $previewXml.SelectNodes(
            "//*[local-name()='shape'][@name='$Shape']"
        )
    )

    if ($previewTarget.Count -ne 1) {
        throw "UPDATE BLOCKED: Preview target shape validation failed."
    }

    if ([string]$previewTarget[0].userlabel -ne $Label) {
        throw "UPDATE BLOCKED: Preview userlabel validation failed."
    }

    if ($shapeType -eq "returndocuments") {

        $previewReturnConfig = $previewTarget[0].SelectSingleNode(
            "./*[local-name()='configuration']/*[local-name()='returndocuments']"
        )

        if (-not $previewReturnConfig) {
            throw "UPDATE BLOCKED: Preview Return Documents configuration is missing."
        }

        if ([string]$previewReturnConfig.label -ne $Label) {
            throw "UPDATE BLOCKED: Preview Return Documents label validation failed."
        }
    }

    Write-Host "Preview validation : OK"

    if ($shapeType -eq "returndocuments") {
        Write-Host "userlabel          : OK"
        Write-Host "config label       : OK"
    }

    Write-Host "Preview:"
    Write-Host "  $previewPath"
    Write-Host ""

    Write-Host "UPDATE OPERATION"
    Write-Host "================"
    Write-Host "Component : $($component.name)"
    Write-Host "ID        : $Id"
    Write-Host "Folder    : $($component.folderFullPath)"
    Write-Host "Shape     : $Shape"
    Write-Host "Type      : $shapeType"
    Write-Host ""
    Write-Host "Requested Display Name:"
    Write-Host "  '$Label'"
    Write-Host ""

    if ($shapeType -eq "returndocuments") {
        Write-Host "The following confirmed XML values will be synchronized:"
        Write-Host "  shape/@userlabel"
        Write-Host "  configuration/returndocuments/@label"
        Write-Host ""
    }
    else {
        Write-Host "The following XML value will be updated:"
        Write-Host "  shape/@userlabel"
        Write-Host ""
        Write-Host "Additional Display Name fields for this shape type are"
        Write-Host "NOT assumed without evidence."
        Write-Host ""
    }

    Write-Host "No deployment or execution will occur."
    Write-Host ""

    $confirmation = Read-Host "Type UPDATE exactly to continue"

    if ($confirmation -cne "UPDATE") {
        Write-Host ""
        Write-Host "UPDATE cancelled."
        return
    }

    $updatePayload = [IO.File]::ReadAllText(
        $previewPath,
        [Text.Encoding]::UTF8
    )

    $writeHeaders = Get-BoomiWriteHeaders

    Write-Host ""
    Write-Host "Updating component..."

    $updateResponse = Invoke-WebRequest `
        -Method Post `
        -Uri "$script:BaseUrl/Component/$Id/update" `
        -Headers $writeHeaders `
        -Body ([Text.Encoding]::UTF8.GetBytes($updatePayload)) `
        -UseBasicParsing

    Write-Host "Boomi accepted the Component UPDATE."
    Write-Host ""

    $verifyResponse = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$verifyXml = $verifyResponse.Content
    $actual = $verifyXml.Component

    $actualTarget = @(
        $verifyXml.SelectNodes(
            "//*[local-name()='shape'][@name='$Shape']"
        )
    )

    $failed = $false

    if ($actual.componentId -eq $Id) {
        Write-Host "Component ID : OK"
    }
    else {
        Write-Host "Component ID : FAILED"
        $failed = $true
    }

    if (
        [string]$actual.folderFullPath -ceq
        [string]$component.folderFullPath
    ) {
        Write-Host "Folder       : OK"
    }
    else {
        Write-Host "Folder       : FAILED"
        Write-Host "Expected     : $($component.folderFullPath)"
        Write-Host "Actual       : $($actual.folderFullPath)"
        $failed = $true
    }

    if ($actualTarget.Count -ne 1) {

        Write-Host "Target shape : FAILED"
        $failed = $true
    }
    else {

        $actualUserLabel = [string]$actualTarget[0].userlabel

        if ($actualUserLabel -eq $Label) {
            Write-Host "userlabel    : OK ('$actualUserLabel')"
        }
        else {
            Write-Host "userlabel    : FAILED ('$actualUserLabel')"
            $failed = $true
        }

        if ($shapeType -eq "returndocuments") {

            $actualReturnConfig = $actualTarget[0].SelectSingleNode(
                "./*[local-name()='configuration']/*[local-name()='returndocuments']"
            )

            if (-not $actualReturnConfig) {

                Write-Host "config label : FAILED (configuration missing)"
                $failed = $true
            }
            else {

                $actualConfigLabel = [string]$actualReturnConfig.label

                if ($actualConfigLabel -eq $Label) {
                    Write-Host "config label : OK ('$actualConfigLabel')"
                }
                else {
                    Write-Host "config label : FAILED ('$actualConfigLabel')"
                    $failed = $true
                }
            }
        }
    }

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $verifiedPath = Join-Path `
        "$script:WorkspaceRoot\exports" `
        "${timestamp}_verified_set_label_${safeName}_${Shape}.xml"

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
        Write-Host "RESULT: UPDATE VERIFIED SUCCESSFULLY"
        Write-Host ""
        Write-Host "New Version:"
        Write-Host "  $($actual.version)"
    }
}
