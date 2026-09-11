param(
    [Parameter(Mandatory=$true)]
    [string]$CommonFile,

    [Parameter(Mandatory=$true)]
    [string]$WorkspaceRoot
)

$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)

$script:CliRoot = Split-Path (
    Split-Path $CommonFile -Parent
) -Parent

$script:WorkspaceRoot = $WorkspaceRoot

$SecretsDirectory = Join-Path $WorkspaceRoot "secrets"
$TokenFile = Join-Path $SecretsDirectory "boomi-api-token.dpapi"

New-Item `
    -ItemType Directory `
    -Force `
    -Path $SecretsDirectory |
    Out-Null

$SyntheticToken = "LEGACY_DPAPI_TEST_TOKEN_NOT_REAL"

$SecureToken = ConvertTo-SecureString `
    $SyntheticToken `
    -AsPlainText `
    -Force

$EncryptedToken = $SecureToken |
    ConvertFrom-SecureString

Set-Content `
    -LiteralPath $TokenFile `
    -Value $EncryptedToken

# Runtime token MUST be absent so Initialize-BoomiContext
# is forced through the legacy DPAPI path.
[Environment]::SetEnvironmentVariable(
    "BOOMI_API_TOKEN",
    $null,
    "Process"
)

. $CommonFile

Initialize-BoomiContext

if ($script:BaseUrl -ne "https://api.boomi.com/api/rest/v1/LEGACY_TEST_ACCOUNT") {
    throw "Unexpected BaseUrl."
}

if ([string]::IsNullOrWhiteSpace($script:JsonHeaders.Authorization)) {
    throw "Authorization header was not created."
}

if (-not $script:JsonHeaders.Authorization.StartsWith("Basic ")) {
    throw "Unexpected Authorization scheme."
}

Write-Output "LEGACY_DPAPI_AUTH_OK"