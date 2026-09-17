# ============================================================
# Boomi.Corpus.ps1
# PRIVATE bounded process-definition corpus acquisition
#
# PRIVATE MACHINE CONTRACT:
#
#   This module implements the private captured-stdout machine
#   contract for bounded corpus acquisition. It is consumed by
#   the Boomi Builder backend via a dedicated private entry
#   script and is NOT routed through the human-facing boomi.ps1
#   dispatcher output layer.
#
#   The only function exposed here returns a single JSON envelope
#   document containing raw Component XML strings. Raw XML must
#   never be written to the terminal, Write-Host, stderr, logs or
#   exception messages.
#
#   Bound: maximum 10 definitions (Stage 2B.1 contract).
#
#   All-or-nothing:
#   If ANY acquisition or validation step fails, no JSON envelope
#   and no raw Component XML is emitted.
# ============================================================


function Get-BoomiProcessDefinitionCorpus {

    <#
    .SYNOPSIS
    Acquires a bounded corpus of process Component XML definitions.

    .DESCRIPTION
    Performs complete ComponentMetadata pagination, selects up to
    10 unique active process componentIds in deterministic
    componentId order, acquires every selected Component definition through
    Get-BoomiComponentXml, validates each definition, and returns
    exactly one serialized JSON machine envelope:

        {"version":1,"definitions":["<Component .../>", ...]}

    Component IDs are used internally for acquisition and
    integrity validation only. They are never added to the
    envelope as metadata.

    On any failure this function throws before producing output.
    No partial envelope is ever emitted.

    .OUTPUTS
    System.String - one serialized JSON machine envelope.
    #>

    # --------------------------------------------------------
    # Complete metadata inventory
    # --------------------------------------------------------

    $metadata = Get-BoomiComponentMetadata
    $allMetadata = $metadata.Results

    # --------------------------------------------------------
    # Deterministic active process selection
    #
    # Mirrors the Stage 2B.1 evidence-supported selection:
    #   type == process
    #   deleted != true
    #   non-empty componentId
    #   uniqueness by componentId before the bound
    #   stable ordering by componentId
    #   hard bound: first 10 unique componentIds
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

    if ($activeProcesses.Count -eq 0) {
        throw "Process definition corpus contained no active process definitions."
    }

    # --------------------------------------------------------
    # ComponentMetadata can contain multiple active rows for
    # one componentId. Corpus cardinality is based on unique
    # component identities, not metadata-history rows.
    #
    # Do not filter by currentVersion and do not select a
    # metadata version. Component acquisition uses
    # Component/{ComponentId}.
    # --------------------------------------------------------

    $activeProcessIds = @(
        $activeProcesses |
            ForEach-Object {
                [string]$_.componentId
            } |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace($_)
            } |
            Sort-Object -Unique
    )

    if ($activeProcessIds.Count -eq 0) {
        throw "Process definition corpus contained no active process identities."
    }

    $definitionLimit = 10

    if ($activeProcessIds.Count -lt $definitionLimit) {
        $definitionLimit = $activeProcessIds.Count
    }

    $selectedProcessIds = @(
        $activeProcessIds[0..($definitionLimit - 1)]
    )

    # --------------------------------------------------------
    # All-or-nothing acquisition
    #
    # Definitions are buffered internally. Nothing is written to
    # the output stream until every acquisition and validation
    # step has succeeded.
    # --------------------------------------------------------

    $definitions = @()

    foreach ($componentId in $selectedProcessIds) {

        $componentId = [string]$componentId

        $response = Get-BoomiComponentXml `
            -ComponentId $componentId

        if (
            $null -eq $response -or
            [string]::IsNullOrWhiteSpace(
                [string]$response.Content
            )
        ) {
            throw "Process definition corpus acquisition returned an empty definition."
        }

        [xml]$definitionXml = $response.Content

        if ($null -eq $definitionXml.Component) {
            throw "Process definition corpus acquisition returned a non-Component document."
        }

        $returnedId = [string]$definitionXml.Component.componentId

        if ([string]::IsNullOrWhiteSpace($returnedId)) {
            throw "Process definition corpus acquisition returned a definition without identity."
        }

        if ($returnedId -ne $componentId) {
            throw "Process definition corpus acquisition returned a mismatched definition identity."
        }

        if ($null -eq $definitionXml.Component.object) {
            throw "Process definition corpus acquisition returned a definition without an object."
        }

        $definitions += [string]$response.Content
    }

    # --------------------------------------------------------
    # Complete envelope construction
    #
    # Exact v1 schema:
    #   version      - integer 1
    #   definitions  - array of raw Component XML strings
    #
    # No other top-level keys are permitted.
    # --------------------------------------------------------

    $envelope = [ordered]@{
        version     = 1
        definitions = @($definitions)
    }

    $envelopeJson = (
        $envelope |
            ConvertTo-Json `
                -Depth 10 `
                -Compress
    )

    return [string]$envelopeJson
}
