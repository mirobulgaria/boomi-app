from __future__ import annotations

import pytest

from boomi_builder.services.boomi_connector_component_analyzer import (
    BoomiConnectorComponentAnalysisError,
    BoomiConnectorComponentAnalyzer,
)


REFERENCE_ID = (
    "11111111-1111-1111-1111-111111111111"
)


SETTINGS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    name="Synthetic Connector Settings"
    type="connector-settings"
    version="1">
  <object>
    <SyntheticConnectionConfig xmlns="">
      <field
          id="endpoint"
          type="string"
          value="https://example.invalid/service" />
      <field
          id="security"
          type="string"
          value="NONE" />
      <field
          id="password"
          type="password" />
      <field
          id="advancedOptions"
          type="custom">
        <SyntheticOptions mode="example">
          <NestedOption enabled="true" />
        </SyntheticOptions>
      </field>
    </SyntheticConnectionConfig>
  </object>
</Component>
"""


OPERATION_XML = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    name="Synthetic Connector Operation"
    type="connector-action"
    version="1">
  <object>
    <SyntheticOperation
        xmlns=""
        mode="request-response">
      <Archiving enabled="false" />
      <Configuration>
        <SyntheticOperationConfig
            operationType="EXECUTE"
            requestProfileType="xml"
            responseProfileType="json">
          <field
              id="requestEnvelope"
              type="boolean"
              value="true" />
          <field
              id="linkedComponent"
              type="component"
              value="" />
          <SyntheticReference
              componentId="{REFERENCE_ID}" />
        </SyntheticOperationConfig>
      </Configuration>
      <Tracking>
        <TrackedFields />
      </Tracking>
    </SyntheticOperation>
  </object>
</Component>
"""


def analyze(
    xml_text: str,
):
    return (
        BoomiConnectorComponentAnalyzer()
        .analyze(xml_text)
    )


def test_analyzer_reads_connector_settings_type() -> None:
    result = analyze(
        SETTINGS_XML
    )

    assert (
        result.component_type
        == "connector-settings"
    )

    assert (
        result.root_name
        == "SyntheticConnectionConfig"
    )


def test_analyzer_reads_connector_action_type() -> None:
    result = analyze(
        OPERATION_XML
    )

    assert (
        result.component_type
        == "connector-action"
    )

    assert (
        result.root_name
        == "SyntheticOperation"
    )


def test_analyzer_preserves_root_attributes() -> None:
    result = analyze(
        OPERATION_XML
    )

    assert dict(
        result.root_attributes
    ) == {
        "mode": "request-response",
    }


def test_analyzer_collects_settings_fields() -> None:
    result = analyze(
        SETTINGS_XML
    )

    assert result.field_count == 4

    assert [
        field.id
        for field in result.fields
    ] == [
        "endpoint",
        "security",
        "password",
        "advancedOptions",
    ]


def test_analyzer_preserves_field_metadata() -> None:
    result = analyze(
        SETTINGS_XML
    )

    endpoint = result.find_field(
        "endpoint"
    )

    assert endpoint is not None
    assert endpoint.type == "string"

    assert endpoint.value == (
        "https://example.invalid/service"
    )

    assert endpoint.path == (
        "SyntheticConnectionConfig/field"
    )


def test_analyzer_preserves_missing_field_value() -> None:
    result = analyze(
        SETTINGS_XML
    )

    password = result.find_field(
        "password"
    )

    assert password is not None
    assert password.type == "password"
    assert password.value is None


def test_analyzer_preserves_nested_field_configuration() -> None:
    result = analyze(
        SETTINGS_XML
    )

    advanced = result.find_field(
        "advancedOptions"
    )

    assert advanced is not None

    assert len(
        advanced.configuration
    ) == 1

    options = (
        advanced.configuration[0]
    )

    assert options.name == (
        "SyntheticOptions"
    )

    assert dict(
        options.attributes
    ) == {
        "mode": "example",
    }

    assert len(
        options.children
    ) == 1

    assert (
        options.children[0].name
        == "NestedOption"
    )


