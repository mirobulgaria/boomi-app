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
#   get-definition
#   export
#   inspect
#   list-environments
# ============================================================


function Get-BoomiComponentMetadata {

    <#
    .SYNOPSIS
    Retrieves complete ComponentMetadata inventory using pagination.

    .DESCRIPTION
    Performs full pagination of ComponentMetadata/query and
    ComponentMetadata/queryMore with an empty QueryFilter.
    Returns the complete unfiltered metadata collection.

    The pagination contract:
    - POST ComponentMetadata/query with empty QueryFilter
    - UTF-8 JSON request body
    - POST ComponentMetadata/queryMore with text/plain; charset=utf-8
    - Raw UTF-8 queryToken body
    - Accumulate all results
    - Terminate on empty queryToken

    .OUTPUTS
    Array of metadata objects.
    Also returns reported result count via output metadata.
    #>

    # --------------------------------------------------------
    # Initial query
    # --------------------------------------------------------

    $body = @{
        QueryFilter = @{}
    } | ConvertTo-Json -Depth 10

    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "$script:BaseUrl/ComponentMetadata/query" `
        -Headers $script:JsonHeaders `
        -Body (
            [Text.Encoding]::UTF8.GetBytes(
                $body
            )
        )

    # --------------------------------------------------------
    # Accumulate first page
    # --------------------------------------------------------

    $results = @()

    if ($null -ne $response.result) {

        foreach ($item in @($response.result)) {

            if ($null -ne $item) {
                $results += $item
            }
        }
    }

    $initialResultCount = $results.Count

    $reportedResultCount = $null

    if (
        $null -ne
        $response.PSObject.Properties["numberOfResults"]
    ) {
        $reportedResultCount = [int]$response.numberOfResults
    }

    $queryToken = [string]$response.queryToken

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    while (
        -not [string]::IsNullOrWhiteSpace(
            $queryToken
        )
    ) {

        $queryMoreHeaders = @{}

        foreach ($key in $script:JsonHeaders.Keys) {
            $queryMoreHeaders[$key] = $script:JsonHeaders[$key]
        }

        $queryMoreHeaders["Content-Type"] = `
            "text/plain; charset=utf-8"

        $nextResponse = Invoke-RestMethod `
            -Method Post `
            -Uri "$script:BaseUrl/ComponentMetadata/queryMore" `
            -Headers $queryMoreHeaders `
            -Body (
                [Text.Encoding]::UTF8.GetBytes(
                    $queryToken
                )
            )

        if ($null -ne $nextResponse.result) {

            foreach ($item in @($nextResponse.result)) {

                if ($null -ne $item) {
                    $results += $item
                }
            }
        }

        $queryToken = [string]$nextResponse.queryToken
    }

    # Return results with metadata
    return @{
        Results = $results
        ReportedCount = $reportedResultCount
    }
}


function Invoke-BoomiCapabilityInventoryProbe {

    Write-Host ""
    Write-Host "Boomi Capability Inventory"
    Write-Host "=========================="
    Write-Host ""
    Write-Host "Stage                    : full metadata inventory"
    Write-Host "Object                   : ComponentMetadata"
    Write-Host "Operation                : QUERY + queryMore"
    Write-Host "Component definitions    : NOT REQUESTED"
    Write-Host "Mutation operations      : NONE"
    Write-Host ""

    try {

        $metadata = Get-BoomiComponentMetadata

        $results = $metadata.Results
        $reportedResultCount = $metadata.ReportedCount

        Write-Host "ComponentMetadata/query  : ACCEPTED"
    }
    catch {

        Write-Host "ComponentMetadata/query  : REJECTED"
        Write-Host "Definitions requested    : 0"
        Write-Host "Mutation calls            : 0"

        throw "CAPABILITY INVENTORY: ComponentMetadata retrieval failed."
    }

    # --------------------------------------------------------
    # Completeness gates
    # --------------------------------------------------------

    Write-Host ""
    Write-Host "===== INVENTORY COMPLETENESS ====="

    Write-Host "Metadata objects scanned : $($results.Count)"

    if ($results.Count -eq 0) {
        throw "CAPABILITY INVENTORY: No metadata objects returned."
    }

    Write-Host "Pagination terminated    : PASS"

    if ($null -ne $reportedResultCount) {
        Write-Host "API reported results     : $reportedResultCount"

        if ($results.Count -ne $reportedResultCount) {
            throw (
                "CAPABILITY INVENTORY: Accumulated metadata count " +
                "$($results.Count) does not match API-reported " +
                "count $reportedResultCount."
            )
        }

        Write-Host "Result count match       : PASS"
    }
    else {
        Write-Host "API reported results     : <not present>"
        Write-Host "Result count match       : NOT AVAILABLE"
    }

    # --------------------------------------------------------
    # Component type aggregation
    # --------------------------------------------------------

    $typeCounts = @(
        $results |
            Where-Object {
                $null -ne
                $_.PSObject.Properties["type"]
            } |
            Group-Object -Property type |
            Sort-Object Name
    )

    Write-Host ""
    Write-Host "===== COMPONENT TYPES ====="

    if ($typeCounts.Count -eq 0) {

        Write-Host "  <none>"
    }
    else {

        foreach ($group in $typeCounts) {

            Write-Host (
                "  {0,-30} {1}" -f `
                    [string]$group.Name,
                    $group.Count
            )
        }
    }

    # --------------------------------------------------------
    # Process inventory
    # --------------------------------------------------------

    $processes = @(
        $results |
            Where-Object {
                [string]$_.type -eq "process"
            }
    )

    $deletedProcesses = @(
        $processes |
            Where-Object {

                $deletedProperty = `
                    $_.PSObject.Properties["deleted"]

                if ($null -eq $deletedProperty) {
                    return $false
                }

                return (
                    [string]$deletedProperty.Value
                ).ToLowerInvariant() -eq "true"
            }
    )

    $activeProcesses = @(
        $processes |
            Where-Object {

                $deletedProperty = `
                    $_.PSObject.Properties["deleted"]

                if ($null -eq $deletedProperty) {
                    return $true
                }

                return (
                    [string]$deletedProperty.Value
                ).ToLowerInvariant() -ne "true"
            }
    )

    Write-Host ""
    Write-Host "===== PROCESS INVENTORY ====="
    Write-Host "Process components       : $($processes.Count)"
    Write-Host "Deleted processes        : $($deletedProcesses.Count)"
    Write-Host "Active processes         : $($activeProcesses.Count)"

    if (
        (
            $deletedProcesses.Count +
            $activeProcesses.Count
        ) -ne
        $processes.Count
    ) {
        throw "CAPABILITY INVENTORY: Process classification count mismatch."
    }

    Write-Host "Process count integrity  : PASS"

    # --------------------------------------------------------
    # Security / read boundary
    # --------------------------------------------------------

    Write-Host ""
    Write-Host "===== SECURITY ====="
    Write-Host "Component names printed  : False"
    Write-Host "Component IDs printed    : False"
    Write-Host "Folder names printed     : False"
    Write-Host "Definitions printed      : False"
    Write-Host "Business data printed    : False"
    Write-Host "Credentials printed      : False"

    Write-Host ""
    Write-Host "===== API OPERATION COUNTS ====="
    Write-Host "Initial metadata queries : 1"
    Write-Host "queryMore calls          : <computed by pagination>"
    Write-Host "Component GET calls      : 0"
    Write-Host "Definitions requested    : 0"
    Write-Host "Mutation calls            : 0"

    Write-Host ""
    Write-Host "CAPABILITY INVENTORY : PASS"
}

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


