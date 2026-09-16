"""Tests for Boomi shape contract extractor.

Tests prove that the extractor:
- discards attribute values
- discards element text
- discards component identities
- produces deterministic structural fingerprints
- groups structurally identical instances
- handles unknown shapetypes generically
- produces no security leaks
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from boomi_builder.services.boomi_process_analyzer import (
    BoomiProcessAnalyzer,
    ProcessShape,
)
from boomi_builder.services.boomi_shape_contract_extractor import (
    BoomiShapeContractExtractor,
    ConfigurationStructure,
    ShapeInstanceStructure,
)


def _create_process_xml(*, shapes_xml: str) -> str:
    """Helper to create synthetic process XML."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    name="Test Process"
    type="process"
    version="1">
  <object>
    <process xmlns="" workload="general">
      <shapes>
{shapes_xml}
      </shapes>
    </process>
  </object>
</Component>
"""


def _create_shape_xml(
    *,
    shape_name: str,
    shapetype: str,
    configuration_xml: str = "",
) -> str:
    """Helper to create synthetic shape XML."""
    return f"""        <shape
            name="{shape_name}"
            shapetype="{shapetype}"
            x="100.0"
            y="100.0">
          <configuration>
{configuration_xml}
          </configuration>
        </shape>"""


def test_configuration_structure_discards_attribute_values() -> None:
    """Prove that ConfigurationStructure does not retain attribute values."""
    xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="connectoraction",
            configuration_xml="""
            <connectoraction
                password="SYNTHETIC_PASSWORD_MUST_NOT_LEAK"
                apiToken="SYNTHETIC_TOKEN_MUST_NOT_LEAK"
                connectionId="SYNTHETIC_COMPONENT_ID_MUST_NOT_LEAK">
            </connectoraction>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis = analyzer.analyze(xml)

    extractor = BoomiShapeContractExtractor()
    instance_structure = extractor._shape_to_instance_structure(analysis.shapes[0])

    assert instance_structure.configuration_structure is not None

    structure = instance_structure.configuration_structure

    # Attribute names should be present
    assert "password" in structure.attribute_names
    assert "apiToken" in structure.attribute_names
    assert "connectionId" in structure.attribute_names

    # Serialize structure to prove values are absent
    serialized = str(structure)
    assert "SYNTHETIC_PASSWORD_MUST_NOT_LEAK" not in serialized
    assert "SYNTHETIC_TOKEN_MUST_NOT_LEAK" not in serialized
    assert "SYNTHETIC_COMPONENT_ID_MUST_NOT_LEAK" not in serialized


def test_configuration_structure_discards_element_text() -> None:
    """Prove that ConfigurationStructure does not retain element text."""
    xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="message",
            configuration_xml="""
            <message>
                <msgTxt>SYNTHETIC_MESSAGE_MUST_NOT_LEAK</msgTxt>
            </message>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis = analyzer.analyze(xml)

    extractor = BoomiShapeContractExtractor()
    instance_structure = extractor._shape_to_instance_structure(analysis.shapes[0])

    assert instance_structure.configuration_structure is not None

    structure = instance_structure.configuration_structure

    # Find the msgTxt child element
    msgtxt_child = None
    for child in structure.children:
        if child.element_name == "msgTxt":
            msgtxt_child = child
            break

    assert msgtxt_child is not None

    # Element name should be present
    assert msgtxt_child.element_name == "msgTxt"

    # Serialize structure to prove text is absent
    serialized = str(msgtxt_child)
    assert "SYNTHETIC_MESSAGE_MUST_NOT_LEAK" not in serialized


def test_identical_structure_different_values_same_fingerprint() -> None:
    """Prove that values do not affect fingerprint."""
    xml1 = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="connectoraction",
            configuration_xml="""
            <connectoraction
                password="value1"
                token="value2">
            </connectoraction>
""",
        )
    )

    xml2 = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape2",
            shapetype="connectoraction",
            configuration_xml="""
            <connectoraction
                password="different_value"
                token="another_value">
            </connectoraction>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis1 = analyzer.analyze(xml1)
    analysis2 = analyzer.analyze(xml2)

    extractor = BoomiShapeContractExtractor()
    structure1 = extractor._shape_to_instance_structure(analysis1.shapes[0])
    structure2 = extractor._shape_to_instance_structure(analysis2.shapes[0])

    fingerprint1 = structure1.compute_fingerprint()
    fingerprint2 = structure2.compute_fingerprint()

    # Fingerprints should be identical (only structure matters)
    assert fingerprint1 == fingerprint2


