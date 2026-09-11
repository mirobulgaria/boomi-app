# ============================================================
# Boomi.Config.ps1
# boomi-cli - Generic CLI Configuration Layer
#
# Purpose:
#   Load and validate CLI/account configuration from external
#   JSON.
#
# IMPORTANT:
#   - NO project-specific names or paths
#   - NO hard-coded Boomi Component IDs
#   - NO hard-coded branch names or branch IDs
#   - NO Boomi API calls
#   - NO writes
#
# Supported config version:
#   1
# ============================================================


function Read-BoomiCliConfig {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "CONFIG ERROR: Configuration path is empty."
    }

    try {

        $resolvedPath = (
            Resolve-Path `
                -LiteralPath $Path `
                -ErrorAction Stop
        ).Path
    }
    catch {

        throw "CONFIG ERROR: Configuration file was not found: $Path"
    }

    if (-not (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
        throw "CONFIG ERROR: Configuration path is not a file: $resolvedPath"
    }

    try {

        $jsonText = [IO.File]::ReadAllText(
            $resolvedPath,
            [Text.Encoding]::UTF8
        )
    }
    catch {

        throw "CONFIG ERROR: Failed to read configuration as UTF-8: $resolvedPath"
    }

    if ([string]::IsNullOrWhiteSpace($jsonText)) {
        throw "CONFIG ERROR: Configuration file is empty."
    }

    if (
        $jsonText.Length -gt 0 -and
        [int][char]$jsonText[0] -eq 0xFEFF
    ) {
        $jsonText = $jsonText.Substring(1)
    }

    try {

        $config = $jsonText |
            ConvertFrom-Json `
                -ErrorAction Stop
    }
    catch {

        throw "CONFIG ERROR: Configuration contains invalid JSON."
    }

    if ($null -eq $config) {
        throw "CONFIG ERROR: JSON produced no configuration object."
    }

    # ========================================================
    # Config version
    # ========================================================

    if ($null -eq $config.PSObject.Properties["configVersion"]) {
        throw "CONFIG ERROR: Required property 'configVersion' is missing."
    }

    $configVersion = [string]$config.configVersion

    if ($configVersion -ne "1") {

        throw @"
CONFIG ERROR: Unsupported configuration version.

Actual:
$configVersion

Supported:
1
"@
    }

    # ========================================================
    # Write policy
    # ========================================================

    if ($null -eq $config.PSObject.Properties["writePolicy"]) {
        throw "CONFIG ERROR: Required object 'writePolicy' is missing."
    }

    $writePolicy = $config.writePolicy

    if (
        $null -eq
        $writePolicy.PSObject.Properties["allowedFolders"]
    ) {
        throw "CONFIG ERROR: writePolicy.allowedFolders is missing."
    }

    $allowedFolders = @(
        $writePolicy.allowedFolders |
            ForEach-Object {
                [string]$_
            }
    )

    if ($allowedFolders.Count -eq 0) {
        throw "CONFIG ERROR: writePolicy.allowedFolders is empty."
    }

    foreach ($folder in $allowedFolders) {

        if ([string]::IsNullOrWhiteSpace($folder)) {
            throw "CONFIG ERROR: writePolicy.allowedFolders contains an empty value."
        }
    }

    $uniqueFolders = @(
        $allowedFolders |
            Sort-Object -Unique
    )

    if ($uniqueFolders.Count -ne $allowedFolders.Count) {
        throw "CONFIG ERROR: writePolicy.allowedFolders contains duplicate entries."
    }

    # ========================================================
    # Branch context
    #
    # Branch query access is not assumed. The configured
    # branch context is account/runtime configuration.
    #
    # Components with resolved dependencies can later validate
    # their authoritative branch metadata against this context.
    # ========================================================

    if ($null -eq $config.PSObject.Properties["branchContext"]) {
        throw "CONFIG ERROR: Required object 'branchContext' is missing."
    }

    $branchContext = $config.branchContext

    if ($null -eq $branchContext.PSObject.Properties["name"]) {
        throw "CONFIG ERROR: branchContext.name is missing."
    }

    if ($null -eq $branchContext.PSObject.Properties["id"]) {
        throw "CONFIG ERROR: branchContext.id is missing."
    }

    $branchName = [string]$branchContext.name
    $branchId = [string]$branchContext.id

    if ([string]::IsNullOrWhiteSpace($branchName)) {
        throw "CONFIG ERROR: branchContext.name is empty."
    }

    if ([string]::IsNullOrWhiteSpace($branchId)) {
        throw "CONFIG ERROR: branchContext.id is empty."
    }

    return [PSCustomObject]@{
        Path           = $resolvedPath
        ConfigVersion  = $configVersion
        AllowedFolders = $allowedFolders
        BranchName     = $branchName
        BranchId       = $branchId
        Raw            = $config
    }
}


function Initialize-BoomiCliConfig {

    param(
        [Parameter(Mandatory=$true)]
        [string]$Path
    )

    $config = Read-BoomiCliConfig `
        -Path $Path

    $script:BoomiCliConfig = $config

    return $config
}


function Get-BoomiCliConfig {

    if ($null -eq $script:BoomiCliConfig) {

        throw @"
CONFIG ERROR: CLI configuration is not initialized.

Call Initialize-BoomiCliConfig before using configuration-dependent operations.
"@
    }

    return $script:BoomiCliConfig
}


function Get-BoomiConfiguredBranchContext {

    $config = Get-BoomiCliConfig

    if ([string]::IsNullOrWhiteSpace([string]$config.BranchName)) {
        throw "CONFIG ERROR: Configured branch name is empty."
    }

    if ([string]::IsNullOrWhiteSpace([string]$config.BranchId)) {
        throw "CONFIG ERROR: Configured branch ID is empty."
    }

    return [PSCustomObject]@{
        Name = [string]$config.BranchName
        Id   = [string]$config.BranchId
    }
}


function Show-BoomiCliConfig {

    $config = Get-BoomiCliConfig

    Write-Host ""
    Write-Host "Boomi CLI Configuration"
    Write-Host "======================="
    Write-Host "File           : $($config.Path)"
    Write-Host "Config Version : $($config.ConfigVersion)"
    Write-Host "Allowed folders: $(@($config.AllowedFolders).Count)"
    Write-Host ""

    foreach ($folder in $config.AllowedFolders) {
        Write-Host "  $folder"
    }

    Write-Host ""
    Write-Host "Branch context:"
    Write-Host "  Name : $($config.BranchName)"
    Write-Host "  ID   : $($config.BranchId)"
    Write-Host ""
    Write-Host "CONFIGURATION: OK"
    Write-Host ""
    Write-Host "No Boomi API call was performed."
    Write-Host ""
}
