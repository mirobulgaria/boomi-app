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

. $CommonFile

Initialize-BoomiContext

if ($script:BaseUrl -ne "https://api.boomi.com/api/rest/v1/TEST_ACCOUNT") {
    throw "Unexpected BaseUrl."
}

if ([string]::IsNullOrWhiteSpace($script:JsonHeaders.Authorization)) {
    throw "Authorization header was not created."
}

if (-not $script:JsonHeaders.Authorization.StartsWith("Basic ")) {
    throw "Unexpected Authorization scheme."
}

Write-Output "RUNTIME_AUTH_OK"