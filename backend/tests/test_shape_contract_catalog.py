"""Tests for shape contract catalog aggregation.

Tests prove that the catalog aggregator:
- aggregates across multiple process definitions
- preserves structural evidence only
- does not retain values/text/identities
- produces deterministic results regardless of input order
- handles multi-process synthetic corpus correctly
"""

from __future__ import annotations

from boomi_builder.services.boomi_process_analyzer import (
    BoomiProcessAnalyzer,
)
from boomi_builder.services.boomi_shape_contract_extractor import (
    BoomiShapeContractExtractor,
    ShapeContractCatalog,
    ShapeContractCatalogAggregator,
    ShapeContractCatalogRenderer,
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


def test_catalog_aggregates_across_processes() -> None:
    """Prove that catalog aggregates instances across multiple processes."""
    # Process A: 2 message shapes with same structure
    process_a_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="message",
            configuration_xml="""
            <message combined="false">
                <msgTxt>textA</msgTxt>
            </message>
""",
        )
        + _create_shape_xml(
            shape_name="shape2",
            shapetype="message",
            configuration_xml="""
            <message combined="false">
                <msgTxt>textB</msgTxt>
            </message>
""",
        )
    )

    # Process B: 3 message shapes with same structure
    process_b_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape3",
            shapetype="message",
            configuration_xml="""
            <message combined="false">
                <msgTxt>textC</msgTxt>
            </message>
""",
        )
        + _create_shape_xml(
            shape_name="shape4",
            shapetype="message",
            configuration_xml="""
            <message combined="false">
                <msgTxt>textD</msgTxt>
            </message>
""",
        )
        + _create_shape_xml(
            shape_name="shape5",
            shapetype="message",
            configuration_xml="""
            <message combined="false">
                <msgTxt>textE</msgTxt>
            </message>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()

    extraction_a = extractor.extract(analyzer.analyze(process_a_xml))
    extraction_b = extractor.extract(analyzer.analyze(process_b_xml))

    catalog = aggregator.aggregate([extraction_a, extraction_b])

    assert catalog.process_definitions_observed == 2
    assert catalog.shapes_observed == 5

    # Should have 1 variant with 5 instances aggregated
    message_entry = catalog.shapetypes[0]
    assert message_entry.shapetype == "message"
    assert message_entry.instances_observed == 5
    assert len(message_entry.variants) == 1
    assert message_entry.variants[0].instances_observed == 5


def test_catalog_groups_different_variants_across_processes() -> None:
    """Prove that different structural variants remain separate in catalog."""
    # Process A: variant X
    process_a_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="custom",
            configuration_xml="""
            <parent>
                <child name="a"/>
            </parent>
""",
        )
    )

    # Process B: variant X and variant Y
    process_b_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape2",
            shapetype="custom",
            configuration_xml="""
            <parent>
                <child name="a"/>
            </parent>
""",
        )
        + _create_shape_xml(
            shape_name="shape3",
            shapetype="custom",
            configuration_xml="""
            <parent>
                <child name="a"/>
                <child name="b"/>
            </parent>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()

    extraction_a = extractor.extract(analyzer.analyze(process_a_xml))
    extraction_b = extractor.extract(analyzer.analyze(process_b_xml))

    catalog = aggregator.aggregate([extraction_a, extraction_b])

    custom_entry = catalog.shapetypes[0]
    assert custom_entry.shapetype == "custom"
    assert custom_entry.instances_observed == 3
    assert len(custom_entry.variants) == 2

    # Variant-001 should have 2 instances (both from A and B)
    # Variant-002 should have 1 instance (from B only)
    variant_counts = {v.variant_id: v.instances_observed for v in custom_entry.variants}
    assert variant_counts.get("variant-001") == 2
    assert variant_counts.get("variant-002") == 1


def test_catalog_deterministic_regardless_of_input_order() -> None:
    """Prove that catalog is deterministic regardless of process input order."""
    process_a_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="message",
            configuration_xml="<message><msgTxt>text</msgTxt></message>",
        )
    )

    process_b_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape2",
            shapetype="decision",
            configuration_xml="<decision condition=\"expr\"/>",
        )
    )

    process_c_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape3",
            shapetype="connectoraction",
            configuration_xml="<connectoraction/>",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()

    extraction_a = extractor.extract(analyzer.analyze(process_a_xml))
    extraction_b = extractor.extract(analyzer.analyze(process_b_xml))
    extraction_c = extractor.extract(analyzer.analyze(process_c_xml))

    # Test different input orders
    catalog_abc = aggregator.aggregate([extraction_a, extraction_b, extraction_c])
    catalog_cba = aggregator.aggregate([extraction_c, extraction_b, extraction_a])
    catalog_bac = aggregator.aggregate([extraction_b, extraction_a, extraction_c])

    # All should produce identical catalog
    assert catalog_abc.process_definitions_observed == catalog_cba.process_definitions_observed
    assert catalog_abc.shapes_observed == catalog_cba.shapes_observed
    assert catalog_abc.shapes_observed == catalog_bac.shapes_observed

    # Shapetype order should be deterministic (alphabetical)
    shapetypes_abc = [s.shapetype for s in catalog_abc.shapetypes]
    shapetypes_cba = [s.shapetype for s in catalog_cba.shapetypes]
    shapetypes_bac = [s.shapetype for s in catalog_bac.shapetypes]

    assert shapetypes_abc == shapetypes_cba == shapetypes_bac


