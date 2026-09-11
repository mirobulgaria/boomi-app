param(
    [Parameter(Mandatory=$true)]
    [string]$ReadFile
)

$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)

. $ReadFile

$SyntheticComponent = [PSCustomObject]@{
    ComponentId    = "00000000-1111-2222-3333-444444444444"
    Name           = "TEST — Български ↔ ZTE"
    Type           = "process"
    Version        = 7
    CurrentVersion = $true
    Deleted        = $false
    FolderFullPath = "Example/Integration"
    BranchName     = "main"
}

Write-BoomiComponentHuman `
    -Component $SyntheticComponent