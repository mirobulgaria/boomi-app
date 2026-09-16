# ============================================================
# Boomi.Build.ps1
# boomi-cli - Generic Component XML Builder
#
# Purpose:
#   Build fresh Boomi Component XML from:
#
#     validated external specification
#       +
#     resolved authoritative references
#
# IMPORTANT:
#   - NO project-specific logic
#   - NO hard-coded Component IDs
#   - NO source Component XML reuse
#   - NO Boomi API write
#
# Initially supported:
#   component.type = process
#
# Proven process shape contracts currently supported:
#   start / connectoraction / LISTEN
#   start / passthroughaction
#   map
#   connectoraction / EXECUTE
#   processcall
#   returndocuments
# ============================================================


function ConvertTo-BoomiXmlBoolean {

    param(
        [Parameter(Mandatory=$true)]
        [bool]$Value
    )

    if ($Value) {
        return "true"
    }

    return "false"
}


function Get-BoomiResolvedReference {

    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [object[]]$ResolvedReferences,

        [Parameter(Mandatory=$true)]
        [string]$Shape,

        [Parameter(Mandatory=$true)]
        [string]$Role
    )

    $matches = @(
        $ResolvedReferences |
            Where-Object {
                [string]$_.Shape -eq $Shape -and
                [string]$_.Role -eq $Role
            }
    )

    if ($matches.Count -eq 0) {
        throw "BUILD ERROR: No resolved reference for shape='$Shape', role='$Role'."
    }

    if ($matches.Count -gt 1) {
        throw "BUILD ERROR: Multiple resolved references for shape='$Shape', role='$Role'."
    }

    return $matches[0]
}


function New-BoomiXmlElement {

    param(
        [Parameter(Mandatory=$true)]
        [System.Xml.XmlDocument]$Document,

        [Parameter(Mandatory=$true)]
        [string]$Name
    )

    return $Document.CreateElement($Name)
}


function Add-BoomiXmlAttribute {

    param(
        [Parameter(Mandatory=$true)]
        [System.Xml.XmlElement]$Element,

        [Parameter(Mandatory=$true)]
        [string]$Name,

        [Parameter(Mandatory=$true)]
        [AllowEmptyString()]
        [string]$Value
    )

    $Element.SetAttribute(
        $Name,
        $Value
    )
}


