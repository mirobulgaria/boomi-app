from __future__ import annotations

import pytest

from boomi_builder.services.boomi_transform_map_analyzer import (
    BoomiTransformMapAnalysisError,
    BoomiTransformMapAnalyzer,
)


SOURCE_PROFILE_ID = (
    "11111111-1111-1111-1111-111111111111"
)

TARGET_PROFILE_ID = (
    "22222222-2222-2222-2222-222222222222"
)


MAP_XML = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    name="Synthetic Customer Map"
    type="transform.map"
    version="1">
  <object>
    <Map
        xmlns=""
        fromProfile="{SOURCE_PROFILE_ID}"
        toProfile="{TARGET_PROFILE_ID}">
      <Mappings>
        <Mapping
            fromKey="10"
            fromKeyPath="*[@key='1']/*[@key='10']"
            fromNamePath="Customer/Id"
            fromType="profile"
            toKey="20"
            toKeyPath="*[@key='2']/*[@key='20']"
            toNamePath="Party/ExternalId"
            toType="profile" />
        <Mapping
            fromKey="11"
            fromKeyPath="*[@key='1']/*[@key='11']"
            fromNamePath="Customer/Name"
            fromType="profile"
            toKey="21"
            toKeyPath="*[@key='2']/*[@key='21']"
            toNamePath="Party/DisplayName"
            toType="profile" />
      </Mappings>
      <Functions optimizeExecutionOrder="true" />
      <Defaults />
      <DocumentCacheJoins />
    </Map>
  </object>
</Component>
"""


IDENTITY_MAP_XML = f"""\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="transform.map">
  <object>
    <Map
        xmlns=""
        fromProfile="{SOURCE_PROFILE_ID}"
        toProfile="{SOURCE_PROFILE_ID}">
      <Mappings>
        <Mapping
            fromKey="10"
            fromKeyPath="*[@key='1']/*[@key='10']"
            fromNamePath="Document/Id"
            fromType="profile"
            toKey="10"
            toKeyPath="*[@key='1']/*[@key='10']"
            toNamePath="Document/Id"
            toType="profile" />
      </Mappings>
      <Functions optimizeExecutionOrder="false" />
      <Defaults />
      <DocumentCacheJoins />
    </Map>
  </object>
</Component>
"""


def analyze(
    xml_text: str = MAP_XML,
):
    return BoomiTransformMapAnalyzer().analyze(
        xml_text
    )


def test_analyzer_reads_profile_references() -> None:
    result = analyze()

    assert (
        result.source_profile_id
        == SOURCE_PROFILE_ID
    )

    assert (
        result.target_profile_id
        == TARGET_PROFILE_ID
    )

    assert result.source_equals_target is False


def test_analyzer_reads_mappings() -> None:
    result = analyze()

    assert result.mapping_count == 2

    first = result.mappings[0]

    assert first.from_key == "10"
    assert first.from_key_path == (
        "*[@key='1']/*[@key='10']"
    )
    assert first.from_name_path == (
        "Customer/Id"
    )
    assert first.from_type == "profile"

    assert first.to_key == "20"
    assert first.to_key_path == (
        "*[@key='2']/*[@key='20']"
    )
    assert first.to_name_path == (
        "Party/ExternalId"
    )
    assert first.to_type == "profile"

    assert first.is_identity is False


def test_analyzer_preserves_mapping_order() -> None:
    result = analyze()

    assert [
        mapping.from_name_path
        for mapping in result.mappings
    ] == [
        "Customer/Id",
        "Customer/Name",
    ]


def test_analyzer_reads_functions_metadata() -> None:
    result = analyze()

    assert (
        result.optimize_execution_order
        is True
    )

    assert result.functions.present is True

    assert result.functions.attributes == (
        (
            "optimizeExecutionOrder",
            "true",
        ),
    )

    assert (
        result.functions.descendant_element_count
        == 0
    )


def test_analyzer_distinguishes_empty_sections() -> None:
    result = analyze()

    assert result.defaults.present is True
    assert result.defaults.attributes == ()
    assert (
        result.defaults.descendant_element_count
        == 0
    )

    assert (
        result.document_cache_joins.present
        is True
    )

    assert (
        result.document_cache_joins.attributes
        == ()
    )

    assert (
        result.document_cache_joins
        .descendant_element_count
        == 0
    )


def test_analyzer_detects_identity_map() -> None:
    result = analyze(
        IDENTITY_MAP_XML
    )

    assert result.source_equals_target is True
    assert result.mapping_count == 1
    assert result.identity_mapping_count == 1
    assert result.all_mappings_are_identity is True

    assert (
        result.mappings[0].is_identity
        is True
    )

    assert (
        result.optimize_execution_order
        is False
    )


def test_analyzer_detects_non_identity_mappings() -> None:
    result = analyze()

    assert result.identity_mapping_count == 0
    assert (
        result.all_mappings_are_identity
        is False
    )


def test_analyzer_handles_missing_optional_sections() -> None:
    xml = f"""\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="transform.map">
  <object>
    <Map
        xmlns=""
        fromProfile="{SOURCE_PROFILE_ID}"
        toProfile="{TARGET_PROFILE_ID}">
      <Mappings />
    </Map>
  </object>