function Write-BoomiComponentHuman {

    param(
        [Parameter(Mandatory=$true)]
        [PSObject]$Component
    )

    Write-Host ""
    Write-Host "Boomi Component"
    Write-Host "==============="
    Write-Host "Name            : $($Component.Name)"
    Write-Host "Type            : $($Component.Type)"
    Write-Host "Component ID    : $($Component.ComponentId)"
    Write-Host "Version         : $($Component.Version)"
    Write-Host "Current Version : $($Component.CurrentVersion.ToString().ToLowerInvariant())"
    Write-Host "Deleted         : $($Component.Deleted.ToString().ToLowerInvariant())"
    Write-Host "Folder          : $($Component.FolderFullPath)"
    Write-Host "Branch          : $($Component.BranchName)"
    Write-Host ""
}


function Show-BoomiComponent {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id
    )

    $component = Get-BoomiComponentInfo `
        -ComponentId $Id

    Write-BoomiComponentHuman `
        -Component $component
}


function Convert-BoomiComponentInfoToJson {

    param(
        [Parameter(Mandatory=$true)]
        [PSObject]$Component
    )

    $result = [ordered]@{
        success   = $true
        operation = "get"
        data      = [ordered]@{
            componentId    = [string]$Component.ComponentId
            name           = [string]$Component.Name
            type           = [string]$Component.Type
            version        = [int]$Component.Version
            currentVersion = [bool]$Component.CurrentVersion
            deleted        = [bool]$Component.Deleted
            folderFullPath = [string]$Component.FolderFullPath
            branchName     = [string]$Component.BranchName
        }
    }

    return (
        $result |
            ConvertTo-Json `
                -Depth 10 `
                -Compress
    )
}


