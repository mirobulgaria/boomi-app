from __future__ import annotations

import pytest

from boomi_builder.services.boomi_process_analyzer import (
    BoomiProcessAnalysisError,
    BoomiProcessAnalyzer,
)


MAP_ID = (
    "11111111-1111-1111-1111-111111111111"
)

CONNECTION_ID = (
    "22222222-2222-2222-2222-222222222222"
)

OPERATION_ID = (
    "33333333-3333-3333-3333-333333333333"
)


PROCESS_XML = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    name="Synthetic Order Process"
    type="process"
    version="1">
  <object>
    <process
        xmlns=""
        allowSimultaneous="false"
        enableUserLog="false"
        stopProcessingIfZeroDocuments="true"
        workload="general">
      <shapes>
        <shape
            image="start"
            name="startShape"
            shapetype="start"
            userlabel=""
            x="100.0"
            y="100.0">
          <configuration>
            <passthroughaction />
          </configuration>
          <dragpoints>
            <dragpoint
                name="startShape.out"
                toShape="mapShape"
                x="200.0"
                y="100.0" />
          </dragpoints>
        </shape>

        <shape
            image="map_icon"
            name="mapShape"
            shapetype="map"
            userlabel="Transform Customer"
            x="300.0"
            y="100.0">
          <configuration>
            <map mapId="{MAP_ID}" />
          </configuration>
          <dragpoints>
            <dragpoint
                name="mapShape.out"
                toShape="sendShape"
                x="400.0"
                y="100.0" />
          </dragpoints>
        </shape>

        <shape
            image="returndocuments_icon"
            name="returnShape"
            shapetype="returndocuments"
            userlabel=""
            x="700.0"
            y="100.0">
          <configuration>
            <returndocuments label="" />
          </configuration>
          <dragpoints />
        </shape>

        <shape
            image="connectoraction_icon"
            name="sendShape"
            shapetype="connectoraction"
            userlabel="Send Customer"
            x="500.0"
            y="100.0">
          <configuration>
            <connectoraction
                actionType="EXECUTE"
                allowDynamicCredentials="false"
                connectionId="{CONNECTION_ID}"
                connectorType="syntheticconnector"
                hideSettings="false"
                operationId="{OPERATION_ID}">
              <parameters>
                <parameter
                    name="mode"
                    value="example" />
              </parameters>
              <dynamicProperties />
            </connectoraction>
          </configuration>
          <dragpoints>
            <dragpoint
                name="sendShape.out"
                toShape="returnShape"
                x="600.0"
                y="100.0" />
          </dragpoints>
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""


def analyze(
    xml_text: str = PROCESS_XML,
):
    return BoomiProcessAnalyzer().analyze(
        xml_text
    )


def test_analyzer_reads_process_settings() -> None:
    result = analyze()

    settings = dict(
        result.settings
    )

    assert settings[
        "allowSimultaneous"
    ] == "false"

    assert settings[
        "enableUserLog"
    ] == "false"

    assert settings[
        "stopProcessingIfZeroDocuments"
    ] == "true"

    assert settings[
        "workload"
    ] == "general"


def test_analyzer_reads_shapes() -> None:
    result = analyze()

    assert result.shape_count == 4

    assert [
        shape.name
        for shape in result.shapes
    ] == [
        "startShape",
        "mapShape",
        "returnShape",
        "sendShape",
    ]

    assert [
        shape.shape_type
        for shape in result.shapes
    ] == [
        "start",
        "map",
        "returndocuments",
        "connectoraction",
    ]


def test_analyzer_preserves_layout_metadata() -> None:
    result = analyze()

    map_shape = result.shapes[1]

    assert map_shape.image == "map_icon"
    assert map_shape.x == "300.0"
    assert map_shape.y == "100.0"

    assert (
        map_shape.user_label
        == "Transform Customer"
    )


def test_analyzer_reads_configuration_roots() -> None:
    result = analyze()

    assert (
        result.shapes[0]
        .configuration_root_names
        == ("passthroughaction",)
    )

    assert (
        result.shapes[1]
        .configuration_root_names
        == ("map",)
    )

    assert (
        result.shapes[2]
        .configuration_root_names
        == ("returndocuments",)
    )

    assert (
        result.shapes[3]
        .configuration_root_names
        == ("connectoraction",)
    )


def test_analyzer_preserves_nested_configuration() -> None:
    result = analyze()

    connector = (
        result.shapes[3]
        .configuration[0]
    )

    assert connector.name == (
        "connectoraction"
    )

    assert [
        child.name
        for child in connector.children
    ] == [
        "parameters",
        "dynamicProperties",
    ]

    parameters = connector.children[0]

    assert len(parameters.children) == 1

    parameter = parameters.children[0]

    assert parameter.name == "parameter"

    assert dict(
        parameter.attributes
    ) == {
        "name": "mode",
        "value": "example",
    }


def test_analyzer_reads_transitions_from_dragpoints() -> None:
    result = analyze()

    assert result.transition_count == 3

    assert [
        (
            transition.source_shape,
            transition.target_shape,
        )
        for transition in result.transitions
    ] == [
        (
            "startShape",
            "mapShape",
        ),
        (
            "mapShape",
            "sendShape",
        ),
        (
            "sendShape",
            "returnShape",
        ),
    ]


def test_execution_graph_does_not_depend_on_xml_shape_order() -> None:
    result = analyze()

    assert [
        shape.name
        for shape in result.shapes
    ] == [
        "startShape",
        "mapShape",
        "returnShape",
        "sendShape",
    ]

    assert [
        (
            transition.source_shape,
            transition.target_shape,
        )
        for transition in result.transitions
    ] == [
        (
            "startShape",
            "mapShape",
        ),
        (
            "mapShape",
            "sendShape",
        ),
        (
            "sendShape",
            "returnShape",
        ),
    ]


