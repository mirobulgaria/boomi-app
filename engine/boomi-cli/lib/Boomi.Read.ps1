# ============================================================
# Boomi.Read.ps1
# boomi-cli v1 READ operations
#
# Uses Get-BoomiComponentXml from Boomi.Common.ps1.
# XML is therefore decoded explicitly as UTF-8.
#
# READ capabilities:
#   search
#   get
#   export
#   inspect
#   list-environments
# ============================================================


function Search-BoomiComponent {

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
        -Body ([Text.Encoding]::UTF8.GetBytes($body))

    Write-Host ""
    Write-Host "Boomi Component Search"
    Write-Host "======================"
    Write-Host "Results: $($response.numberOfResults)"
    Write-Host ""

    if ($response.numberOfResults -gt 0) {

        $response.result |
            Select-Object `
                name,
                type,
                folderName,
                componentId,
                currentVersion,
                deleted |
            Format-Table -AutoSize
    }
}


function Show-BoomiComponent {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id
    )

    $response = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$xml = $response.Content
    $component = $xml.Component

    Write-Host ""
    Write-Host "Boomi Component"
    Write-Host "==============="
    Write-Host "Name            : $($component.name)"
    Write-Host "Type            : $($component.type)"
    Write-Host "Component ID    : $($component.componentId)"
    Write-Host "Version         : $($component.version)"
    Write-Host "Current Version : $($component.currentVersion)"
    Write-Host "Deleted         : $($component.deleted)"
    Write-Host "Folder          : $($component.folderFullPath)"
    Write-Host "Branch          : $($component.branchName)"
    Write-Host ""
}


function Export-BoomiComponent {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id
    )

    $response = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$xml = $response.Content
    $component = $xml.Component

    $safeName = (
        [string]$component.name -replace '[\\/:*?"<>| ]', '_'
    )

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

    $path = Join-Path `
        "$script:WorkspaceRoot\exports" `
        "${timestamp}_export_${safeName}.xml"

    Write-BoomiUtf8File `
        -Path $path `
        -Content $response.Content

    Write-Host ""
    Write-Host "Component exported successfully."
    Write-Host "UTF-8 Mode : explicit"
    Write-Host "Name       : $($component.name)"
    Write-Host "Version    : $($component.version)"
    Write-Host "File       : $path"
    Write-Host ""

    return $path
}


function Inspect-BoomiProcess {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id
    )

    $response = Get-BoomiComponentXml `
        -ComponentId $Id

    [xml]$xml = $response.Content
    $component = $xml.Component

    if ($component.type -ne "process") {
        throw "Component is not a process."
    }

    $ns = New-Object System.Xml.XmlNamespaceManager(
        $xml.NameTable
    )

    $ns.AddNamespace(
        "bns",
        "http://api.platform.boomi.com/"
    )

    $processNode = $xml.SelectSingleNode(
        "//bns:object/*[local-name()='process']",
        $ns
    )

    if (-not $processNode) {
        throw "Process definition not found."
    }

    Write-Host ""
    Write-Host "Boomi Process Inspector"
    Write-Host "======================="
    Write-Host "Process : $($component.name)"
    Write-Host "ID      : $($component.componentId)"
    Write-Host "Version : $($component.version)"
    Write-Host "Folder  : $($component.folderFullPath)"
    Write-Host ""

    $shapes = @(
        $processNode.SelectNodes(
            "./*[local-name()='shapes']/*[local-name()='shape']"
        )
    )

    foreach ($shape in $shapes) {

        $type = [string]$shape.shapetype
        $label = [string]$shape.userlabel

        Write-Host "Shape: $($shape.name)"
        Write-Host "  Type  : $type"

        if (-not [string]::IsNullOrWhiteSpace($label)) {
            Write-Host "  Label : $label"
        }

        switch ($type) {

            "start" {

                $connector = $shape.SelectSingleNode(
                    ".//*[local-name()='connectoraction']"
                )

                if ($connector) {

                    $connection = Get-BoomiComponentInfo `
                        -ComponentId $connector.connectionId

                    $operation = Get-BoomiComponentInfo `
                        -ComponentId $connector.operationId

                    Write-Host "  Action     : $($connector.actionType)"
                    Write-Host "  Connection : $($connection.Name)"
                    Write-Host "  Operation  : $($operation.Name)"
                }
                else {
                    Write-Host "  Detail     : Data Passthrough / No connector"
                }
            }

            "processcall" {

                $node = $shape.SelectSingleNode(
                    ".//*[local-name()='processcall']"
                )

                $info = Get-BoomiComponentInfo `
                    -ComponentId $node.processId

                Write-Host "  Process Call : $($info.Name)"
            }

            "map" {

                $node = $shape.SelectSingleNode(
                    ".//*[local-name()='map']"
                )

                $info = Get-BoomiComponentInfo `
                    -ComponentId $node.mapId

                Write-Host "  Map : $($info.Name)"
            }

            "connectoraction" {

                $node = $shape.SelectSingleNode(
                    ".//*[local-name()='connectoraction']"
                )

                $connection = Get-BoomiComponentInfo `
                    -ComponentId $node.connectionId

                $operation = Get-BoomiComponentInfo `
                    -ComponentId $node.operationId

                Write-Host "  Action     : $($node.actionType)"
                Write-Host "  Connection : $($connection.Name)"
                Write-Host "  Operation  : $($operation.Name)"
            }

            "returndocuments" {
                Write-Host "  Detail : Return Documents"
            }
        }

        Write-Host ""
    }
}


# ============================================================
# Environment query helper
#
# Windows PowerShell 5.1 compatibility:
# use normal PowerShell arrays instead of generic List[object].
# ============================================================

function Get-BoomiEnvironmentsByClassification {

    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("TEST", "PROD")]
        [string]$Classification
    )

    $body = @{
        QueryFilter = @{
            expression = @{
                property = "classification"
                operator = "EQUALS"
                argument = @($Classification)
            }
        }
    } | ConvertTo-Json -Depth 10

    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "$script:BaseUrl/Environment/query" `
        -Headers $script:JsonHeaders `
        -Body ([Text.Encoding]::UTF8.GetBytes($body))

    $results = @()

    if ($null -ne $response.result) {

        foreach ($item in @($response.result)) {

            if ($null -ne $item) {
                $results += $item
            }
        }
    }

    # --------------------------------------------------------
    # Preserve queryToken handling.
    # This path is used only if Boomi returns another page.
    # --------------------------------------------------------

    $queryToken = [string]$response.queryToken

    while (-not [string]::IsNullOrWhiteSpace($queryToken)) {

        $queryMoreHeaders = @{}

        foreach ($key in $script:JsonHeaders.Keys) {
            $queryMoreHeaders[$key] = $script:JsonHeaders[$key]
        }

        $queryMoreHeaders["Content-Type"] = "text/plain; charset=utf-8"

        $nextResponse = Invoke-RestMethod `
            -Method Post `
            -Uri "$script:BaseUrl/Environment/queryMore" `
            -Headers $queryMoreHeaders `
            -Body ([Text.Encoding]::UTF8.GetBytes($queryToken))

        if ($null -ne $nextResponse.result) {

            foreach ($item in @($nextResponse.result)) {

                if ($null -ne $item) {
                    $results += $item
                }
            }
        }

        $queryToken = [string]$nextResponse.queryToken
    }

    return $results
}


