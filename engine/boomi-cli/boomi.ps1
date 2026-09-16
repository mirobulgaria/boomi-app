param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet(
        "search",
        "get",
        "get-definition",
        "export",
        "inspect",
        "list-environments",
        "get-environment-extensions",
        "create-preview",
        "create",
        "create-empty-process",
        "set-label",
        "clone-process",
        "set-process-call",
        "clone-component",
        "set-map",
        "set-connector",
        "delete",
        "restore"
    )]
    [string]$Command,

    [Parameter(Mandatory=$true)]
    [string]$Workspace,

    [Parameter()]
    [string]$Name,

    [Parameter()]
    [string]$Id,

    [Parameter()]
    [string]$Folder,

    [Parameter()]
    [string]$Shape,

    [Parameter()]
    [AllowEmptyString()]
    [string]$Label,

    [Parameter()]
    [string]$TargetProcessId,

    [Parameter()]
    [string]$TargetMapId,

    [Parameter()]
    [string]$TargetConnectionId,

    [Parameter()]
    [string]$TargetOperationId,

    [Parameter()]
    [string]$EnvironmentId,

    [Parameter()]
    [string]$SpecPath,

    [Parameter()]
    [ValidateSet(
        "human",
        "json",
        "xml"
    )]
    [string]$OutputFormat = "human",

    [Parameter()]
    [ValidateSet(
        "workspace",
        "app-readonly"
    )]
    [string]$RuntimeMode = "workspace"
)

$ErrorActionPreference = "Stop"


# ============================================================
# CLI root
# ============================================================

$CliRoot = $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($CliRoot)) {
    throw "CLI STARTUP ERROR: Unable to determine CLI root directory."
}

try {
    $CliRoot = (
        Resolve-Path `
            -LiteralPath $CliRoot `
            -ErrorAction Stop
    ).Path
}
catch {
    throw "CLI STARTUP ERROR: Unable to resolve CLI root directory."
}

$script:CliRoot = $CliRoot


# ============================================================
# Workspace root
# ============================================================

if ([string]::IsNullOrWhiteSpace($Workspace)) {
    throw "CLI STARTUP ERROR: Workspace is required."
}

try {
    $WorkspaceRoot = (
        Resolve-Path `
            -LiteralPath $Workspace `
            -ErrorAction Stop
    ).Path
}
catch {
    throw "CLI STARTUP ERROR: Workspace directory was not found: $Workspace"
}

if (-not (Test-Path -LiteralPath $WorkspaceRoot -PathType Container)) {
    throw "CLI STARTUP ERROR: Workspace path is not a directory: $WorkspaceRoot"
}

$script:WorkspaceRoot = $WorkspaceRoot


# ============================================================
# Load reusable CLI engine modules
# ============================================================

$LibRoot = Join-Path `
    $CliRoot `
    "lib"

if (-not (Test-Path -LiteralPath $LibRoot -PathType Container)) {
    throw "CLI STARTUP ERROR: CLI lib directory was not found: $LibRoot"
}

. "$LibRoot\Boomi.Common.ps1"
. "$LibRoot\Boomi.Config.ps1"
. "$LibRoot\Boomi.Read.ps1"
. "$LibRoot\Boomi.Write.ps1"
. "$LibRoot\Boomi.Clone.ps1"
. "$LibRoot\Boomi.ProcessCall.ps1"
. "$LibRoot\Boomi.ComponentClone.ps1"
. "$LibRoot\Boomi.Map.ps1"
. "$LibRoot\Boomi.Connector.ps1"
. "$LibRoot\Boomi.Environment.ps1"
. "$LibRoot\Boomi.Spec.ps1"
. "$LibRoot\Boomi.Validate.ps1"
. "$LibRoot\Boomi.Resolve.ps1"
. "$LibRoot\Boomi.Build.ps1"
. "$LibRoot\Boomi.Verify.ps1"
. "$LibRoot\Boomi.Create.ps1"
. "$LibRoot\Boomi.Delete.ps1"
. "$LibRoot\Boomi.Restore.ps1"


# ============================================================
# Runtime mode safety policy
#
# app-readonly is an explicit allowlist mode.
#
# IMPORTANT:
# The safety check runs before workspace configuration,
# authentication and command dispatch.
#
# Only explicitly approved read contracts are permitted.
# ============================================================

if ($RuntimeMode -eq "app-readonly") {

    $AppReadOnlyCommands = @(
    "get",
    "get-definition",
    "list-environments",
    "get-environment-extensions"
    )

    if ($Command -notin $AppReadOnlyCommands) {

        throw @"
APP READ-ONLY SAFETY BLOCK.

Command:
$Command

Runtime mode:
app-readonly

The command is not permitted in app-readonly mode.

No workspace configuration was loaded.
No Boomi authentication context was initialized.
No Boomi API operation was performed.
"@
    }
}


# ============================================================
# Workspace configuration
# ============================================================

