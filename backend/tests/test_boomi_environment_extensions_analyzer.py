from __future__ import annotations

import pytest

from boomi_builder.services.boomi_environment_extensions_analyzer import (
    BoomiEnvironmentExtensionsAnalysisError,
    BoomiEnvironmentExtensionsAnalyzer,
)


SYNTHETIC_FIELD_SECRET = (
    "SYNTHETIC_FIELD_SECRET_MUST_NOT_LEAK"
)

SYNTHETIC_PROPERTY_SECRET = (
    "SYNTHETIC_PROPERTY_SECRET_MUST_NOT_LEAK"
)

SYNTHETIC_HELP_TEXT = (
    "SYNTHETIC_HELP_TEXT_MUST_NOT_LEAK"
)

SYNTHETIC_OVERRIDE = (
    "SYNTHETIC_OVERRIDE_MUST_NOT_LEAK"
)


def synthetic_xml() -> str:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<EnvironmentExtensions
    environmentId="env-1"
    extensionGroupId="group-1"
    id="extensions-1">

  <connections>
    <connection
        id="connection-1"
        name="Synthetic Connection">
      <field
          id="password"
          componentOverride="true"
          encryptedValueSet="true"
          useDefault="false"
          usesEncryption="true"
          value="{SYNTHETIC_FIELD_SECRET}" />
    </connection>
  </connections>

  <operations>
    <operation
        id="operation-1"
        name="Synthetic Operation">
      <field
          id="requestOption"
          value="{SYNTHETIC_FIELD_SECRET}" />
    </operation>
  </operations>

  <crossReferences>
    <crossReference
        id="cross-reference-1"
        name="Synthetic Cross Reference"
        overrideValues="{SYNTHETIC_OVERRIDE}">
      <CrossReferenceRows />
    </crossReference>
  </crossReferences>

  <processProperties>
    <ProcessProperty
        id="property-1"
        name="Synthetic Process Property">
      <ProcessPropertyValue
          key="property-key"
          label="Property Label"
          dataType="string"
          encryptedValueSet="true"
          helpText="{SYNTHETIC_HELP_TEXT}"
          useDefault="false"
          value="{SYNTHETIC_PROPERTY_SECRET}" />
    </ProcessProperty>
  </processProperties>