def test_identical_structure_different_text_same_fingerprint() -> None:
    """Prove that element text does not affect fingerprint."""
    xml1 = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="message",
            configuration_xml="""
            <message>
                <msgTxt>message content one</msgTxt>
            </message>
""",
        )
    )

    xml2 = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape2",
            shapetype="message",
            configuration_xml="""
            <message>
                <msgTxt>different message content</msgTxt>
            </message>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis1 = analyzer.analyze(xml1)
    analysis2 = analyzer.analyze(xml2)

    extractor = BoomiShapeContractExtractor()
    structure1 = extractor._shape_to_instance_structure(analysis1.shapes[0])
    structure2 = extractor._shape_to_instance_structure(analysis2.shapes[0])

    fingerprint1 = structure1.compute_fingerprint()
    fingerprint2 = structure2.compute_fingerprint()

    # Fingerprints should be identical
    assert fingerprint1 == fingerprint2


def test_different_attribute_presence_different_fingerprint() -> None:
    """Prove that attribute presence affects fingerprint."""
    xml1 = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="connectoraction",
            configuration_xml="""
            <connectoraction password="value">
            </connectoraction>
""",
        )
    )

    xml2 = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape2",
            shapetype="connectoraction",
            configuration_xml="""
            <connectoraction password="value" token="value">
            </connectoraction>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis1 = analyzer.analyze(xml1)
    analysis2 = analyzer.analyze(xml2)

    extractor = BoomiShapeContractExtractor()
    structure1 = extractor._shape_to_instance_structure(analysis1.shapes[0])
    structure2 = extractor._shape_to_instance_structure(analysis2.shapes[0])

    fingerprint1 = structure1.compute_fingerprint()
    fingerprint2 = structure2.compute_fingerprint()

    # Fingerprints should differ (different attribute presence)
    assert fingerprint1 != fingerprint2


def test_different_child_presence_different_fingerprint() -> None:
    """Prove that child presence affects fingerprint."""
    xml1 = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="message",
            configuration_xml="""
            <message>
                <msgTxt>text</msgTxt>
            </message>
""",
        )
    )

    xml2 = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape2",
            shapetype="message",
            configuration_xml="""
            <message>
                <msgTxt>text</msgTxt>
                <msgParameters>
                    <parametervalue>
                        <staticparameter/>
                    </parametervalue>
                </msgParameters>
            </message>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis1 = analyzer.analyze(xml1)
    analysis2 = analyzer.analyze(xml2)

    extractor = BoomiShapeContractExtractor()
    structure1 = extractor._shape_to_instance_structure(analysis1.shapes[0])
    structure2 = extractor._shape_to_instance_structure(analysis2.shapes[0])

    fingerprint1 = structure1.compute_fingerprint()
    fingerprint2 = structure2.compute_fingerprint()

    # Fingerprints should differ (different child presence)
    assert fingerprint1 != fingerprint2


def test_repeated_child_structure_observed() -> None:
    """Prove that repeated children are represented in structure."""
    xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="custom",
            configuration_xml="""
            <parent>
                <child name="a"/>
                <child name="b"/>
                <child name="c"/>
            </parent>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis = analyzer.analyze(xml)

    extractor = BoomiShapeContractExtractor()
    structure = extractor._shape_to_instance_structure(analysis.shapes[0])

    assert structure.configuration_structure is not None

    cardinalities = structure.configuration_structure.get_observed_cardinalities()

    # Should observe 3 children
    assert "parent/child" in cardinalities
    assert cardinalities["parent/child"]["min"] == 3
    assert cardinalities["parent/child"]["max"] == 3


def test_unknown_shapetype_handled_generically() -> None:
    """Prove that unknown shapetypes are handled without special logic."""
    xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="completely_unknown_shapetype_12345",
            configuration_xml="""
            <unknown_element>
                <nested>text</nested>
            </unknown_element>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis = analyzer.analyze(xml)

    extractor = BoomiShapeContractExtractor()
    extraction = extractor.extract(analysis)

    # Should extract successfully despite unknown shapetype
    assert extraction.total_shapes_observed == 1

    # Should group by shapetype name
    assert len(extraction.shapetype_observations) == 1
    assert extraction.shapetype_observations[0].shapetype == "completely_unknown_shapetype_12345"


def test_message_regression_fixture_structure() -> None:
    """Test synthetic Message fixture reproduces observed structure."""
    xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="messageShape",
            shapetype="message",
            configuration_xml="""
            <message combined="false">
                <msgTxt>SYNTHETIC_MESSAGE_TEXT</msgTxt>
                <msgParameters>
                    <parametervalue
                        key="parameter_key"
                        usesEncryption="false"
                        valueType="static">
                        <staticparameter staticproperty="property_name">
                            SYNTHETIC_STATIC_VALUE
                        </staticparameter>
                    </parametervalue>
                </msgParameters>
            </message>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis = analyzer.analyze(xml)

    extractor = BoomiShapeContractExtractor()
    extraction = extractor.extract(analysis)

    assert extraction.total_shapes_observed == 1

    observation = extraction.shapetype_observations[0]
    assert observation.shapetype == "message"
    assert observation.total_instances == 1
    assert observation.distinct_variants == 1

    variant = observation.variants[0]
    structure = variant.structure

    assert structure is not None

    # Verify expected element hierarchy
    paths = variant.structural_paths
    assert "message" in paths
    assert "message/@combined" in paths
    assert "message/msgTxt" in paths
    assert "message/msgParameters" in paths
    assert "message/msgParameters/parametervalue" in paths
    assert "message/msgParameters/parametervalue/@key" in paths
    assert "message/msgParameters/parametervalue/@usesEncryption" in paths
    assert "message/msgParameters/parametervalue/@valueType" in paths
    assert "message/msgParameters/parametervalue/staticparameter" in paths
    assert "message/msgParameters/parametervalue/staticparameter/@staticproperty" in paths

    # Verify no values in model
    assert "SYNTHETIC_MESSAGE_TEXT" not in str(structure)
    assert "SYNTHETIC_STATIC_VALUE" not in str(structure)
    assert "parameter_key" not in str(structure)
    assert "property_name" not in str(structure)