function Show-BoomiEnvironments {

    Write-Host ""
    Write-Host "Boomi Environments"
    Write-Host "=================="

    $testEnvironments = @(
        Get-BoomiEnvironmentsByClassification `
            -Classification "TEST"
    )

    $prodEnvironments = @(
        Get-BoomiEnvironmentsByClassification `
            -Classification "PROD"
    )

    $allEnvironments = @()

    foreach ($item in $testEnvironments) {

        if ($null -ne $item) {
            $allEnvironments += $item
        }
    }

    foreach ($item in $prodEnvironments) {

        if ($null -ne $item) {
            $allEnvironments += $item
        }
    }

    $uniqueEnvironments = @(
        $allEnvironments |
            Where-Object {
                $null -ne $_ -and
                -not [string]::IsNullOrWhiteSpace(
                    [string]$_.id
                )
            } |
            Sort-Object id -Unique |
            Sort-Object classification, name
    )

    Write-Host ""
    Write-Host "Results : $($uniqueEnvironments.Count)"
    Write-Host ""

    if ($uniqueEnvironments.Count -eq 0) {

        Write-Host "No environments were returned."
        Write-Host ""
        Write-Host "READ ONLY."
        Write-Host "No environment configuration was modified."
        Write-Host ""

        return
    }

    $uniqueEnvironments |
        Select-Object `
            name,
            id,
            classification |
        Format-Table -AutoSize

    Write-Host ""
    Write-Host "READ ONLY."
    Write-Host "No environment configuration was modified."
    Write-Host ""
}