</Component>
"""

    result = analyze(
        xml
    )

    assert result.mapping_count == 0

    assert (
        result.optimize_execution_order
        is None
    )

    assert result.functions.present is False
    assert result.defaults.present is False

    assert (
        result.document_cache_joins.present
        is False
    )

    assert (
        result.all_mappings_are_identity
        is False
    )


def test_analyzer_preserves_unknown_section_content() -> None:
    xml = f"""\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="transform.map">
  <object>
    <Map
        xmlns=""
        fromProfile="{SOURCE_PROFILE_ID}"
        toProfile="{TARGET_PROFILE_ID}">
      <Mappings />
      <Functions optimizeExecutionOrder="true">
        <SyntheticFunction kind="example">
          <NestedValue />
        </SyntheticFunction>
      </Functions>
      <Defaults>
        <SyntheticDefault />
      </Defaults>
      <DocumentCacheJoins>
        <SyntheticJoin />
      </DocumentCacheJoins>
    </Map>
  </object>
</Component>
"""

    result = analyze(
        xml
    )

    assert (
        result.functions.descendant_element_count
        == 2
    )

    assert (
        result.defaults.descendant_element_count
        == 1
    )

    assert (
        result.document_cache_joins
        .descendant_element_count
        == 1
    )


def test_analyzer_allows_partial_mapping_attributes() -> None:
    xml = f"""\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="transform.map">
  <object>
    <Map
        xmlns=""
        fromProfile="{SOURCE_PROFILE_ID}"
        toProfile="{TARGET_PROFILE_ID}">
      <Mappings>
        <Mapping
            fromType="function"
            toKey="20"
            toNamePath="Party/ExternalId"
            toType="profile" />
      </Mappings>
    </Map>
  </object>
</Component>
"""

    result = analyze(
        xml
    )

    assert result.mapping_count == 1

    mapping = result.mappings[0]

    assert mapping.from_key is None
    assert mapping.from_key_path is None
    assert mapping.from_name_path is None
    assert mapping.from_type == "function"

    assert mapping.to_key == "20"
    assert mapping.to_name_path == (
        "Party/ExternalId"
    )

    assert mapping.is_identity is False


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
        BoomiTransformMapAnalysisError,
        match="not well-formed",
    ):
        analyze(
            "<Component>"
        )


def test_analyzer_rejects_non_map_component() -> None:
    xml = MAP_XML.replace(
        'type="transform.map"',
        'type="process"',
        1,
    )

    with pytest.raises(
        BoomiTransformMapAnalysisError,
        match=(
            "Component type must be transform.map"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_rejects_missing_map_definition() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="transform.map">
  <object>
    <SomethingElse />
  </object>
</Component>
"""

    with pytest.raises(
        BoomiTransformMapAnalysisError,
        match="Map definition is missing",
    ):
        analyze(
            xml
        )


def test_analyzer_requires_source_profile() -> None:
    xml = f"""\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="transform.map">
  <object>
    <Map
        xmlns=""
        toProfile="{TARGET_PROFILE_ID}" />
  </object>
</Component>
"""

    with pytest.raises(
        BoomiTransformMapAnalysisError,
        match=(
            "Map attribute 'fromProfile' "
            "is missing"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_requires_target_profile() -> None:
    xml = f"""\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="transform.map">
  <object>
    <Map
        xmlns=""
        fromProfile="{SOURCE_PROFILE_ID}" />
  </object>
</Component>
"""

    with pytest.raises(
        BoomiTransformMapAnalysisError,
        match=(
            "Map attribute 'toProfile' "
            "is missing"
        ),
    ):
        analyze(
            xml
        )


def test_analyzer_rejects_invalid_boolean() -> None:
    xml = MAP_XML.replace(
        'optimizeExecutionOrder="true"',
        'optimizeExecutionOrder="maybe"',
        1,
    )

    with pytest.raises(
        BoomiTransformMapAnalysisError,
        match=(
            "Attribute 'optimizeExecutionOrder' "
            "must be true or false"
        ),
    ):
        analyze(
            xml
        )