def test_catalog_model_no_value_leakage() -> None:
    """Prove that catalog model does not retain synthetic values."""
    process_xml = _create_process_xml(
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
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()

    extraction = extractor.extract(analyzer.analyze(process_xml))
    catalog = aggregator.aggregate([extraction])

    # Serialize catalog to prove values are absent
    serialized = str(catalog)

    assert "SYNTHETIC_PASSWORD_MUST_NOT_LEAK" not in serialized
    assert "SYNTHETIC_TOKEN_MUST_NOT_LEAK" not in serialized
    assert "SYNTHETIC_COMPONENT_ID_MUST_NOT_LEAK" not in serialized
    assert "SYNTHETIC_SECRET_MUST_NOT_LEAK" not in serialized

    # Structural names should be present
    assert "connectoraction" in serialized
    assert "password" in serialized
    assert "apiToken" in serialized
    assert "connectionId" in serialized
    assert "secretValue" in serialized


def test_catalog_aggregates_multiple_shapetypes() -> None:
    """Prove that catalog handles multiple shapetypes correctly."""
    process_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="message",
            configuration_xml="<message><msgTxt>text</msgTxt></message>",
        )
        + _create_shape_xml(
            shape_name="shape2",
            shapetype="decision",
            configuration_xml="<decision condition=\"expr\"/>",
        )
        + _create_shape_xml(
            shape_name="shape3",
            shapetype="connectoraction",
            configuration_xml="<connectoraction/>",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()

    extraction = extractor.extract(analyzer.analyze(process_xml))
    catalog = aggregator.aggregate([extraction])

    assert catalog.process_definitions_observed == 1
    assert catalog.shapes_observed == 3
    assert len(catalog.shapetypes) == 3

    # Shapetypes should be sorted deterministically
    shapetypes = [s.shapetype for s in catalog.shapetypes]
    assert shapetypes == ["connectoraction", "decision", "message"]


def test_catalog_observed_cardinality_aggregation() -> None:
    """Prove that observed cardinalities aggregate correctly."""
    # Process A: 1 child
    process_a_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="custom",
            configuration_xml="""
            <parent>
                <child name="a"/>
            </parent>
""",
        )
    )

    # Process B: 3 children
    process_b_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape2",
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
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()

    extraction_a = extractor.extract(analyzer.analyze(process_a_xml))
    extraction_b = extractor.extract(analyzer.analyze(process_b_xml))

    catalog = aggregator.aggregate([extraction_a, extraction_b])

    # Since structures differ, should have 2 variants
    custom_entry = catalog.shapetypes[0]
    assert len(custom_entry.variants) == 2

    # Each variant should preserve its own cardinality
    cardinalities = [v.observed_cardinalities for v in custom_entry.variants]

    # One variant should have min=1 max=1, other min=3 max=3
    child_counts = [c.get("parent/child", {}) for c in cardinalities]
    count_ranges = [(c.get("min", 0), c.get("max", 0)) for c in child_counts]

    assert (1, 1) in count_ranges
    assert (3, 3) in count_ranges


