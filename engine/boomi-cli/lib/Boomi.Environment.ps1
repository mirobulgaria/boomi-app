# ============================================================
# Boomi.Environment.ps1
# boomi-cli v1 READ-ONLY Environment Extensions inspection
#
# Capabilities:
#   Get-BoomiEnvironmentExtensionsXml
#   Show-BoomiEnvironmentExtensions
#
# SAFETY:
#   - GET only
#   - no EnvironmentExtensions UPDATE
#   - no deployment
#   - no execution
#   - extension values are NOT printed in human mode
#   - raw XML is emitted only when explicitly requested
#     through the internal machine-readable xml contract
# ============================================================


function Get-BoomiEnvironmentExtensionsXml {

    param(
        [Parameter(Mandatory=$true)]
        [string]$EnvironmentId
    )

    $tempFile = Join-Path `
        ([IO.Path]::GetTempPath()) `
        ("boomi_envext_" + [Guid]::NewGuid().ToString("N") + ".xml")

    try {

        Invoke-WebRequest `
            -Method Get `
            -Uri "$script:BaseUrl/EnvironmentExtensions/$EnvironmentId" `
            -Headers $script:XmlHeaders `
            -OutFile $tempFile `
            -UseBasicParsing

        if (-not (Test-Path $tempFile)) {
            throw "EnvironmentExtensions GET returned no response file."
        }

        $bytes = [IO.File]::ReadAllBytes($tempFile)

        if ($bytes.Length -eq 0) {
            throw "EnvironmentExtensions GET returned an empty response."
        }

        $content = [Text.Encoding]::UTF8.GetString($bytes)

        if (
            $content.Length -gt 0 -and
            [int][char]$content[0] -eq 0xFEFF
        ) {
            $content = $content.Substring(1)
        }

        try {
            [xml]$xml = $content
        }
        catch {
            throw "EnvironmentExtensions response could not be parsed as UTF-8 XML."
        }

        return [PSCustomObject]@{
            Content = $content
            Xml     = $xml
        }
    }
    finally {

        Remove-Item `
            -Path $tempFile `
            -Force `
            -ErrorAction SilentlyContinue
    }
}


function Show-BoomiEnvironmentExtensions {

    param(
        [Parameter(Mandatory=$true)]
        [string]$EnvironmentId,

        [Parameter()]
        [ValidateSet(
            "human",
            "xml"
        )]
        [string]$OutputFormat = "human"
    )

    # ========================================================
    # STEP 1 - Validate Environment
    # ========================================================

    $environmentResponse = Invoke-RestMethod `
        -Method Get `
        -Uri "$script:BaseUrl/Environment/$EnvironmentId" `
        -Headers $script:JsonHeaders

    if ([string]$environmentResponse.id -ne $EnvironmentId) {
        throw "Environment ID verification failed."
    }

    # ========================================================
    # STEP 2 - GET EnvironmentExtensions
    # ========================================================

    $response = Get-BoomiEnvironmentExtensionsXml `
        -EnvironmentId $EnvironmentId

    [xml]$xml = $response.Xml

    $root = $xml.DocumentElement

    if (-not $root) {
        throw "EnvironmentExtensions XML contains no root element."
    }

    if ($root.LocalName -ne "EnvironmentExtensions") {
        throw "EnvironmentExtensions XML root is unexpected."
    }

    # ========================================================
    # MACHINE CONTRACT
    #
    # IMPORTANT:
    # Raw XML may contain sensitive extension values.
    # This branch must only be used by trusted application
    # code that immediately parses the result.
    # ========================================================

    if ($OutputFormat -eq "xml") {
        [Console]::Out.Write(
            [string]$response.Content
        )

        return
    }

    # ========================================================
    # HUMAN SAFE PRESENTATION
    # ========================================================

    Write-Host ""
    Write-Host "Boomi Environment Extensions"
    Write-Host "============================"
    Write-Host ""
    Write-Host "Environment ID : $EnvironmentId"
    Write-Host ""

    Write-Host "STEP 1 - Validate Environment"
    Write-Host "============================="
    Write-Host "Name           : $($environmentResponse.name)"
    Write-Host "ID             : $($environmentResponse.id)"
    Write-Host "Classification : $($environmentResponse.classification)"
    Write-Host ""

    Write-Host "STEP 2 - Read Environment Extensions"
    Write-Host "===================================="
    Write-Host "GET : OK"
    Write-Host ""

    # ========================================================
    # STEP 3 - Safe structural summary
    #
    # IMPORTANT:
    # We intentionally do NOT print value/text content.
    # ========================================================

    Write-Host "STEP 3 - Safe extension structure"
    Write-Host "================================="

    Write-Host "Root element : $($root.LocalName)"
    Write-Host ""

    $allElements = @(
        $root.SelectNodes(".//*")
    )

    Write-Host "Element count : $($allElements.Count)"
    Write-Host ""

    Write-Host "Element types:"
    Write-Host ""

    $allElements |
        ForEach-Object {
            $_.LocalName
        } |
        Sort-Object -Unique |
        ForEach-Object {
            Write-Host "  $_"
        }

    Write-Host ""

    # ========================================================
    # STEP 4 - Connection extension metadata
    #
    # We extract only safe identifiers:
    #   componentId
    #   name
    #   field id
    #   field type
    #   whether a value attribute exists
    #
    # NEVER print the value itself.
    # ========================================================

    Write-Host "STEP 4 - Connection extension metadata"
    Write-Host "======================================"

    $connectionNodes = @(
        $root.SelectNodes(
            ".//*[local-name()='connection']"
        )
    )

    Write-Host "Connection entries : $($connectionNodes.Count)"
    Write-Host ""

    foreach ($connection in $connectionNodes) {

        $connectionId = ""

        foreach ($candidate in @(
            "id",
            "componentId",
            "component-id"
        )) {
            if ($connection.HasAttribute($candidate)) {
                $connectionId = [string]$connection.GetAttribute($candidate)
                break
            }
        }

        $connectionName = ""

        if ($connection.HasAttribute("name")) {
            $connectionName = [string]$connection.GetAttribute("name")
        }

        Write-Host "Connection"
        Write-Host "----------"

        if (-not [string]::IsNullOrWhiteSpace($connectionName)) {
            Write-Host "Name : $connectionName"
        }

        if (-not [string]::IsNullOrWhiteSpace($connectionId)) {
            Write-Host "ID   : $connectionId"
        }

        $fields = @(
            $connection.SelectNodes(
                ".//*[local-name()='field']"
            )
        )

        Write-Host "Fields : $($fields.Count)"

        foreach ($field in $fields) {

            $fieldId = ""

            if ($field.HasAttribute("id")) {
                $fieldId = [string]$field.GetAttribute("id")
            }

            $fieldType = ""

            if ($field.HasAttribute("type")) {
                $fieldType = [string]$field.GetAttribute("type")
            }

            $hasValue = $field.HasAttribute("value")

            Write-Host (
                "  id='{0}'  type='{1}'  HasValue={2}" -f `
                    $fieldId,
                    $fieldType,
                    $hasValue
            )
        }

        Write-Host ""
    }

    Write-Host ""
    Write-Host "READ ONLY."
    Write-Host "No extension values were printed."
    Write-Host "No EnvironmentExtensions UPDATE was performed."
    Write-Host ""
}