function Get-BoomiComponentDefinitionXml {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Id
    )

    $response = Get-BoomiComponentXml `
        -ComponentId $Id

    if (
        $null -eq $response -or
        [string]::IsNullOrWhiteSpace(
            [string]$response.Content
        )
    ) {
        throw "Boomi component definition was empty."
    }

    [xml]$xml = $response.Content

    if ($null -eq $xml.Component) {
        throw "Boomi component definition root was not Component."
    }

    $actualId = [string]$xml.Component.componentId

    if ($actualId -ne $Id) {
        throw "Boomi component definition ID did not match the requested ID."
    }

    if ($null -eq $xml.Component.object) {
        throw "Boomi component definition object was not found."
    }

    # Write the raw Component XML to the success output stream.
    #
    # Do not use Write-Host here. The application consumes stdout
    # as a machine-readable XML contract.
    return [string]$response.Content
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

    param(
        [Parameter()]
        [ValidateSet(
            "human",
            "json"
        )]
        [string]$OutputFormat = "human"
    )

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

    if ($OutputFormat -eq "json") {

        $data = @(
            $uniqueEnvironments |
                ForEach-Object {
                    [ordered]@{
                        id = [string]$_.id
                        name = [string]$_.name
                        classification = [string]$_.classification
                    }
                }
        )

        $payload = [ordered]@{
            success = $true
            operation = "list-environments"
            data = $data
        }

        $payload |
            ConvertTo-Json `
                -Depth 8 `
                -Compress

        return
    }

    Write-Host ""
    Write-Host "Boomi Environments"
    Write-Host "=================="

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


# ============================================================
# Process definition corpus
# ============================================================

function Get-ProcessShapeStructuralFingerprint {

    <#
    .SYNOPSIS
    Extracts structural fingerprint from a process shape configuration.

    .DESCRIPTION
    Traverses configuration XML recursively and extracts ONLY structural
    information: element names, attribute names, hierarchy, cardinality.
    No attribute values, element text, or business data are included.

    .PARAMETER ConfigurationNode
    The configuration XML node to fingerprint.

    .OUTPUTS
    String representing the structural fingerprint.
    #>

    param(
        [Parameter(Mandatory=$true)]
        [System.Xml.XmlNode]$ConfigurationNode
    )

    if ($null -eq $ConfigurationNode) {
        return ""
    }

    $fingerprintParts = @()

    # Element name
    $elementName = $ConfigurationNode.LocalName
    $fingerprintParts += "E:$elementName"

    # Attribute names (sorted deterministically)
    $attributeNames = @(
        $ConfigurationNode.Attributes |
            ForEach-Object { $_.LocalName } |
            Sort-Object
    )

    if ($attributeNames.Count -gt 0) {
        $fingerprintParts += "A:($($attributeNames -join ','))"
    }

    # Child elements (recursive)
    $childFingerprints = @(
        $ConfigurationNode.ChildNodes |
            Where-Object {
                $_ -is [System.Xml.XmlElement]
            } |
            ForEach-Object {
                Get-ProcessShapeStructuralFingerprint `
                    -ConfigurationNode $_
            }
    )

    if ($childFingerprints.Count -gt 0) {
        $fingerprintParts += "C:($($childFingerprints -join '|'))"
    }

    return $fingerprintParts -join ';'
}