def test_model_serialization_no_leakage() -> None:
    """Prove that model serialization does not contain synthetic values."""
    xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="connectoraction",
            configuration_xml="""
            <connectoraction
                password="SYNTHETIC_PASSWORD_MUST_NOT_LEAK"
                apiToken="SYNTHETIC_TOKEN_MUST_NOT_LEAK"
                connectionId="SYNTHETIC_COMPONENT_ID_MUST_NOT_LEAK">
                <secretValue>SYNTHETIC_SECRET_MUST_NOT_LEAK</secretValue>
            </connectoraction>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis = analyzer.analyze(xml)

    extractor = BoomiShapeContractExtractor()
    extraction = extractor.extract(analysis)

    # Serialize the entire extraction result
    serialized = str(extraction)

    # Prove synthetic values are absent
    assert "SYNTHETIC_PASSWORD_MUST_NOT_LEAK" not in serialized
    assert "SYNTHETIC_TOKEN_MUST_NOT_LEAK" not in serialized
    assert "SYNTHETIC_COMPONENT_ID_MUST_NOT_LEAK" not in serialized
    assert "SYNTHETIC_SECRET_MUST_NOT_LEAK" not in serialized

    # Prove structural names are present
    assert "connectoraction" in serialized
    assert "password" in serialized
    assert "apiToken" in serialized
    assert "connectionId" in serialized
    assert "secretValue" in serialized


def test_multiple_variants_grouped_correctly() -> None:
    """Prove that multiple structural variants are grouped separately."""
    xml = _create_process_xml(
        shapes_xml="""
""" + _create_shape_xml(
            shape_name="shape1",
            shapetype="custom",
            configuration_xml="""
            <parent>
                <child name="a"/>
            </parent>
""",
        )
        + _create_shape_xml(
            shape_name="shape2",
            shapetype="custom",
            configuration_xml="""
            <parent>
                <child name="a"/>
                <child name="b"/>
            </parent>
""",
        )
        + _create_shape_xml(
            shape_name="shape3",
            shapetype="custom",
            configuration_xml="""
            <parent>
                <child name="a"/>
            </parent>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis = analyzer.analyze(xml)

    extractor = BoomiShapeContractExtractor()
    extraction = extractor.extract(analysis)

    observation = extraction.shapetype_observations[0]
    assert observation.shapetype == "custom"
    assert observation.total_instances == 3
    assert observation.distinct_variants == 2

    # Verify grouping: variant-001 has 2 instances, variant-002 has 1
    variant_counts = {v.variant_id: v.instance_count for v in observation.variants}
    assert variant_counts.get("variant-001") == 2  # identical structures
    assert variant_counts.get("variant-002") == 1  # different structure


def test_deterministic_variant_ordering() -> None:
    """Prove that variant IDs are assigned deterministically."""
    xml = _create_process_xml(
        shapes_xml="""
""" + _create_shape_xml(
            shape_name="shape1",
            shapetype="custom",
            configuration_xml="<structureA/>",
        )
        + _create_shape_xml(
            shape_name="shape2",
            shapetype="custom",
            configuration_xml="<structureB/>",
        )
        + _create_shape_xml(
            shape_name="shape3",
            shapetype="custom",
            configuration_xml="<structureC/>",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis = analyzer.analyze(xml)

    extractor = BoomiShapeContractExtractor()
    extraction1 = extractor.extract(analysis)
    extraction2 = extractor.extract(analysis)

    # Should produce identical results
    assert extraction1.total_distinct_variants == extraction2.total_distinct_variants

    # Variant IDs should be deterministic
    variant_ids_1 = [v.variant_id for v in extraction1.shapetype_observations[0].variants]
    variant_ids_2 = [v.variant_id for v in extraction2.shapetype_observations[0].variants]

    assert variant_ids_1 == variant_ids_2
    assert variant_ids_1 == ["variant-001", "variant-002", "variant-003"]


def test_no_configuration_no_crash() -> None:
    """Prove that shapes without configuration are handled gracefully."""
    xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="start",
            configuration_xml="",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    analysis = analyzer.analyze(xml)

    extractor = BoomiShapeContractExtractor()
    extraction = extractor.extract(analysis)

    assert extraction.total_shapes_observed == 1
    assert extraction.shapetype_observations[0].shapetype == "start"

    # Variant should indicate no configuration
    variant = extraction.shapetype_observations[0].variants[0]
    assert variant.structure is None