param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("protect", "unprotect")]
    [string]$Action,

    [Parameter(Mandatory=$true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"

[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)

if ($Action -eq "protect") {

    $SecretValue = [Console]::In.ReadToEnd()

    if ([string]::IsNullOrEmpty($SecretValue)) {
        throw "Secret value must not be empty."
    }

    $SecureValue = ConvertTo-SecureString `
        $SecretValue `
        -AsPlainText `
        -Force

    $ProtectedValue = $SecureValue |
        ConvertFrom-SecureString

    [IO.File]::WriteAllText(
        $Path,
        $ProtectedValue,
        [Text.UTF8Encoding]::new($false)
    )

    Write-Output "PROTECTED"
    exit 0
}

if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "Protected secret was not found."
}

$ProtectedValue = [IO.File]::ReadAllText(
    $Path,
    [Text.Encoding]::UTF8
)

$ProtectedValue = $ProtectedValue.Trim()

$SecureValue = $ProtectedValue |
    ConvertTo-SecureString

$Credential = New-Object `
    System.Management.Automation.PSCredential(
        "secret",
        $SecureValue
    )

$PlainValue = $Credential.GetNetworkCredential().Password

if ([string]::IsNullOrEmpty($PlainValue)) {
    throw "Failed to unprotect secret."
}

[Console]::Out.Write($PlainValue)