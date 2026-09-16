# ============================================================
# Boomi.Verify.ps1
# boomi-cli - Generic Generated Component Verification
#
# Purpose:
#   Verify that a generated fresh XML DOM corresponds to:
#     - the validated external specification
#     - the dynamically resolved component references
#     - the resolved target folder
#     - the resolved branch
#
# SAFETY:
#   - NO project-specific logic
#   - NO hard-coded Component IDs
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


function Assert-BoomiEqual {

    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyString()]
        [string]$Expected,

        [Parameter(Mandatory=$true)]
        [AllowEmptyString()]
        [string]$Actual,

        [Parameter(Mandatory=$true)]
        [string]$Context
    )

    if ($Expected -cne $Actual) {

        throw @"
VERIFY ERROR: Value mismatch.

Context:
$Context

Expected:
$Expected

Actual:
$Actual
"@
    }
}


function Assert-BoomiXmlBoolean {

    param(
        [Parameter(Mandatory=$true)]
        [bool]$Expected,

        [Parameter(Mandatory=$true)]
        [AllowEmptyString()]
        [string]$Actual,

        [Parameter(Mandatory=$true)]
        [string]$Context
    )

    $expectedText = if ($Expected) {
        "true"
    }
    else {
        "false"
    }

    Assert-BoomiEqual `
        -Expected $expectedText `
        -Actual $Actual `
        -Context $Context
}


function Assert-BoomiXmlNumber {

    param(
        [Parameter(Mandatory=$true)]
        [double]$Expected,

        [Parameter(Mandatory=$true)]
        [AllowEmptyString()]
        [string]$Actual,

        [Parameter(Mandatory=$true)]
        [string]$Context
    )

    $parsed = 0.0

    $ok = [double]::TryParse(
        $Actual,
        [Globalization.NumberStyles]::Float,
        [Globalization.CultureInfo]::InvariantCulture,
        [ref]$parsed
    )

    if (-not $ok) {
        throw "VERIFY ERROR: '$Context' is not a valid invariant numeric value: '$Actual'"
    }

    if ($parsed -ne $Expected) {

        throw @"
VERIFY ERROR: Numeric value mismatch.

Context:
$Context

Expected:
$Expected

Actual:
$parsed
"@
    }
}


function Test-BoomiConnectorActionConfigurationXml {

    param(
        [Parameter(Mandatory=$true)]
        [System.Xml.XmlElement]$ShapeNode,

        [Parameter(Mandatory=$true)]
        [object]$ConfigurationSpec,

        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [object[]]$ResolvedReferences,

        [Parameter(Mandatory=$true)]
        [string]$ShapeName
    )

    $connectorNodes = @(
        $ShapeNode.SelectNodes(
            "./*[local-name()='configuration']/*[local-name()='connectoraction']"
        )
    )

    if ($connectorNodes.Count -ne 1) {

        throw @"
VERIFY ERROR: connector shape '$ShapeName'
requires exactly one connectoraction configuration.

Actual count:
$($connectorNodes.Count)
"@
    }

    $connectorNode = $connectorNodes[0]

    $connectionReference = Get-BoomiResolvedReference `
        -ResolvedReferences $ResolvedReferences `
        -Shape $ShapeName `
        -Role "connection"

    $operationReference = Get-BoomiResolvedReference `
        -ResolvedReferences $ResolvedReferences `
        -Shape $ShapeName `
        -Role "operation"

    Assert-BoomiEqual `
        -Expected ([string]$ConfigurationSpec.actionType) `
        -Actual ([string]$connectorNode.actionType) `
        -Context "shape[$ShapeName].connector.actionType"

    Assert-BoomiEqual `
        -Expected ([string]$ConfigurationSpec.allowDynamicCredentials) `
        -Actual ([string]$connectorNode.allowDynamicCredentials) `
        -Context "shape[$ShapeName].connector.allowDynamicCredentials"

    Assert-BoomiEqual `
        -Expected ([string]$connectionReference.Id) `
        -Actual ([string]$connectorNode.connectionId) `
        -Context "shape[$ShapeName].connector.connectionId"

    Assert-BoomiEqual `
        -Expected ([string]$ConfigurationSpec.connector.expectedSubType) `
        -Actual ([string]$connectorNode.connectorType) `
        -Context "shape[$ShapeName].connector.connectorType"

    Assert-BoomiXmlBoolean `
        -Expected ([bool]$ConfigurationSpec.hideSettings) `
        -Actual ([string]$connectorNode.hideSettings) `
        -Context "shape[$ShapeName].connector.hideSettings"

    Assert-BoomiEqual `
        -Expected ([string]$operationReference.Id) `
        -Actual ([string]$connectorNode.operationId) `
        -Context "shape[$ShapeName].connector.operationId"

    # Proven connectoraction contract currently contains exactly
    # these six attributes.
    $expectedAttributes = @(
        "actionType",
        "allowDynamicCredentials",
        "connectionId",
        "connectorType",
        "hideSettings",
        "operationId"
    )

    if ($connectorNode.Attributes.Count -ne $expectedAttributes.Count) {

        throw @"
VERIFY ERROR: connectoraction '$ShapeName' attribute count mismatch.

Expected:
$($expectedAttributes.Count)

Actual:
$($connectorNode.Attributes.Count)
"@
    }

    foreach ($attributeName in $expectedAttributes) {

        if (-not $connectorNode.HasAttribute($attributeName)) {
            throw "VERIFY ERROR: connectoraction '$ShapeName' is missing attribute '$attributeName'."
        }
    }

    # Proven child structure:
    #
    # <parameters />
    # <dynamicProperties />
    #
    # No additional element children are currently accepted.

    $elementChildren = @(
        $connectorNode.ChildNodes |
            Where-Object {
                $_.NodeType -eq [System.Xml.XmlNodeType]::Element
            }
    )

    if ($elementChildren.Count -ne 2) {

        throw @"
VERIFY ERROR: connectoraction '$ShapeName' child element count mismatch.

Expected:
2

Actual:
$($elementChildren.Count)
"@
    }

    if ([string]$elementChildren[0].LocalName -cne "parameters") {
        throw "VERIFY ERROR: connectoraction '$ShapeName' first child must be parameters."
    }

    if ([string]$elementChildren[1].LocalName -cne "dynamicProperties") {
        throw "VERIFY ERROR: connectoraction '$ShapeName' second child must be dynamicProperties."
    }

    if ($elementChildren[0].Attributes.Count -ne 0) {
        throw "VERIFY ERROR: connectoraction '$ShapeName' parameters contains unexpected attributes."
    }

    if ($elementChildren[0].HasChildNodes) {
        throw "VERIFY ERROR: connectoraction '$ShapeName' parameters contains unexpected child nodes."
    }

    if ($elementChildren[1].Attributes.Count -ne 0) {
        throw "VERIFY ERROR: connectoraction '$ShapeName' dynamicProperties contains unexpected attributes."
    }

    if ($elementChildren[1].HasChildNodes) {
        throw "VERIFY ERROR: connectoraction '$ShapeName' dynamicProperties contains unexpected child nodes."
    }
}


function Test-BoomiGeneratedProcessXml {

    param(
        [Parameter(Mandatory=$true)]
        [object]$SpecResult,

        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [object[]]$ResolvedReferences,

        [Parameter(Mandatory=$true)]
        [xml]$Xml,

        [Parameter(Mandatory=$true)]
        [string]$FolderId,

        [Parameter(Mandatory=$true)]
        [string]$BranchId,

        [switch]$AllowComponentIdentity
    )

    if ($SpecResult.ComponentType -ne "process") {
        throw "VERIFY ERROR: Process verifier received a non-process specification."
    }

    $root = $Xml.DocumentElement

    if (-not $root) {
        throw "VERIFY ERROR: XML contains no root element."
    }

    Write-Host ""
    Write-Host "Generic Process XML Verification"
    Write-Host "================================"
    Write-Host "Name : $($SpecResult.ComponentName)"
    Write-Host ""

    # ========================================================
    # 1 - Root / identity
    # ========================================================

    Assert-BoomiEqual `
        -Expected "Component" `
        -Actual ([string]$root.LocalName) `
        -Context "Component.LocalName"

    Assert-BoomiEqual `
        -Expected "http://api.platform.boomi.com/" `
        -Actual ([string]$root.NamespaceURI) `
        -Context "Component.NamespaceURI"

    Assert-BoomiEqual `
        -Expected ([string]$SpecResult.ComponentName) `
        -Actual ([string]$root.GetAttribute("name")) `
        -Context "Component.name"

    Assert-BoomiEqual `
        -Expected "process" `
        -Actual ([string]$root.GetAttribute("type")) `
        -Context "Component.type"

    Assert-BoomiEqual `
        -Expected $FolderId `
        -Actual ([string]$root.GetAttribute("folderId")) `
        -Context "Component.folderId"

    Assert-BoomiEqual `
        -Expected $BranchId `
        -Actual ([string]$root.GetAttribute("branchId")) `
        -Context "Component.branchId"

    if (-not $AllowComponentIdentity) {

        $forbiddenAttributes = @(
            "componentId",
            "version",
            "createdDate",
            "createdBy",
            "modifiedDate",
            "modifiedBy",
            "currentVersion",
            "deleted"
        )

        foreach ($attributeName in $forbiddenAttributes) {

            if ($root.HasAttribute($attributeName)) {
                throw "VERIFY ERROR: Fresh CREATE XML contains forbidden identity attribute '$attributeName'."
            }
        }
    }

    Write-Host "Component metadata      : OK"
    Write-Host "Fresh identity          : OK"

    # ========================================================
    # 2 - Process node/settings
    # ========================================================

    $processNode = $Xml.SelectSingleNode(
        "/*[local-name()='Component']/*[local-name()='object']/*[local-name()='process']"
    )

    if (-not $processNode) {
        throw "VERIFY ERROR: process node was not found."
    }

    $settings = $SpecResult.Raw.process.settings

    Assert-BoomiXmlBoolean `
        -Expected ([bool]$settings.allowSimultaneous) `
        -Actual ([string]$processNode.allowSimultaneous) `
        -Context "process.allowSimultaneous"

    Assert-BoomiXmlBoolean `
        -Expected ([bool]$settings.enableUserLog) `
        -Actual ([string]$processNode.enableUserLog) `
        -Context "process.enableUserLog"

    Assert-BoomiXmlBoolean `
        -Expected ([bool]$settings.processLogOnErrorOnly) `
        -Actual ([string]$processNode.processLogOnErrorOnly) `
        -Context "process.processLogOnErrorOnly"

    Assert-BoomiXmlBoolean `
        -Expected ([bool]$settings.purgeDataImmediately) `
        -Actual ([string]$processNode.purgeDataImmediately) `
        -Context "process.purgeDataImmediately"

    Assert-BoomiXmlBoolean `
        -Expected ([bool]$settings.stopProcessingIfZeroDocuments) `
        -Actual ([string]$processNode.stopProcessingIfZeroDocuments) `
        -Context "process.stopProcessingIfZeroDocuments"

    Assert-BoomiXmlBoolean `
        -Expected ([bool]$settings.updateRunDates) `
        -Actual ([string]$processNode.updateRunDates) `
        -Context "process.updateRunDates"

    Assert-BoomiEqual `
        -Expected ([string]$settings.workload) `
        -Actual ([string]$processNode.workload) `
        -Context "process.workload"

    Write-Host "Process settings        : OK"

    # ========================================================
    # 3 - Shape cardinality
    # ========================================================

    $specShapes = @(
        $SpecResult.Raw.process.shapes
    )

    $xmlShapes = @(
        $processNode.SelectNodes(
            "./*[local-name()='shapes']/*[local-name()='shape']"
        )
    )

    if ($xmlShapes.Count -ne $specShapes.Count) {

        throw @"
VERIFY ERROR: Shape count mismatch.

Expected:
$($specShapes.Count)

Actual:
$($xmlShapes.Count)
"@
    }

    Write-Host "Shape count             : OK ($($xmlShapes.Count))"

    # ========================================================
    # 4 - Verify every shape against spec
    # ========================================================

    foreach ($shapeSpec in $specShapes) {

        $shapeName = [string]$shapeSpec.name

        $matches = @(
            $xmlShapes |
                Where-Object {
                    [string]$_.name -eq $shapeName
                }
        )

        if ($matches.Count -ne 1) {
            throw "VERIFY ERROR: Expected exactly one XML shape named '$shapeName'."
        }

        $shapeNode = $matches[0]

        Assert-BoomiEqual `
            -Expected ([string]$shapeSpec.type) `
            -Actual ([string]$shapeNode.shapetype) `
            -Context "shape[$shapeName].shapetype"

        Assert-BoomiEqual `
            -Expected ([string]$shapeSpec.image) `
            -Actual ([string]$shapeNode.image) `
            -Context "shape[$shapeName].image"

        Assert-BoomiEqual `
            -Expected ([string]$shapeSpec.label) `
            -Actual ([string]$shapeNode.userlabel) `
            -Context "shape[$shapeName].userlabel"

        Assert-BoomiXmlNumber `
            -Expected ([double]$shapeSpec.x) `
            -Actual ([string]$shapeNode.x) `
            -Context "shape[$shapeName].x"

        Assert-BoomiXmlNumber `
            -Expected ([double]$shapeSpec.y) `
            -Actual ([string]$shapeNode.y) `
            -Context "shape[$shapeName].y"

        $configurationSpec = $shapeSpec.configuration

        switch ([string]$shapeSpec.type) {

            # =================================================
            # START
            # =================================================

            "start" {

                $startKind = [string]$configurationSpec.kind

                if ($startKind -eq "passthroughaction") {

                    $passthroughNodes = @(
                        $shapeNode.SelectNodes(
                            "./*[local-name()='configuration']/*[local-name()='passthroughaction']"
                        )
                    )

                    if ($passthroughNodes.Count -ne 1) {

                        throw @"
VERIFY ERROR: start shape '$shapeName'
requires exactly one passthroughaction configuration.

Actual count:
$($passthroughNodes.Count)
"@
                    }

                    if ($passthroughNodes[0].Attributes.Count -ne 0) {
                        throw "VERIFY ERROR: passthroughaction on '$shapeName' contains unexpected attributes."
                    }

                    if ($passthroughNodes[0].HasChildNodes) {
                        throw "VERIFY ERROR: passthroughaction on '$shapeName' contains unexpected child nodes."
                    }
                }

                if ($startKind -eq "connectoraction") {

                    Test-BoomiConnectorActionConfigurationXml `
                        -ShapeNode $shapeNode `
                        -ConfigurationSpec $configurationSpec `
                        -ResolvedReferences $ResolvedReferences `
                        -ShapeName $shapeName
                }
            }

            # =================================================
            # MAP
            # =================================================

            "map" {

                $mapNodes = @(
                    $shapeNode.SelectNodes(
                        "./*[local-name()='configuration']/*[local-name()='map']"
                    )
                )

                if ($mapNodes.Count -ne 1) {
                    throw "VERIFY ERROR: map shape '$shapeName' requires exactly one map configuration."
                }

                $mapReference = Get-BoomiResolvedReference `
                    -ResolvedReferences $ResolvedReferences `
                    -Shape $shapeName `
                    -Role "map"

                Assert-BoomiEqual `
                    -Expected ([string]$mapReference.Id) `
                    -Actual ([string]$mapNodes[0].mapId) `
                    -Context "shape[$shapeName].map.mapId"

                if ($mapNodes[0].Attributes.Count -ne 1) {
                    throw "VERIFY ERROR: map configuration on '$shapeName' contains unexpected attributes."
                }

                if (-not $mapNodes[0].HasAttribute("mapId")) {
                    throw "VERIFY ERROR: map configuration on '$shapeName' has no mapId attribute."
                }

                if ($mapNodes[0].HasChildNodes) {
                    throw "VERIFY ERROR: map configuration on '$shapeName' contains unexpected child nodes."
                }
            }

            # =================================================
            # CONNECTOR ACTION
            # =================================================

            "connectoraction" {

                Test-BoomiConnectorActionConfigurationXml `
                    -ShapeNode $shapeNode `
                    -ConfigurationSpec $configurationSpec `
                    -ResolvedReferences $ResolvedReferences `
                    -ShapeName $shapeName
            }

            # =================================================
            # PROCESS CALL
            # =================================================

            "processcall" {

                $processCallNode = $shapeNode.SelectSingleNode(
                    "./*[local-name()='configuration']/*[local-name()='processcall']"
                )

                if (-not $processCallNode) {
                    throw "VERIFY ERROR: processcall shape '$shapeName' has no processcall configuration."
                }

                $processReference = Get-BoomiResolvedReference `
                    -ResolvedReferences $ResolvedReferences `
                    -Shape $shapeName `
                    -Role "process"

                Assert-BoomiXmlBoolean `
                    -Expected ([bool]$configurationSpec.abort) `
                    -Actual ([string]$processCallNode.abort) `
                    -Context "shape[$shapeName].processcall.abort"

                Assert-BoomiEqual `
                    -Expected ([string]$processReference.Id) `
                    -Actual ([string]$processCallNode.processId) `
                    -Context "shape[$shapeName].processcall.processId"

                Assert-BoomiXmlBoolean `
                    -Expected ([bool]$configurationSpec.wait) `
                    -Actual ([string]$processCallNode.wait) `
                    -Context "shape[$shapeName].processcall.wait"

                $specReturnPaths = @(
                    $configurationSpec.returnPaths
                )

                $xmlReturnPaths = @(
                    $processCallNode.SelectNodes(
                        "./*[local-name()='returnpaths']/*[local-name()='returnpaths']"
                    )
                )

                if ($specReturnPaths.Count -ne $xmlReturnPaths.Count) {
                    throw "VERIFY ERROR: Process Call '$shapeName' returnPaths count mismatch."
                }

                for (
                    $i = 0;
                    $i -lt $specReturnPaths.Count;
                    $i++
                ) {

                    Assert-BoomiEqual `
                        -Expected ([string]$specReturnPaths[$i].childShapeName) `
                        -Actual ([string]$xmlReturnPaths[$i].childShapeName) `
                        -Context "shape[$shapeName].returnPaths[$i].childShapeName"

                    Assert-BoomiEqual `
                        -Expected ([string]$specReturnPaths[$i].returnLabel) `
                        -Actual ([string]$xmlReturnPaths[$i].returnLabel) `
                        -Context "shape[$shapeName].returnPaths[$i].returnLabel"
                }
            }

            # =================================================
            # RETURN DOCUMENTS
            # =================================================

            "returndocuments" {

                $returnNode = $shapeNode.SelectSingleNode(
                    "./*[local-name()='configuration']/*[local-name()='returndocuments']"
                )

                if (-not $returnNode) {
                    throw "VERIFY ERROR: returndocuments shape '$shapeName' has no returndocuments configuration."
                }

                Assert-BoomiEqual `
                    -Expected ([string]$configurationSpec.label) `
                    -Actual ([string]$returnNode.label) `
                    -Context "shape[$shapeName].returndocuments.label"
            }

            "stop" {

                $stopNode = $shapeNode.SelectSingleNode(
                    "./*[local-name()='configuration']/*[local-name()='stop']"
                )

                if (-not $stopNode) {
                    throw "VERIFY ERROR: stop shape '$shapeName' has no stop configuration."
                }

                if ($stopNode.Attributes.Count -ne 1) {
                    throw "VERIFY ERROR: stop shape '$shapeName' contains unexpected configuration attributes."
                }

                if (-not $stopNode.HasAttribute("continue")) {
                    throw "VERIFY ERROR: stop shape '$shapeName' has no continue attribute."
                }

                if ($stopNode.HasChildNodes) {
                    throw "VERIFY ERROR: stop shape '$shapeName' contains unexpected configuration child nodes."
                }

                Assert-BoomiXmlBoolean `
                    -Expected ([bool]$configurationSpec.continue) `
                    -Actual ([string]$stopNode.continue) `
                    -Context "shape[$shapeName].stop.continue"
            }

            "branch" {

                $branchNode = $shapeNode.SelectSingleNode(
                    "./*[local-name()='configuration']/*[local-name()='branch']"
                )

                if (-not $branchNode) {
                    throw "VERIFY ERROR: branch shape '$shapeName' has no branch configuration."
                }

                if ($branchNode.Attributes.Count -ne 1) {
                    throw "VERIFY ERROR: branch shape '$shapeName' contains unexpected configuration attributes."
                }

                if (-not $branchNode.HasAttribute("numBranches")) {
                    throw "VERIFY ERROR: branch shape '$shapeName' has no numBranches attribute."
                }

                if ($branchNode.HasChildNodes) {
                    throw "VERIFY ERROR: branch shape '$shapeName' contains unexpected configuration child nodes."
                }

                Assert-BoomiXmlNumber `
                    -Expected ([double]$configurationSpec.numBranches) `
                    -Actual ([string]$branchNode.numBranches) `
                    -Context "shape[$shapeName].branch.numBranches"
            }

            "catcherrors" {

                $catchErrorsNode = $shapeNode.SelectSingleNode(
                    "./*[local-name()='configuration']/*[local-name()='catcherrors']"
                )

                if (-not $catchErrorsNode) {
                    throw "VERIFY ERROR: catcherrors shape '$shapeName' has no catcherrors configuration."
                }

                if ($catchErrorsNode.Attributes.Count -ne 2) {
                    throw "VERIFY ERROR: catcherrors shape '$shapeName' contains unexpected configuration attributes."
                }

                foreach ($attributeName in @(
                    "catchAll",
                    "retryCount"
                )) {
                    if (-not $catchErrorsNode.HasAttribute($attributeName)) {
                        throw "VERIFY ERROR: catcherrors shape '$shapeName' is missing attribute '$attributeName'."
                    }
                }

                if ($catchErrorsNode.HasChildNodes) {
                    throw "VERIFY ERROR: catcherrors shape '$shapeName' contains unexpected configuration child nodes."
                }

                Assert-BoomiXmlBoolean `
                    -Expected ([bool]$configurationSpec.catchAll) `
                    -Actual ([string]$catchErrorsNode.catchAll) `
                    -Context "shape[$shapeName].catcherrors.catchAll"

                Assert-BoomiXmlNumber `
                    -Expected ([double]$configurationSpec.retryCount) `
                    -Actual ([string]$catchErrorsNode.retryCount) `
                    -Context "shape[$shapeName].catcherrors.retryCount"
            }

            "decision" {

                $decisionNode = $shapeNode.SelectSingleNode(
                    "./*[local-name()='configuration']/*[local-name()='decision']"
                )

                if ($null -eq $decisionNode) {
                    throw "VERIFY ERROR: decision shape '$shapeName' has no decision configuration."
                }

                if ($decisionNode.Attributes.Count -ne 2) {
                    throw "VERIFY ERROR: decision shape '$shapeName' contains unexpected decision attributes."
                }

                Assert-BoomiEqual `
                    -Expected ([string]$configurationSpec.comparison) `
                    -Actual (
                        [string]$decisionNode.GetAttribute(
                            "comparison"
                        )
                    ) `
                    -Context "shape[$shapeName].decision.comparison"

                Assert-BoomiEqual `
                    -Expected ([string]$configurationSpec.name) `
                    -Actual (
                        [string]$decisionNode.GetAttribute(
                            "name"
                        )
                    ) `
                    -Context "shape[$shapeName].decision.name"

                $expectedValues = @(
                    $configurationSpec.values
                )

                $actualValues = @(
                    $decisionNode.SelectNodes(
                        "./*[local-name()='decisionvalue']"
                    )
                )

                if (
                    $actualValues.Count -ne
                    $expectedValues.Count
                ) {
                    throw "VERIFY ERROR: decision shape '$shapeName' value count mismatch."
                }

                for (
                    $valueIndex = 0;
                    $valueIndex -lt $expectedValues.Count;
                    $valueIndex++
                ) {

                    $expectedValue = $expectedValues[$valueIndex]
                    $actualValue = $actualValues[$valueIndex]

                    if ($actualValue.Attributes.Count -ne 1) {
                        throw "VERIFY ERROR: decisionvalue contains unexpected attributes."
                    }

                    Assert-BoomiEqual `
                        -Expected ([string]$expectedValue.valueType) `
                        -Actual (
                            [string]$actualValue.GetAttribute(
                                "valueType"
                            )
                        ) `
                        -Context "shape[$shapeName].decision.values[$valueIndex].valueType"

                    if (
                        [string]$expectedValue.valueType -eq
                        "process"
                    ) {

                        $processParameters = @(
                            $actualValue.SelectNodes(
                                "./*[local-name()='processparameter']"
                            )
                        )

                        $staticParameters = @(
                            $actualValue.SelectNodes(
                                "./*[local-name()='staticparameter']"
                            )
                        )

                        if (
                            $processParameters.Count -ne 1 -or
                            $staticParameters.Count -ne 0
                        ) {
                            throw "VERIFY ERROR: decision process value has invalid child structure."
                        }

                        $processParameter = $processParameters[0]

                        if (
                            $processParameter.Attributes.Count -ne 2
                        ) {
                            throw "VERIFY ERROR: decision processparameter contains unexpected attributes."
                        }

                        Assert-BoomiEqual `
                            -Expected (
                                [string]$expectedValue.process.processProperty
                            ) `
                            -Actual (
                                [string]$processParameter.GetAttribute(
                                    "processproperty"
                                )
                            ) `
                            -Context "shape[$shapeName].decision.values[$valueIndex].processProperty"

                        Assert-BoomiEqual `
                            -Expected (
                                [string]$expectedValue.process.processPropertyDefaultValue
                            ) `
                            -Actual (
                                [string]$processParameter.GetAttribute(
                                    "processpropertydefaultvalue"
                                )
                            ) `
                            -Context "shape[$shapeName].decision.values[$valueIndex].processPropertyDefaultValue"
                    }

                    if (
                        [string]$expectedValue.valueType -eq
                        "static"
                    ) {

                        $staticParameters = @(
                            $actualValue.SelectNodes(
                                "./*[local-name()='staticparameter']"
                            )
                        )

                        $processParameters = @(
                            $actualValue.SelectNodes(
                                "./*[local-name()='processparameter']"
                            )
                        )

                        if (
                            $staticParameters.Count -ne 1 -or
                            $processParameters.Count -ne 0
                        ) {
                            throw "VERIFY ERROR: decision static value has invalid child structure."
                        }

                        $staticParameter = $staticParameters[0]

                        if (
                            $staticParameter.Attributes.Count -ne 1
                        ) {
                            throw "VERIFY ERROR: decision staticparameter contains unexpected attributes."
                        }

                        Assert-BoomiEqual `
                            -Expected (
                                [string]$expectedValue.static.value
                            ) `
                            -Actual (
                                [string]$staticParameter.GetAttribute(
                                    "staticproperty"
                                )
                            ) `
                            -Context "shape[$shapeName].decision.values[$valueIndex].static.value"
                    }
                }
            }
            default {

                throw "VERIFY ERROR: No verifier exists for shape type '$($shapeSpec.type)'."
            }
        }

        # ====================================================
        # Dragpoints / topology
        # ====================================================

        $specConnections = @(
            $shapeSpec.connections
        )

        $xmlConnections = @(
            $shapeNode.SelectNodes(
                "./*[local-name()='dragpoints']/*[local-name()='dragpoint']"
            )
        )

        if ($specConnections.Count -ne $xmlConnections.Count) {

            throw @"
VERIFY ERROR: Dragpoint count mismatch.

Shape:
$shapeName

Expected:
$($specConnections.Count)

Actual:
$($xmlConnections.Count)
"@
        }

        for (
            $i = 0;
            $i -lt $specConnections.Count;
            $i++
        ) {

            $specConnection = $specConnections[$i]
            $xmlConnection = $xmlConnections[$i]

            Assert-BoomiEqual `
                -Expected ([string]$specConnection.name) `
                -Actual ([string]$xmlConnection.name) `
                -Context "shape[$shapeName].connections[$i].name"

            Assert-BoomiEqual `
                -Expected ([string]$specConnection.toShape) `
                -Actual ([string]$xmlConnection.toShape) `
                -Context "shape[$shapeName].connections[$i].toShape"

            $expectedIdentifier = ""

            if (
                $null -ne
                $specConnection.PSObject.Properties["identifier"]
            ) {
                $expectedIdentifier = [string]$specConnection.identifier
            }

            Assert-BoomiEqual `
                -Expected $expectedIdentifier `
                -Actual ([string]$xmlConnection.identifier) `
                -Context "shape[$shapeName].connections[$i].identifier"

            $expectedText = ""

            if (
                $null -ne
                $specConnection.PSObject.Properties["text"]
            ) {
                $expectedText = [string]$specConnection.text
            }

            Assert-BoomiEqual `
                -Expected $expectedText `
                -Actual ([string]$xmlConnection.text) `
                -Context "shape[$shapeName].connections[$i].text"

            Assert-BoomiXmlNumber `
                -Expected ([double]$specConnection.x) `
                -Actual ([string]$xmlConnection.x) `
                -Context "shape[$shapeName].connections[$i].x"

            Assert-BoomiXmlNumber `
                -Expected ([double]$specConnection.y) `
                -Actual ([string]$xmlConnection.y) `
                -Context "shape[$shapeName].connections[$i].y"
        }
    }

    Write-Host "Shape definitions       : OK"
    Write-Host "Component references    : OK"
    Write-Host "Return paths            : OK"
    Write-Host "Topology                : OK"
    Write-Host ""
    Write-Host "GENERATED XML VERIFY: OK"
    Write-Host ""
    Write-Host "No Boomi API write was performed."
    Write-Host ""

    return $true
}


function Test-BoomiGeneratedComponentXml {

    param(
        [Parameter(Mandatory=$true)]
        [object]$SpecResult,

        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [object[]]$ResolvedReferences,

        [Parameter(Mandatory=$true)]
        [xml]$Xml,

        [Parameter(Mandatory=$true)]
        [string]$FolderId,

        [Parameter(Mandatory=$true)]
        [string]$BranchId,

        [switch]$AllowComponentIdentity
    )

    switch ($SpecResult.ComponentType) {

        "process" {

            return Test-BoomiGeneratedProcessXml `
                -SpecResult $SpecResult `
                -ResolvedReferences $ResolvedReferences `
                -Xml $Xml `
                -FolderId $FolderId `
                -BranchId $BranchId `
                -AllowComponentIdentity:$AllowComponentIdentity
        }

        default {

            throw "VERIFY ERROR: No generated XML verifier exists for component type '$($SpecResult.ComponentType)'."
        }
    }
}