def test_analyzer_discovers_component_references_generically() -> None:
    result = analyze()

    references = (
        result.referenced_components
    )

    assert len(references) == 3

    assert [
        reference.component_id
        for reference in references
    ] == [
        MAP_ID,
        CONNECTION_ID,
        OPERATION_ID,
    ]

    assert [
        reference.attribute_name
        for reference in references
    ] == [
        "mapId",
        "connectionId",
        "operationId",
    ]


def test_analyzer_returns_unique_referenced_component_ids() -> None:
    result = analyze()

    assert (
        result.referenced_component_ids
        == (
            MAP_ID,
            CONNECTION_ID,
            OPERATION_ID,
        )
    )


def test_reference_contains_shape_and_element_context() -> None:
    result = analyze()

    map_reference = (
        result.referenced_components[0]
    )

    assert (
        map_reference.shape_name
        == "mapShape"
    )

    assert (
        map_reference.element_name
        == "map"
    )

    assert (
        map_reference.attribute_name
        == "mapId"
    )

    assert (
        map_reference.component_id
        == MAP_ID
    )


def test_analyzer_allows_process_without_shapes() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="" workload="general" />
  </object>
</Component>
"""

    result = analyze(
        xml
    )

    assert result.shape_count == 0
    assert result.transition_count == 0

    assert (
        result.referenced_component_ids
        == ()
    )


def test_analyzer_allows_shape_without_configuration() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="">
      <shapes>
        <shape
            name="shapeA"
            shapetype="custom">
          <dragpoints />
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""

    result = analyze(
        xml
    )

    assert result.shape_count == 1

    shape = result.shapes[0]

    assert shape.name == "shapeA"
    assert shape.shape_type == "custom"
    assert shape.configuration == ()
    assert shape.references == ()


def test_analyzer_preserves_unknown_configuration_type() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="">
      <shapes>
        <shape
            name="shapeA"
            shapetype="future-shape">
          <configuration>
            <futureconfiguration
                mode="example">
              <nested value="123" />
            </futureconfiguration>
          </configuration>
          <dragpoints />
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""

    result = analyze(
        xml
    )

    shape = result.shapes[0]

    assert (
        shape.configuration_root_names
        == ("futureconfiguration",)
    )

    configuration = (
        shape.configuration[0]
    )

    assert configuration.name == (
        "futureconfiguration"
    )

    assert dict(
        configuration.attributes
    ) == {
        "mode": "example",
    }

    assert (
        configuration.children[0].name
        == "nested"
    )


def test_non_uuid_configuration_values_are_not_component_references() -> None:
    result = analyze()

    values = {
        reference.component_id
        for reference
        in result.referenced_components
    }

    assert "EXECUTE" not in values
    assert "syntheticconnector" not in values
    assert "example" not in values


def test_analyzer_rejects_duplicate_shape_names() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="">
      <shapes>
        <shape
            name="duplicate"
            shapetype="start" />
        <shape
            name="duplicate"
            shapetype="stop" />
      </shapes>
    </process>
  </object>
</Component>
"""

    with pytest.raises(
        BoomiProcessAnalysisError,
        match=(
            "Duplicate process shape name"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_ignores_unset_transition_target() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="">
      <shapes>
        <shape
            name="shapeA"
            shapetype="start">
          <dragpoints>
            <dragpoint
                name="shapeA.out"
                toShape="unset"
                x="200.0"
                y="100.0" />
          </dragpoints>
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""

    result = analyze(
        xml
    )

    assert result.shape_count == 1
    assert result.transition_count == 0
    assert result.transitions == ()


def test_analyzer_rejects_transition_to_unknown_shape() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="">
      <shapes>
        <shape
            name="shapeA"
            shapetype="start">
          <dragpoints>
            <dragpoint
                name="shapeA.out"
                toShape="missingShape" />
          </dragpoints>
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""

    with pytest.raises(
        BoomiProcessAnalysisError,
        match=(
            "Process transition target "
            "does not exist"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_rejects_dragpoint_without_target() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="">
      <shapes>
        <shape
            name="shapeA"
            shapetype="start">
          <dragpoints>
            <dragpoint
                name="shapeA.out" />
          </dragpoints>
        </shape>
      </shapes>
    </process>
  </object>
</Component>
"""

    with pytest.raises(
        BoomiProcessAnalysisError,
        match=(
            "dragpoint attribute "
            "'toShape' is missing"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_rejects_shape_without_name() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="">
      <shapes>
        <shape shapetype="start" />
      </shapes>
    </process>
  </object>
</Component>
"""

    with pytest.raises(
        BoomiProcessAnalysisError,
        match=(
            "shape attribute 'name' "
            "is missing"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_rejects_shape_without_type() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <process xmlns="">
      <shapes>
        <shape name="shapeA" />
      </shapes>
    </process>
  </object>
</Component>
"""

    with pytest.raises(
        BoomiProcessAnalysisError,
        match=(
            "shape attribute 'shapetype' "
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
        BoomiProcessAnalysisError,
        match="not well-formed",
    ):
        analyze(
            "<Component>"
        )


def test_analyzer_rejects_non_process_component() -> None:
    xml = PROCESS_XML.replace(
        'type="process"',
        'type="transform.map"',
        1,
    )

    with pytest.raises(
        BoomiProcessAnalysisError,
        match=(
            "Component type must be process"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_rejects_missing_process_definition() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="process">
  <object>
    <SomethingElse />
  </object>
</Component>
"""

    with pytest.raises(
        BoomiProcessAnalysisError,
        match="Process definition is missing",
    ):
        analyze(
            xml
        )