if ($RuntimeMode -eq "workspace") {

    $CliConfigPath = Join-Path `
        $WorkspaceRoot `
        "config\cli.json"

    if (-not (Test-Path -LiteralPath $CliConfigPath -PathType Leaf)) {

        throw @"
CLI STARTUP ERROR: Workspace configuration file was not found.

Workspace:
$WorkspaceRoot

Expected:
$CliConfigPath
"@
    }

    Initialize-BoomiCliConfig `
        -Path $CliConfigPath |
        Out-Null
}


# ============================================================
# Authentication / Boomi API context
# ============================================================

Initialize-BoomiContext


# ============================================================
# Command dispatch
# ============================================================

switch ($Command) {

    "search" {

        if ([string]::IsNullOrWhiteSpace($Name)) {
            throw "search requires -Name"
        }

        Search-BoomiComponent `
            -Name $Name
    }

    "get" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "get requires -Id"
        }

        if ($OutputFormat -eq "json") {

            $component = Get-BoomiComponentInfo `
                -ComponentId $Id

            Convert-BoomiComponentInfoToJson `
                -Component $component
        }
        else {

            Show-BoomiComponent `
                -Id $Id
        }
    }

    "get-definition" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "get-definition requires -Id"
        }

        if ($OutputFormat -ne "xml") {
            throw "get-definition requires -OutputFormat xml"
        }

        Get-BoomiComponentDefinitionXml `
            -Id $Id
    }

    "export" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "export requires -Id"
        }

        Export-BoomiComponent `
            -Id $Id
    }

    "inspect" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "inspect requires -Id"
        }

        Inspect-BoomiProcess `
            -Id $Id
    }

    "list-environments" {
    Show-BoomiEnvironments `
        -OutputFormat $OutputFormat
    }

    "get-environment-extensions" {

    if ([string]::IsNullOrWhiteSpace($EnvironmentId)) {
        throw "get-environment-extensions requires -EnvironmentId"
    }

    if (
        $OutputFormat -ne "human" -and
        $OutputFormat -ne "xml"
    ) {
        throw (
            "get-environment-extensions requires " +
            "-OutputFormat human or xml"
        )
    }

    Show-BoomiEnvironmentExtensions `
        -EnvironmentId $EnvironmentId `
        -OutputFormat $OutputFormat
    }

    "create-preview" {

        if ([string]::IsNullOrWhiteSpace($SpecPath)) {
            throw "create-preview requires -SpecPath"
        }

        New-BoomiComponentCreatePreview `
            -SpecPath $SpecPath |
            Out-Null
    }

    "create" {

        if ([string]::IsNullOrWhiteSpace($SpecPath)) {
            throw "create requires -SpecPath"
        }

        Invoke-BoomiComponentCreateFromSpec `
            -SpecPath $SpecPath
    }

    "create-empty-process" {

        if ([string]::IsNullOrWhiteSpace($Name)) {
            throw "create-empty-process requires -Name"
        }

        if ([string]::IsNullOrWhiteSpace($Folder)) {
            throw "create-empty-process requires -Folder"
        }

        New-BoomiEmptyProcess `
            -Name $Name `
            -Folder $Folder
    }

    "set-label" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "set-label requires -Id"
        }

        if ([string]::IsNullOrWhiteSpace($Shape)) {
            throw "set-label requires -Shape"
        }

        if ($null -eq $Label) {
            throw "set-label requires -Label"
        }

        Set-BoomiProcessShapeLabel `
            -Id $Id `
            -Shape $Shape `
            -Label $Label
    }

    "clone-process" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "clone-process requires -Id"
        }

        if ([string]::IsNullOrWhiteSpace($Name)) {
            throw "clone-process requires -Name"
        }

        if ([string]::IsNullOrWhiteSpace($Folder)) {
            throw "clone-process requires -Folder"
        }

        Copy-BoomiProcess `
            -Id $Id `
            -Name $Name `
            -Folder $Folder
    }

    "set-process-call" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "set-process-call requires -Id"
        }

        if ([string]::IsNullOrWhiteSpace($Shape)) {
            throw "set-process-call requires -Shape"
        }

        if ([string]::IsNullOrWhiteSpace($TargetProcessId)) {
            throw "set-process-call requires -TargetProcessId"
        }

        Set-BoomiProcessCallTarget `
            -Id $Id `
            -Shape $Shape `
            -TargetProcessId $TargetProcessId
    }

    "clone-component" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "clone-component requires -Id"
        }

        if ([string]::IsNullOrWhiteSpace($Name)) {
            throw "clone-component requires -Name"
        }

        if ([string]::IsNullOrWhiteSpace($Folder)) {
            throw "clone-component requires -Folder"
        }

        Copy-BoomiAllowedComponent `
            -Id $Id `
            -Name $Name `
            -Folder $Folder
    }

    "set-map" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "set-map requires -Id"
        }

        if ([string]::IsNullOrWhiteSpace($Shape)) {
            throw "set-map requires -Shape"
        }

        if ([string]::IsNullOrWhiteSpace($TargetMapId)) {
            throw "set-map requires -TargetMapId"
        }

        Set-BoomiMapTarget `
            -Id $Id `
            -Shape $Shape `
            -TargetMapId $TargetMapId
    }

    "set-connector" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "set-connector requires -Id"
        }

        if ([string]::IsNullOrWhiteSpace($Shape)) {
            throw "set-connector requires -Shape"
        }

        if ([string]::IsNullOrWhiteSpace($TargetConnectionId)) {
            throw "set-connector requires -TargetConnectionId"
        }

        if ([string]::IsNullOrWhiteSpace($TargetOperationId)) {
            throw "set-connector requires -TargetOperationId"
        }

        Set-BoomiConnectorTarget `
            -Id $Id `
            -Shape $Shape `
            -TargetConnectionId $TargetConnectionId `
            -TargetOperationId $TargetOperationId
    }

    "delete" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "delete requires -Id"
        }

        Remove-BoomiComponent `
            -Id $Id
    }

    "restore" {

        if ([string]::IsNullOrWhiteSpace($Id)) {
            throw "restore requires -Id"
        }

        Restore-BoomiComponent `
            -Id $Id
    }
}