function Invoke-BoomiProcessDefinitionCorpusProbe {

    <#
    .SYNOPSIS
    Bounded read-only probe of process definition structural variants.

    .DESCRIPTION
    Retrieves a bounded sample (max 10) of active process definitions,
    extracts structural fingerprints from shapes, and reports observed
    serialization variants without exposing business values.

    Fixed Stage 2B.1 bound: 10 definitions maximum.
    #>

    Write-Host ""
    Write-Host "Boomi Process Definition Corpus"
    Write-Host "=============================="
    Write-Host ""
    Write-Host "Stage                    : bounded structural evidence"
    Write-Host "Object                   : Process definitions"
    Write-Host "Operation                : Component GET (max 10)"
    Write-Host "Mutation operations      : NONE"
    Write-Host ""
    Write-Host "Definition limit         : 10"
    Write-Host ""

    # --------------------------------------------------------
    # Retrieve complete metadata
    # --------------------------------------------------------

    try {

        $metadata = Get-BoomiComponentMetadata
        $allMetadata = $metadata.Results

        Write-Host "ComponentMetadata/query  : ACCEPTED"
    }
    catch {

        Write-Host "ComponentMetadata/query  : REJECTED"
        Write-Host "Definitions requested    : 0"
        Write-Host "Mutation calls            : 0"

        throw "CORPUS PROBE: ComponentMetadata retrieval failed."
    }

    # --------------------------------------------------------
    # Select active processes deterministically
    # --------------------------------------------------------

    $activeProcesses = @(
        $allMetadata |
            Where-Object {
                [string]$_.type -eq "process"
            } |
            Where-Object {

                $deletedProperty = `
                    $_.PSObject.Properties["deleted"]

                if ($null -eq $deletedProperty) {
                    return $true
                }

                return (
                    [string]$deletedProperty.Value
                ).ToLowerInvariant() -ne "true"
            }
    )

    Write-Host "Active processes found     : $($activeProcesses.Count)"

    if ($activeProcesses.Count -eq 0) {
        throw "CORPUS PROBE: No active processes found."
    }

    # Sort by componentId for deterministic selection
    $activeProcesses = @(
        $activeProcesses |
            Sort-Object -Property componentId
    )

    # Hard bounded sample: first 10
    $definitionsRequested = 10

    if ($activeProcesses.Count -lt $definitionsRequested) {
        $definitionsRequested = $activeProcesses.Count
    }

    $selectedProcesses = $activeProcesses[0..($definitionsRequested - 1)]

    Write-Host "Definitions requested      : $definitionsRequested"

    # --------------------------------------------------------
    # Retrieve and parse definitions
    # --------------------------------------------------------

    $definitionsParsed = 0
    $totalShapesObserved = 0
    $shapeTypeInventory = @{}
    $shapeFingerprints = @{}

    foreach ($processMeta in $selectedProcesses) {

        $componentId = [string]$processMeta.componentId

        try {

            $response = Get-BoomiComponentXml `
                -ComponentId $componentId

            [xml]$definitionXml = $response.Content

            if ($null -eq $definitionXml.Component) {
                throw "Component root not found."
            }

            $returnedId = [string]$definitionXml.Component.componentId

            if ($returnedId -ne $componentId) {
                throw "Component ID mismatch."
            }

            if ($null -eq $definitionXml.Component.object) {
                throw "Component object not found."
            }

            $definitionsParsed++

            # --------------------------------------------------------
            # Extract shape structures
            # --------------------------------------------------------

            $ns = New-Object System.Xml.XmlNamespaceManager(
                $definitionXml.NameTable
            )

            $ns.AddNamespace(
                "bns",
                "http://api.platform.boomi.com/"
            )

            $processNode = $definitionXml.SelectSingleNode(
                "//bns:object/*[local-name()='process']",
                $ns
            )

            if ($null -eq $processNode) {
                throw "Process definition not found."
            }

            $shapes = @(
                $processNode.SelectNodes(
                    "./*[local-name()='shapes']/*[local-name()='shape']"
                )
            )

            foreach ($shape in $shapes) {

                $totalShapesObserved++

                $shapeType = [string]$shape.shapetype

                if ([string]::IsNullOrWhiteSpace($shapeType)) {
                    $shapeType = "<unknown>"
                }

                if (-not $shapeTypeInventory.ContainsKey($shapeType)) {
                    $shapeTypeInventory[$shapeType] = 0
                }

                $shapeTypeInventory[$shapeType]++

                # Extract configuration fingerprint
                $configNode = $shape.SelectSingleNode(
                    "./*[local-name()='configuration']"
                )

                $fingerprint = ""

                if ($null -ne $configNode) {
                    $fingerprint = Get-ProcessShapeStructuralFingerprint `
                        -ConfigurationNode $configNode
                }
                else {
                    $fingerprint = "<no-configuration>"
                }

                $fingerprintKey = "$shapeType|$fingerprint"

                if (-not $shapeFingerprints.ContainsKey($fingerprintKey)) {
                    $shapeFingerprints[$fingerprintKey] = 0
                }

                $shapeFingerprints[$fingerprintKey]++
            }
        }
        catch {

            Write-Host ""
            Write-Host "CORPUS PROBE FAILED"
            Write-Host "Definitions parsed        : $definitionsParsed"
            Write-Host "Failed at definition      : NOT PRINTED"
            Write-Host ""
            Write-Host "Error:"
            Write-Host $_
            Write-Host ""

            throw "CORPUS PROBE: Definition parsing failed."
        }
    }

    Write-Host "Definitions parsed        : $definitionsParsed"

    if ($definitionsParsed -ne $definitionsRequested) {
        throw "CORPUS PROBE: Not all requested definitions were parsed."
    }

    # --------------------------------------------------------
    # Report evidence
    # --------------------------------------------------------

    Write-Host ""
    Write-Host "===== STRUCTURAL EVIDENCE ====="
    Write-Host "Shapes observed           : $totalShapesObserved"
    Write-Host "Distinct shapetypes        : $($shapeTypeInventory.Count)"
    Write-Host "Total fingerprints        : $($shapeFingerprints.Count)"

    Write-Host ""
    Write-Host "===== SHAPETYPE INVENTORY ====="

    foreach ($shapeType in $shapeTypeInventory.Keys | Sort-Object) {
        $count = $shapeTypeInventory[$shapeType]

        Write-Host ""
        Write-Host "Shape type               : $shapeType"
        Write-Host "Observed instances       : $count"

        # Count fingerprints for this shapetype
        $typeFingerprints = @(
            $shapeFingerprints.Keys |
                Where-Object { $_ -like "$shapeType*" }
        )

        Write-Host "Fingerprints             : $($typeFingerprints.Count)"
    }

    # --------------------------------------------------------
    # Security / read boundary
    # --------------------------------------------------------

    Write-Host ""
    Write-Host "===== SECURITY ====="
    Write-Host "Component names printed  : False"
    Write-Host "Component IDs printed    : False"
    Write-Host "Folder names printed     : False"
    Write-Host "Raw XML printed          : False"
    Write-Host "Attribute values printed : False"
    Write-Host "Element text printed     : False"
    Write-Host "Business data printed    : False"
    Write-Host "Credentials printed      : False"

    Write-Host ""
    Write-Host "===== API OPERATION COUNTS ====="
    Write-Host "Metadata queries         : 1"
    Write-Host "queryMore calls          : <computed by pagination>"
    Write-Host "Component GET calls      : $definitionsParsed"
    Write-Host "Definitions requested    : $definitionsRequested"
    Write-Host "Mutation calls            : 0"

    Write-Host ""
    Write-Host "CORPUS PROBE : PASS"
}