</EnvironmentExtensions>
"""


@pytest.fixture
def analyzer() -> BoomiEnvironmentExtensionsAnalyzer:
    return BoomiEnvironmentExtensionsAnalyzer()


def test_analyzes_supported_structure(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    analysis = analyzer.analyze(
        synthetic_xml()
    )

    assert (
        analysis.root_name
        == "EnvironmentExtensions"
    )

    assert analysis.connection_count == 1
    assert analysis.operation_count == 1
    assert analysis.cross_reference_count == 1
    assert analysis.process_property_count == 1

    assert analysis.element_count == 13


def test_connection_metadata_is_safe(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    analysis = analyzer.analyze(
        synthetic_xml()
    )

    connection = analysis.connections[0]

    assert (
        connection.component_id
        == "connection-1"
    )

    assert (
        connection.name
        == "Synthetic Connection"
    )

    assert len(connection.fields) == 1

    field = connection.fields[0]

    assert field.field_id == "password"
    assert field.has_value is True

    assert (
        field.has_component_override
        is True
    )

    assert (
        field.has_encrypted_value_set
        is True
    )

    assert field.has_use_default is True

    assert (
        field.has_uses_encryption
        is True
    )


def test_operation_metadata_is_safe(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    analysis = analyzer.analyze(
        synthetic_xml()
    )

    operation = analysis.operations[0]

    assert (
        operation.component_id
        == "operation-1"
    )

    assert (
        operation.name
        == "Synthetic Operation"
    )

    assert len(operation.fields) == 1

    assert (
        operation.fields[0].field_id
        == "requestOption"
    )

    assert (
        operation.fields[0].has_value
        is True
    )


def test_cross_reference_metadata_is_safe(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    analysis = analyzer.analyze(
        synthetic_xml()
    )

    cross_reference = (
        analysis.cross_references[0]
    )

    assert (
        cross_reference.component_id
        == "cross-reference-1"
    )

    assert (
        cross_reference.name
        == "Synthetic Cross Reference"
    )

    assert (
        cross_reference.has_override_values
        is True
    )

    assert (
        cross_reference.row_container_count
        == 1
    )


def test_process_property_metadata_is_safe(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    analysis = analyzer.analyze(
        synthetic_xml()
    )

    process_property = (
        analysis.process_properties[0]
    )

    assert (
        process_property.component_id
        == "property-1"
    )

    assert (
        process_property.name
        == "Synthetic Process Property"
    )

    assert len(
        process_property.values
    ) == 1

    value = process_property.values[0]

    assert value.key == "property-key"
    assert value.label == "Property Label"
    assert value.data_type == "string"

    assert value.has_value is True

    assert (
        value.has_encrypted_value_set
        is True
    )

    assert value.has_use_default is True
    assert value.has_help_text is True


def test_sensitive_values_do_not_enter_analysis(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    analysis = analyzer.analyze(
        synthetic_xml()
    )

    rendered = repr(
        analysis
    )

    forbidden = (
        SYNTHETIC_FIELD_SECRET,
        SYNTHETIC_PROPERTY_SECRET,
        SYNTHETIC_HELP_TEXT,
        SYNTHETIC_OVERRIDE,
    )

    for secret in forbidden:
        assert secret not in rendered


def test_element_counts_are_deterministic(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    analysis = analyzer.analyze(
        synthetic_xml()
    )

    counts = dict(
        analysis.element_counts
    )

    assert counts == {
        "CrossReferenceRows": 1,
        "EnvironmentExtensions": 1,
        "ProcessProperty": 1,
        "ProcessPropertyValue": 1,
        "connection": 1,
        "connections": 1,
        "crossReference": 1,
        "crossReferences": 1,
        "field": 2,
        "operation": 1,
        "operations": 1,
        "processProperties": 1,
    }


def test_empty_environment_extensions_is_valid(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    analysis = analyzer.analyze(
        "<EnvironmentExtensions />"
    )

    assert analysis.root_name == (
        "EnvironmentExtensions"
    )

    assert analysis.element_count == 1
    assert analysis.connection_count == 0
    assert analysis.operation_count == 0

    assert (
        analysis.cross_reference_count
        == 0
    )

    assert (
        analysis.process_property_count
        == 0
    )


def test_namespace_is_supported(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    xml_text = """\
<EnvironmentExtensions
    xmlns="http://api.platform.boomi.com/">
  <connections>
    <connection
        id="connection-1"
        name="Connection" />
  </connections>
</EnvironmentExtensions>
"""

    analysis = analyzer.analyze(
        xml_text
    )

    assert analysis.root_name == (
        "EnvironmentExtensions"
    )

    assert analysis.connection_count == 1


def test_empty_input_is_rejected(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    with pytest.raises(
        BoomiEnvironmentExtensionsAnalysisError,
        match="must not be empty",
    ):
        analyzer.analyze("")


def test_invalid_xml_is_rejected(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    with pytest.raises(
        BoomiEnvironmentExtensionsAnalysisError,
        match="not well-formed",
    ):
        analyzer.analyze(
            "<EnvironmentExtensions>"
        )


def test_wrong_root_is_rejected(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    with pytest.raises(
        BoomiEnvironmentExtensionsAnalysisError,
        match=(
            "XML root must be "
            "EnvironmentExtensions"
        ),
    ):
        analyzer.analyze(
            "<SomethingElse />"
        )


def test_unknown_elements_are_counted_but_not_interpreted(
    analyzer: BoomiEnvironmentExtensionsAnalyzer,
) -> None:
    xml_text = """\
<EnvironmentExtensions>
  <FutureExtension
      value="SYNTHETIC_FUTURE_SECRET">
    <FutureChild />
  </FutureExtension>
</EnvironmentExtensions>
"""

    analysis = analyzer.analyze(
        xml_text
    )

    counts = dict(
        analysis.element_counts
    )

    assert counts[
        "FutureExtension"
    ] == 1

    assert counts[
        "FutureChild"
    ] == 1

    assert (
        "SYNTHETIC_FUTURE_SECRET"
        not in repr(analysis)
    )