def test_catalog_renderer_safe_output() -> None:
    """Prove that renderer produces safe human-readable output."""
    process_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="message",
            configuration_xml="""
            <message combined="false">
                <msgTxt>SYNTHETIC_MESSAGE_MUST_NOT_LEAK</msgTxt>
            </message>
""",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()
    renderer = ShapeContractCatalogRenderer()

    extraction = extractor.extract(analyzer.analyze(process_xml))
    catalog = aggregator.aggregate([extraction])
    rendered = renderer.render(catalog)

    # Should not contain synthetic values
    assert "SYNTHETIC_MESSAGE_MUST_NOT_LEAK" not in rendered

    # Should contain structural information
    assert "SHAPE CONTRACT CATALOG" in rendered
    assert "Process definitions observed : 1" in rendered
    assert "Shapes observed              : 1" in rendered
    assert "SHAPETYPE: message" in rendered
    assert "Structural paths:" in rendered
    assert "message" in rendered
    assert "message/@combined" in rendered
    assert "message/msgTxt" in rendered


def test_catalog_unknown_shapetype_handled_generically() -> None:
    """Prove that unknown shapetypes are handled generically in catalog."""
    process_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="completely_unknown_shapetype_12345",
            configuration_xml="<unknown_element/>",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()

    extraction = extractor.extract(analyzer.analyze(process_xml))
    catalog = aggregator.aggregate([extraction])

    assert catalog.process_definitions_observed == 1
    assert catalog.shapes_observed == 1

    shapetype = catalog.shapetypes[0].shapetype
    assert shapetype == "completely_unknown_shapetype_12345"


def test_catalog_no_configuration_shapes() -> None:
    """Prove that shapes without configuration are handled."""
    process_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="start",
            configuration_xml="",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()

    extraction = extractor.extract(analyzer.analyze(process_xml))
    catalog = aggregator.aggregate([extraction])

    assert catalog.shapes_observed == 1
    assert catalog.shapetypes[0].shapetype == "start"


def test_catalog_message_regression_fixture() -> None:
    """Test synthetic Message fixture in catalog context."""
    process_xml = _create_process_xml(
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
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()

    extraction = extractor.extract(analyzer.analyze(process_xml))
    catalog = aggregator.aggregate([extraction])

    assert catalog.shapes_observed == 1

    message_entry = catalog.shapetypes[0]
    assert message_entry.shapetype == "message"
    assert message_entry.instances_observed == 1

    variant = message_entry.variants[0]

    # Verify structural paths
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

    # Verify no values in catalog
    serialized = str(catalog)
    assert "SYNTHETIC_MESSAGE_TEXT" not in serialized
    assert "SYNTHETIC_STATIC_VALUE" not in serialized
    assert "parameter_key" not in serialized
    assert "property_name" not in serialized


def test_catalog_renderer_deterministic_output() -> None:
    """Prove that renderer produces deterministic output."""
    process_xml = _create_process_xml(
        shapes_xml=_create_shape_xml(
            shape_name="shape1",
            shapetype="message",
            configuration_xml="<message><msgTxt>text</msgTxt></message>",
        )
    )

    analyzer = BoomiProcessAnalyzer()
    extractor = BoomiShapeContractExtractor()
    aggregator = ShapeContractCatalogAggregator()
    renderer = ShapeContractCatalogRenderer()

    extraction = extractor.extract(analyzer.analyze(process_xml))
    catalog = aggregator.aggregate([extraction])

    rendered_1 = renderer.render(catalog)
    rendered_2 = renderer.render(catalog)

    # Should be identical
    assert rendered_1 == rendered_2