function New-BoomiConnectorActionConfigurationNode {

    param(
        [Parameter(Mandatory=$true)]
        [System.Xml.XmlDocument]$Document,

        [Parameter(Mandatory=$true)]
        [object]$ConfigurationSpec,

        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [object[]]$ResolvedReferences,

        [Parameter(Mandatory=$true)]
        [string]$ShapeName
    )

    $connectionReference = Get-BoomiResolvedReference `
        -ResolvedReferences $ResolvedReferences `
        -Shape $ShapeName `
        -Role "connection"

    $operationReference = Get-BoomiResolvedReference `
        -ResolvedReferences $ResolvedReferences `
        -Shape $ShapeName `
        -Role "operation"

    $connectorNode = New-BoomiXmlElement `
        -Document $Document `
        -Name "connectoraction"

    Add-BoomiXmlAttribute `
        -Element $connectorNode `
        -Name "actionType" `
        -Value ([string]$ConfigurationSpec.actionType)

    Add-BoomiXmlAttribute `
        -Element $connectorNode `
        -Name "allowDynamicCredentials" `
        -Value ([string]$ConfigurationSpec.allowDynamicCredentials)

    Add-BoomiXmlAttribute `
        -Element $connectorNode `
        -Name "connectionId" `
        -Value ([string]$connectionReference.Id)

    Add-BoomiXmlAttribute `
        -Element $connectorNode `
        -Name "connectorType" `
        -Value ([string]$ConfigurationSpec.connector.expectedSubType)

    Add-BoomiXmlAttribute `
        -Element $connectorNode `
        -Name "hideSettings" `
        -Value (
            ConvertTo-BoomiXmlBoolean `
                -Value ([bool]$ConfigurationSpec.hideSettings)
        )

    Add-BoomiXmlAttribute `
        -Element $connectorNode `
        -Name "operationId" `
        -Value ([string]$operationReference.Id)

    $parametersNode = New-BoomiXmlElement `
        -Document $Document `
        -Name "parameters"

    $dynamicPropertiesNode = New-BoomiXmlElement `
        -Document $Document `
        -Name "dynamicProperties"

    $connectorNode.AppendChild(
        $parametersNode
    ) | Out-Null

    $connectorNode.AppendChild(
        $dynamicPropertiesNode
    ) | Out-Null

    return $connectorNode
}


function New-BoomiProcessXml {

    param(
        [Parameter(Mandatory=$true)]
        [object]$SpecResult,

        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [object[]]$ResolvedReferences,

        [Parameter(Mandatory=$true)]
        [string]$FolderId,

        [Parameter(Mandatory=$true)]
        [string]$BranchId
    )

    if ($SpecResult.ComponentType -ne "process") {
        throw "BUILD ERROR: Process builder received a non-process specification."
    }

    if ([string]::IsNullOrWhiteSpace($FolderId)) {
        throw "BUILD ERROR: FolderId is empty."
    }

    if ([string]::IsNullOrWhiteSpace($BranchId)) {
        throw "BUILD ERROR: BranchId is empty."
    }

    $spec = $SpecResult.Raw
    $processSpec = $spec.process
    $settings = $processSpec.settings

    # ========================================================
    # 1 - NEW XML document
    # ========================================================

    $xml = New-Object System.Xml.XmlDocument

    $declaration = $xml.CreateXmlDeclaration(
        "1.0",
        "UTF-8",
        "yes"
    )

    $xml.AppendChild($declaration) | Out-Null

    # ========================================================
    # 2 - Component root
    # ========================================================

    $component = $xml.CreateElement(
        "bns",
        "Component",
        "http://api.platform.boomi.com/"
    )

    $xsiNamespace = $xml.CreateAttribute(
        "xmlns",
        "xsi",
        "http://www.w3.org/2000/xmlns/"
    )

    $xsiNamespace.Value = "http://www.w3.org/2001/XMLSchema-instance"

    $component.Attributes.Append(
        $xsiNamespace
    ) | Out-Null

    Add-BoomiXmlAttribute `
        -Element $component `
        -Name "name" `
        -Value ([string]$SpecResult.ComponentName)

    Add-BoomiXmlAttribute `
        -Element $component `
        -Name "type" `
        -Value "process"

    Add-BoomiXmlAttribute `
        -Element $component `
        -Name "folderId" `
        -Value $FolderId

    Add-BoomiXmlAttribute `
        -Element $component `
        -Name "branchId" `
        -Value $BranchId

    $xml.AppendChild($component) | Out-Null

    if ($component.HasAttribute("componentId")) {
        throw "BUILD ERROR: Fresh Component unexpectedly contains componentId."
    }

    # ========================================================
    # 3 - encryptedValues
    # ========================================================

    $encryptedValues = $xml.CreateElement(
        "bns",
        "encryptedValues",
        "http://api.platform.boomi.com/"
    )

    $component.AppendChild(
        $encryptedValues
    ) | Out-Null

    # ========================================================
    # 4 - object
    # ========================================================

    $objectNode = $xml.CreateElement(
        "bns",
        "object",
        "http://api.platform.boomi.com/"
    )

    $component.AppendChild(
        $objectNode
    ) | Out-Null

    # ========================================================
    # 5 - process
    # ========================================================

    $processNode = New-BoomiXmlElement `
        -Document $xml `
        -Name "process"

    Add-BoomiXmlAttribute `
        -Element $processNode `
        -Name "allowSimultaneous" `
        -Value (
            ConvertTo-BoomiXmlBoolean `
                -Value ([bool]$settings.allowSimultaneous)
        )

    Add-BoomiXmlAttribute `
        -Element $processNode `
        -Name "enableUserLog" `
        -Value (
            ConvertTo-BoomiXmlBoolean `
                -Value ([bool]$settings.enableUserLog)
        )

    Add-BoomiXmlAttribute `
        -Element $processNode `
        -Name "processLogOnErrorOnly" `
        -Value (
            ConvertTo-BoomiXmlBoolean `
                -Value ([bool]$settings.processLogOnErrorOnly)
        )

    Add-BoomiXmlAttribute `
        -Element $processNode `
        -Name "purgeDataImmediately" `
        -Value (
            ConvertTo-BoomiXmlBoolean `
                -Value ([bool]$settings.purgeDataImmediately)
        )

    Add-BoomiXmlAttribute `
        -Element $processNode `
        -Name "stopProcessingIfZeroDocuments" `
        -Value (
            ConvertTo-BoomiXmlBoolean `
                -Value ([bool]$settings.stopProcessingIfZeroDocuments)
        )

    Add-BoomiXmlAttribute `
        -Element $processNode `
        -Name "updateRunDates" `
        -Value (
            ConvertTo-BoomiXmlBoolean `
                -Value ([bool]$settings.updateRunDates)
        )

    Add-BoomiXmlAttribute `
        -Element $processNode `
        -Name "workload" `
        -Value ([string]$settings.workload)

    $objectNode.AppendChild(
        $processNode
    ) | Out-Null

    # ========================================================
    # 6 - shapes
    # ========================================================

    $shapesNode = New-BoomiXmlElement `
        -Document $xml `
        -Name "shapes"

    $processNode.AppendChild(
        $shapesNode
    ) | Out-Null

    foreach ($shapeSpec in @($processSpec.shapes)) {

        $shapeName = [string]$shapeSpec.name
        $shapeType = [string]$shapeSpec.type
        $configurationSpec = $shapeSpec.configuration

        $shapeNode = New-BoomiXmlElement `
            -Document $xml `
            -Name "shape"

        Add-BoomiXmlAttribute `
            -Element $shapeNode `
            -Name "image" `
            -Value ([string]$shapeSpec.image)

        Add-BoomiXmlAttribute `
            -Element $shapeNode `
            -Name "name" `
            -Value $shapeName

        Add-BoomiXmlAttribute `
            -Element $shapeNode `
            -Name "shapetype" `
            -Value $shapeType

        Add-BoomiXmlAttribute `
            -Element $shapeNode `
            -Name "userlabel" `
            -Value ([string]$shapeSpec.label)

        Add-BoomiXmlAttribute `
            -Element $shapeNode `
            -Name "x" `
            -Value (
                [Convert]::ToString(
                    [double]$shapeSpec.x,
                    [Globalization.CultureInfo]::InvariantCulture
                )
            )

        Add-BoomiXmlAttribute `
            -Element $shapeNode `
            -Name "y" `
            -Value (
                [Convert]::ToString(
                    [double]$shapeSpec.y,
                    [Globalization.CultureInfo]::InvariantCulture
                )
            )

        # ====================================================
        # configuration
        # ====================================================

        $configurationNode = New-BoomiXmlElement `
            -Document $xml `
            -Name "configuration"

        $shapeNode.AppendChild(
            $configurationNode
        ) | Out-Null

        switch ($shapeType) {

            # =================================================
            # START
            # =================================================

            "start" {

                $startKind = [string]$configurationSpec.kind

                if ($startKind -eq "passthroughaction") {

                    $passthroughNode = New-BoomiXmlElement `
                        -Document $xml `
                        -Name "passthroughaction"

                    $configurationNode.AppendChild(
                        $passthroughNode
                    ) | Out-Null
                }

                if ($startKind -eq "connectoraction") {

                    $connectorNode = New-BoomiConnectorActionConfigurationNode `
                        -Document $xml `
                        -ConfigurationSpec $configurationSpec `
                        -ResolvedReferences $ResolvedReferences `
                        -ShapeName $shapeName

                    $configurationNode.AppendChild(
                        $connectorNode
                    ) | Out-Null
                }
            }

            # =================================================
            # MAP
            # =================================================

            "map" {

                $mapReference = Get-BoomiResolvedReference `
                    -ResolvedReferences $ResolvedReferences `
                    -Shape $shapeName `
                    -Role "map"

                $mapNode = New-BoomiXmlElement `
                    -Document $xml `
                    -Name "map"

                Add-BoomiXmlAttribute `
                    -Element $mapNode `
                    -Name "mapId" `
                    -Value ([string]$mapReference.Id)

                $configurationNode.AppendChild(
                    $mapNode
                ) | Out-Null
            }

            # =================================================
            # CONNECTOR ACTION
            # =================================================

            "connectoraction" {

                $connectorNode = New-BoomiConnectorActionConfigurationNode `
                    -Document $xml `
                    -ConfigurationSpec $configurationSpec `
                    -ResolvedReferences $ResolvedReferences `
                    -ShapeName $shapeName

                $configurationNode.AppendChild(
                    $connectorNode
                ) | Out-Null
            }

            # =================================================
            # PROCESS CALL
            # =================================================

            "processcall" {

                $processReference = Get-BoomiResolvedReference `
                    -ResolvedReferences $ResolvedReferences `
                    -Shape $shapeName `
                    -Role "process"

                $processCallNode = New-BoomiXmlElement `
                    -Document $xml `
                    -Name "processcall"

                Add-BoomiXmlAttribute `
                    -Element $processCallNode `
                    -Name "abort" `
                    -Value (
                        ConvertTo-BoomiXmlBoolean `
                            -Value ([bool]$configurationSpec.abort)
                    )

                Add-BoomiXmlAttribute `
                    -Element $processCallNode `
                    -Name "processId" `
                    -Value ([string]$processReference.Id)

                Add-BoomiXmlAttribute `
                    -Element $processCallNode `
                    -Name "wait" `
                    -Value (
                        ConvertTo-BoomiXmlBoolean `
                            -Value ([bool]$configurationSpec.wait)
                    )

                $parametersNode = New-BoomiXmlElement `
                    -Document $xml `
                    -Name "parameters"

                $processCallNode.AppendChild(
                    $parametersNode
                ) | Out-Null

                $returnPathsNode = New-BoomiXmlElement `
                    -Document $xml `
                    -Name "returnpaths"

                foreach (
                    $returnPathSpec in
                    @($configurationSpec.returnPaths)
                ) {

                    $returnPathNode = New-BoomiXmlElement `
                        -Document $xml `
                        -Name "returnpaths"

                    Add-BoomiXmlAttribute `
                        -Element $returnPathNode `
                        -Name "childShapeName" `
                        -Value ([string]$returnPathSpec.childShapeName)

                    Add-BoomiXmlAttribute `
                        -Element $returnPathNode `
                        -Name "returnLabel" `
                        -Value ([string]$returnPathSpec.returnLabel)

                    $returnPathsNode.AppendChild(
                        $returnPathNode
                    ) | Out-Null
                }

                $processCallNode.AppendChild(
                    $returnPathsNode
                ) | Out-Null

                $configurationNode.AppendChild(
                    $processCallNode
                ) | Out-Null
            }

            # =================================================
            # RETURN DOCUMENTS
            # =================================================

            "returndocuments" {

                $returnDocumentsNode = New-BoomiXmlElement `
                    -Document $xml `
                    -Name "returndocuments"

                Add-BoomiXmlAttribute `
                    -Element $returnDocumentsNode `
                    -Name "label" `
                    -Value ([string]$configurationSpec.label)

                $configurationNode.AppendChild(
                    $returnDocumentsNode
                ) | Out-Null
            }

            "stop" {

                $stopNode = New-BoomiXmlElement `
                    -Document $xml `
                    -Name "stop"

                Add-BoomiXmlAttribute `
                    -Element $stopNode `
                    -Name "continue" `
                    -Value (
                        ConvertTo-BoomiXmlBoolean `
                            -Value ([bool]$configurationSpec.continue)
                    )

                $configurationNode.AppendChild(
                    $stopNode
                ) | Out-Null
            }

            "branch" {

                $branchNode = New-BoomiXmlElement `
                    -Document $xml `
                    -Name "branch"

                Add-BoomiXmlAttribute `
                    -Element $branchNode `
                    -Name "numBranches" `
                    -Value (
                        [Convert]::ToString(
                            [double]$configurationSpec.numBranches,
                            [Globalization.CultureInfo]::InvariantCulture
                        )
                    )

                $configurationNode.AppendChild(
                    $branchNode
                ) | Out-Null
            }

            "catcherrors" {

                $catchErrorsNode = New-BoomiXmlElement `
                    -Document $xml `
                    -Name "catcherrors"

                Add-BoomiXmlAttribute `
                    -Element $catchErrorsNode `
                    -Name "catchAll" `
                    -Value (
                        ConvertTo-BoomiXmlBoolean `
                            -Value ([bool]$configurationSpec.catchAll)
                    )

                Add-BoomiXmlAttribute `
                    -Element $catchErrorsNode `
                    -Name "retryCount" `
                    -Value (
                        [Convert]::ToString(
                            [double]$configurationSpec.retryCount,
                            [Globalization.CultureInfo]::InvariantCulture
                        )
                    )

                $configurationNode.AppendChild(
                    $catchErrorsNode
                ) | Out-Null
            }

            default {

                throw "BUILD ERROR: No process builder exists for shape type '$shapeType'."
            }
        }

        # ====================================================
        # dragpoints
        # ====================================================

        $dragpointsNode = New-BoomiXmlElement `
            -Document $xml `
            -Name "dragpoints"

        foreach ($connectionSpec in @($shapeSpec.connections)) {

            $dragpointNode = New-BoomiXmlElement `
                -Document $xml `
                -Name "dragpoint"

            if (
                $null -ne
                $connectionSpec.PSObject.Properties["identifier"] -and
                -not [string]::IsNullOrWhiteSpace(
                    [string]$connectionSpec.identifier
                )
            ) {

                Add-BoomiXmlAttribute `
                    -Element $dragpointNode `
                    -Name "identifier" `
                    -Value ([string]$connectionSpec.identifier)
            }

            if (
                $null -ne
                $connectionSpec.PSObject.Properties["text"]
            ) {

                Add-BoomiXmlAttribute `
                    -Element $dragpointNode `
                    -Name "text" `
                    -Value ([string]$connectionSpec.text)
            }

            Add-BoomiXmlAttribute `
                -Element $dragpointNode `
                -Name "name" `
                -Value ([string]$connectionSpec.name)

            Add-BoomiXmlAttribute `
                -Element $dragpointNode `
                -Name "toShape" `
                -Value ([string]$connectionSpec.toShape)

            Add-BoomiXmlAttribute `
                -Element $dragpointNode `
                -Name "x" `
                -Value (
                    [Convert]::ToString(
                        [double]$connectionSpec.x,
                        [Globalization.CultureInfo]::InvariantCulture
                    )
                )

            Add-BoomiXmlAttribute `
                -Element $dragpointNode `
                -Name "y" `
                -Value (
                    [Convert]::ToString(
                        [double]$connectionSpec.y,
                        [Globalization.CultureInfo]::InvariantCulture
                    )
                )

            $dragpointsNode.AppendChild(
                $dragpointNode
            ) | Out-Null
        }

        $shapeNode.AppendChild(
            $dragpointsNode
        ) | Out-Null

        $shapesNode.AppendChild(
            $shapeNode
        ) | Out-Null
    }

    # ========================================================
    # 7 - processOverrides
    # ========================================================

    $processOverrides = $xml.CreateElement(
        "bns",
        "processOverrides",
        "http://api.platform.boomi.com/"
    )

    $component.AppendChild(
        $processOverrides
    ) | Out-Null

    # ========================================================
    # 8 - Return NEW DOM
    # ========================================================

    return $xml
}


function New-BoomiComponentXml {

    param(
        [Parameter(Mandatory=$true)]
        [object]$SpecResult,

        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [object[]]$ResolvedReferences,

        [Parameter(Mandatory=$true)]
        [string]$FolderId,

        [Parameter(Mandatory=$true)]
        [string]$BranchId
    )

    switch ($SpecResult.ComponentType) {

        "process" {

            return New-BoomiProcessXml `
                -SpecResult $SpecResult `
                -ResolvedReferences $ResolvedReferences `
                -FolderId $FolderId `
                -BranchId $BranchId
        }

        default {

            throw "BUILD ERROR: No XML builder exists for component type '$($SpecResult.ComponentType)'."
        }
    }
}