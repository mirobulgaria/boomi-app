# ============================================================
# get-process-definition-corpus.ps1
#
# PRIVATE bounded corpus machine-contract entry point.
#
# This is a dedicated private entry script used by the Boomi
# Builder backend through captured stdout IPC. It is NOT a
# boomi.ps1 dispatcher command and produces no human output.
#
# Contract:
#   success -> stdout contains exactly one JSON envelope:
#              {"version":1,"definitions":["<Component .../>", ...]}
#              stderr is empty.
#
#   failure -> non-zero exit code, no stdout envelope, generic
#              diagnostics only. Raw Component XML is never
#              emitted before the complete envelope is built.
#
# The operation is read-only by construction: it performs only
# ComponentMetadata queries and Component GET operations.
#
# RuntimeMode is fixed to app-readonly semantics: no workspace
# configuration file is required or loaded.
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$Workspace,

    [Parameter()]
    [ValidateSet("app-readonly")]
    [string]$RuntimeMode = "app-readonly"
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
    throw "CLI STARTUP ERROR: Workspace directory was not found."
}

if (-not (Test-Path -LiteralPath $WorkspaceRoot -PathType Container)) {
    throw "CLI STARTUP ERROR: Workspace path is not a directory."
}

$script:WorkspaceRoot = $WorkspaceRoot


# ============================================================
# Load required engine modules
#
# Only the modules required by the private corpus contract are
# loaded. Mutation-capable modules are intentionally not loaded.
# ============================================================

$LibRoot = Join-Path `
    $CliRoot `
    "lib"

if (-not (Test-Path -LiteralPath $LibRoot -PathType Container)) {
    throw "CLI STARTUP ERROR: CLI lib directory was not found."
}

. "$LibRoot\Boomi.Common.ps1"
. "$LibRoot\Boomi.Read.ps1"
. "$LibRoot\Boomi.Corpus.ps1"


# ============================================================
# Private machine contract
#
# FAILURE BOUNDARY:
#
# The complete security-sensitive operation (authentication
# context initialization, corpus acquisition and the final
# stdout emission) runs inside an explicit failure boundary.
#
# Any terminating failure is caught before PowerShell's
# default uncaught-error renderer can expose the original
# ErrorRecord. Underlying errors may contain raw HTTP
# response bodies, which must never reach external stderr.
#
# External contract:
#
#   SUCCESS:
#     stdout = exactly one complete JSON envelope
#     stderr = empty
#     exit   = 0
#
#   FAILURE:
#     stdout = empty
#     stderr = one fixed generic diagnostic
#     exit   = 1
#
# The catch block intentionally never references $_, the
# exception, the ErrorRecord or $Error. Their contents are
# not safe to render.
#
# [Environment]::Exit(1) is used instead of "exit 1" because
# PowerShell loses the numeric code when "exit" runs inside
# a script that was invoked from another scope. The direct
# runtime exit guarantees the contract under every host.
# ============================================================

try {

    Initialize-BoomiContext

    $envelopeJson = Get-BoomiProcessDefinitionCorpus

    [Console]::Out.Write($envelopeJson)
}
catch {

    [Console]::Error.Write(
        "Boomi process-definition corpus acquisition failed."
    )

    [Environment]::Exit(1)
}
