# ============================================================
# Boomi.Common.ps1
# Common configuration, authentication and HTTP helpers
#
# ROOT MODEL:
#
#   $script:CliRoot
#       Reusable boomi-cli installation directory.
#
#   $script:WorkspaceRoot
#       Active project workspace containing configuration,
#       secrets, specs and generated artifacts.
#
# IMPORTANT:
#   This module must be loaded by the main boomi.ps1
#   dispatcher after both roots are established.
#
# UTF-8 XML RULE:
# Boomi XML responses are downloaded as raw bytes and decoded
# explicitly as UTF-8.
#
# DPAPI RULE:
# The existing DPAPI file may have been created by Windows
# PowerShell 5.1 Set-Content using UTF-16LE. Therefore the
# token file must NOT be forced through UTF-8 decoding.
# PowerShell Get-Content performs BOM-aware decoding.
# ============================================================


# ============================================================
# Root validation
# ============================================================

if ([string]::IsNullOrWhiteSpace($script:CliRoot)) {

    throw @"
CLI STARTUP ERROR: CliRoot is not initialized.

Boomi.Common.ps1 must be loaded by the main boomi.ps1
dispatcher after it establishes the CLI installation root.
"@
}

if ([string]::IsNullOrWhiteSpace($script:WorkspaceRoot)) {

    throw @"
CLI STARTUP ERROR: WorkspaceRoot is not initialized.

Boomi.Common.ps1 must be loaded by the main boomi.ps1
dispatcher after it establishes the active workspace.
"@
}

if (-not (Test-Path -LiteralPath $script:CliRoot -PathType Container)) {
    throw "CLI STARTUP ERROR: CliRoot is not a directory: $script:CliRoot"
}

if (-not (Test-Path -LiteralPath $script:WorkspaceRoot -PathType Container)) {
    throw "CLI STARTUP ERROR: WorkspaceRoot is not a directory: $script:WorkspaceRoot"
}


# ============================================================
# Workspace authentication material
# ============================================================

$script:TokenFile = Join-Path `
    $script:WorkspaceRoot `
    "secrets\boomi-api-token.dpapi"


# ============================================================
# Console UTF-8
# ============================================================

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

try {

    [Console]::OutputEncoding = $utf8NoBom
}
catch {

    # Some hosts may not allow changing Console.OutputEncoding.
}

$global:OutputEncoding = $utf8NoBom


# ============================================================
# Initialize authentication / API context
# ============================================================