def test_analyzer_preserves_generic_tree() -> None:
    result = analyze(
        OPERATION_XML
    )

    root = result.configuration

    assert root.name == (
        "SyntheticOperation"
    )

    assert [
        child.name
        for child in root.children
    ] == [
        "Archiving",
        "Configuration",
        "Tracking",
    ]

    configuration = (
        root.children[1]
    )

    assert (
        configuration.children[0].name
        == "SyntheticOperationConfig"
    )


def test_analyzer_collects_operation_fields() -> None:
    result = analyze(
        OPERATION_XML
    )

    assert result.field_count == 2

    assert [
        field.id
        for field in result.fields
    ] == [
        "requestEnvelope",
        "linkedComponent",
    ]


def test_find_field_returns_none_for_unknown_field() -> None:
    result = analyze(
        SETTINGS_XML
    )

    assert (
        result.find_field(
            "doesNotExist"
        )
        is None
    )


def test_analyzer_discovers_uuid_references_generically() -> None:
    result = analyze(
        OPERATION_XML
    )

    assert len(
        result.references
    ) == 1

    reference = (
        result.references[0]
    )

    assert (
        reference.element_name
        == "SyntheticReference"
    )

    assert (
        reference.attribute_name
        == "componentId"
    )

    assert (
        reference.component_id
        == REFERENCE_ID
    )

    assert (
        result.referenced_component_ids
        == (REFERENCE_ID,)
    )


def test_non_uuid_values_are_not_references() -> None:
    result = analyze(
        SETTINGS_XML
    )

    assert result.references == ()
    assert (
        result.referenced_component_ids
        == ()
    )


def test_analyzer_preserves_unknown_connector_structure() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="connector-settings">
  <object>
    <FutureConnector xmlns="">
      <UnknownSection mode="future">
        <DeepNode value="123" />
      </UnknownSection>
    </FutureConnector>
  </object>
</Component>
"""

    result = analyze(
        xml
    )

    assert (
        result.root_name
        == "FutureConnector"
    )

    assert (
        result.configuration
        .children[0]
        .name
        == "UnknownSection"
    )

    assert (
        result.configuration
        .children[0]
        .children[0]
        .name
        == "DeepNode"
    )


def test_analyzer_allows_connector_without_fields() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="connector-action">
  <object>
    <FutureOperation xmlns="">
      <Options />
    </FutureOperation>
  </object>
</Component>
"""

    result = analyze(
        xml
    )

    assert result.field_count == 0
    assert result.fields == ()


def test_analyzer_rejects_field_without_id() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="connector-settings">
  <object>
    <SyntheticConnection xmlns="">
      <field
          type="string"
          value="example" />
    </SyntheticConnection>
  </object>
</Component>
"""

    with pytest.raises(
        BoomiConnectorComponentAnalysisError,
        match=(
            "field attribute 'id' "
            "is missing"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_rejects_empty_input() -> None:
    with pytest.raises(
        ValueError,
        match="xml_text must not be empty",
    ):
        analyze(
            ""
        )


def test_analyzer_rejects_invalid_xml() -> None:
    with pytest.raises(
        BoomiConnectorComponentAnalysisError,
        match="not well-formed",
    ):
        analyze(
            "<Component>"
        )


def test_analyzer_rejects_unsupported_component_type() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="" />
  </object>
</Component>
"""

    with pytest.raises(
        BoomiConnectorComponentAnalysisError,
        match=(
            "Component type must be "
            "connector-settings or "
            "connector-action"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_rejects_missing_object() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="connector-settings" />
"""

    with pytest.raises(
        BoomiConnectorComponentAnalysisError,
        match=(
            "Component object element "
            "is missing"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_requires_single_configuration_root() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="connector-settings">
  <object>
    <First xmlns="" />
    <Second xmlns="" />
  </object>
</Component>
"""

    with pytest.raises(
        BoomiConnectorComponentAnalysisError,
        match=(
            "exactly one root "
            "configuration element"
        ),
    ):
        analyze(
            xml
        )