function Initialize-BoomiContext {

    $AccountId = [Environment]::GetEnvironmentVariable(
        "BOOMI_ACCOUNT_ID",
        "User"
    )

    $Username = [Environment]::GetEnvironmentVariable(
        "BOOMI_USERNAME",
        "User"
    )

    if ([string]::IsNullOrWhiteSpace($AccountId)) {
        throw "BOOMI_ACCOUNT_ID is missing."
    }

    if ([string]::IsNullOrWhiteSpace($Username)) {
        throw "BOOMI_USERNAME is missing."
    }

    if (-not (Test-Path -LiteralPath $script:TokenFile -PathType Leaf)) {
        throw "DPAPI token file not found: $script:TokenFile"
    }

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Do NOT use ReadAllText(..., UTF8) here.
    #
    # The existing DPAPI file was created by Windows
    # PowerShell Set-Content and may be UTF-16LE.
    #
    # Get-Content is BOM-aware and correctly reads the
    # existing encrypted SecureString representation.
    # --------------------------------------------------------

    $encryptedToken = Get-Content `
        -LiteralPath $script:TokenFile `
        -Raw

    if ([string]::IsNullOrWhiteSpace($encryptedToken)) {
        throw "DPAPI token file is empty."
    }

    # Remove only trailing CR/LF introduced by Set-Content.
    $encryptedToken = $encryptedToken.Trim()

    try {

        $secureToken = $encryptedToken |
            ConvertTo-SecureString
    }
    catch {

        throw "Failed to decode DPAPI token file. The existing token file was not modified."
    }

    $credential = New-Object `
        System.Management.Automation.PSCredential(
            "dummy",
            $secureToken
        )

    $Token = $credential.GetNetworkCredential().Password

    if ([string]::IsNullOrWhiteSpace($Token)) {
        throw "Failed to decrypt Boomi API token."
    }

    # Correct the interpolation without retaining the token
    # beyond context initialization.
    $pair = "BOOMI_TOKEN.${Username}:" + $Token

    $encoded = [Convert]::ToBase64String(
        [Text.Encoding]::ASCII.GetBytes($pair)
    )

    $script:BaseUrl = "https://api.boomi.com/api/rest/v1/$AccountId"

    $script:JsonHeaders = @{
        Authorization  = "Basic $encoded"
        Accept         = "application/json"
        "Content-Type" = "application/json; charset=utf-8"
    }

    $script:XmlHeaders = @{
        Authorization = "Basic $encoded"
        Accept        = "application/xml"
    }

    # Remove plaintext token variables as soon as possible.
    $Token          = $null
    $pair           = $null
    $credential     = $null
    $secureToken    = $null
    $encryptedToken = $null
}


# ============================================================
# UTF-8-safe Boomi Component GET
#
# IMPORTANT:
# Do NOT rely on Invoke-WebRequest.Content for XML under
# Windows PowerShell 5.1.
#
# Flow:
#   HTTP response
#       -> raw file bytes
#       -> explicit UTF-8 decoding
#       -> XML validation
#
# This protects non-ASCII Unicode text.
# ============================================================

function Get-BoomiComponentXml {

    param(
        [Parameter(Mandatory=$true)]
        [string]$ComponentId
    )

    $tempFile = Join-Path `
        ([IO.Path]::GetTempPath()) `
        ("boomi_" + [Guid]::NewGuid().ToString("N") + ".xml")

    try {

        Invoke-WebRequest `
            -Method Get `
            -Uri "$script:BaseUrl/Component/$ComponentId" `
            -Headers $script:XmlHeaders `
            -OutFile $tempFile `
            -UseBasicParsing

        if (-not (Test-Path -LiteralPath $tempFile -PathType Leaf)) {
            throw "Boomi GET did not create a temporary response file."
        }

        $bytes = [IO.File]::ReadAllBytes(
            $tempFile
        )

        if ($bytes.Length -eq 0) {
            throw "Boomi GET returned an empty response."
        }

        # Boomi Component XML declares UTF-8.
        $content = [Text.Encoding]::UTF8.GetString(
            $bytes
        )

        # Remove decoded UTF-8 BOM character if present.
        if (
            $content.Length -gt 0 -and
            [int][char]$content[0] -eq 0xFEFF
        ) {
            $content = $content.Substring(1)
        }

        try {

            [xml]$testXml = $content
        }
        catch {

            throw "Boomi response could not be parsed as UTF-8 XML."
        }

        return [PSCustomObject]@{
            Content = $content
            Bytes   = $bytes
        }
    }
    finally {

        Remove-Item `
            -LiteralPath $tempFile `
            -Force `
            -ErrorAction SilentlyContinue
    }
}


# ============================================================
# Component metadata helper
# ============================================================

function Get-BoomiComponentInfo {

    param(
        [Parameter(Mandatory=$true)]
        [string]$ComponentId
    )

    $response = Get-BoomiComponentXml `
        -ComponentId $ComponentId

    [xml]$xml = $response.Content
    $component = $xml.Component

    return [PSCustomObject]@{
        Id      = [string]$component.componentId
        Name    = [string]$component.name
        Type    = [string]$component.type
        Folder  = [string]$component.folderFullPath
        Version = [string]$component.version
    }
}


# ============================================================
# UTF-8-safe file writer
# ============================================================

function Write-BoomiUtf8File {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Path,

        [Parameter(Mandatory=$true)]
        [AllowEmptyString()]
        [string]$Content
    )

    [IO.File]::WriteAllText(
        $Path,
        $Content,
        (New-Object System.Text.UTF8Encoding($false))
    )
}