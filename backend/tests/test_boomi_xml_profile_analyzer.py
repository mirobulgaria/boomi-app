from __future__ import annotations

import pytest

from boomi_builder.services.boomi_xml_profile_analyzer import (
    BoomiXmlProfileAnalysisError,
    BoomiXmlProfileAnalyzer,
)


PROFILE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="798a16a7-de85-4dd1-bee7-5b80fd84a734"
    name="PRF S1 - SAP MR Request - ZDVMBG_MR_REQUEST"
    type="profile.xml"
    version="7">
  <object>
    <XMLProfile
        xmlns=""
        modelVersion="2"
        strict="true">
      <ProfileProperties />
      <DataElements>
        <XMLElement
            dataType="character"
            isMappable="true"
            isNode="true"
            key="1"
            maxOccurs="1"
            minOccurs="1"
            name="ZDVMBG_MR_REQUEST"
            typeExpanded="false"
            typeKey="-1"
            useNamespace="-1">
          <DataFormat />
          <XMLElement
              dataType="character"
              isMappable="true"
              isNode="true"
              key="198"
              loopingOption="unique"
              maxOccurs="1"
              minOccurs="1"
              name="IDOC"
              typeExpanded="true"
              typeKey="5"
              typeName="ZDVMBG_MR_ORDER_AMR.ZDVMBG_MR_REQUEST"
              useNamespace="-1"
              validateData="false">
            <DataFormat />
            <XMLAttribute
                dataType="character"
                isMappable="true"
                isNode="true"
                key="200"
                name="BEGIN"
                required="true"
                useNamespace="-1"
                validateData="false" />
            <XMLElement
                dataType="character"
                isMappable="true"
                isNode="true"
                key="204"
                loopingOption="unique"
                maxOccurs="999999999"
                minOccurs="1"
                name="Z1DVMBG_MRINSTPL"
                typeExpanded="true"
                typeKey="49"
                typeName="ZDVMBG_MR_REQUEST.Z1DVMBG_MRINSTPL"
                useNamespace="-1"
                validateData="false">
              <DataFormat />
              <XMLAttribute
                  dataType="character"
                  isMappable="true"
                  isNode="true"
                  key="282"
                  name="SEGMENT"
                  required="true"
                  useNamespace="-1"
                  validateData="false" />
              <XMLElement
                  comments="Point of delivery ID"
                  dataType="character"
                  isMappable="true"
                  isNode="true"
                  key="318"
                  loopingOption="unique"
                  maxLength="50"
                  maxOccurs="1"
                  minOccurs="0"
                  name="PM_ID"
                  typeKey="-1"
                  useNamespace="-1"
                  validateData="true">
                <DataFormat />
              </XMLElement>
              <XMLElement
                  dataType="character"
                  isMappable="true"
                  isNode="true"
                  key="366"
                  loopingOption="unique"
                  maxOccurs="999999999"
                  minOccurs="1"
                  name="Z1DVMBG_MRINSTDEV"
                  typeExpanded="true"
                  typeKey="109"
                  typeName="ZDVMBG_MR_REQUEST.Z1DVMBG_MRINSTDEV"
                  useNamespace="-1"
                  validateData="false">
                <DataFormat />
                <XMLAttribute
                    dataType="character"
                    isMappable="true"
                    isNode="true"
                    key="396"
                    name="SEGMENT"
                    required="true"
                    useNamespace="-1"
                    validateData="false" />
                <XMLElement
                    comments="Manufacturer serial number"
                    dataType="character"
                    isMappable="true"
                    isNode="true"
                    key="402"
                    loopingOption="unique"
                    maxLength="30"
                    maxOccurs="1"
                    minOccurs="0"
                    name="SERGE"
                    typeKey="-1"
                    useNamespace="-1"
                    validateData="true">
                  <DataFormat />
                </XMLElement>
                <XMLElement
                    comments="Meter reading type"
                    dataType="character"
                    isMappable="true"
                    isNode="true"
                    key="420"
                    loopingOption="unique"
                    maxLength="2"
                    maxOccurs="1"
                    minOccurs="0"
                    name="ISTABLART"
                    typeKey="-1"
                    useNamespace="-1"
                    validateData="true">
                  <DataFormat />
                </XMLElement>
                <XMLElement
                    dataType="character"
                    isMappable="true"
                    isNode="true"
                    key="432"
                    loopingOption="unique"
                    maxOccurs="999999999"
                    minOccurs="1"
                    name="Z1DVMBG_MRINSTREG"
                    typeExpanded="true"
                    typeKey="171"
                    typeName="ZDVMBG_MR_REQUEST.Z1DVMBG_MRINSTREG"
                    useNamespace="-1"
                    validateData="false">
                  <DataFormat />
                  <XMLAttribute
                      dataType="character"
                      isMappable="true"
                      isNode="true"
                      key="508"
                      name="SEGMENT"
                      required="true"
                      useNamespace="-1"
                      validateData="false" />
                  <XMLElement
                      comments="Internal ID for meter reading document"
                      dataType="character"
                      isMappable="true"
                      isNode="true"
                      key="510"
                      loopingOption="unique"
                      maxLength="20"
                      maxOccurs="1"
                      minOccurs="0"
                      name="ABLBELNR"
                      typeKey="-1"
                      useNamespace="-1"
                      validateData="true">
                    <DataFormat />
                    <QualifierList />
                  </XMLElement>
                </XMLElement>
              </XMLElement>
            </XMLElement>
          </XMLElement>
        </XMLElement>
      </DataElements>
      <Namespaces />
      <tagLists />
    </XMLProfile>
  </object>
</Component>
"""


def analyze():
    return BoomiXmlProfileAnalyzer().analyze(
        PROFILE_XML
    )


def test_analyzer_reads_profile_contract() -> None:
    result = analyze()

    assert result.model_version == "2"
    assert result.strict is True

    assert result.root_paths == (
        "ZDVMBG_MR_REQUEST",
    )

    assert result.element_count == 9
    assert result.attribute_count == 4


def test_analyzer_preserves_full_hierarchy() -> None:
    result = analyze()

    expected_paths = {
        "ZDVMBG_MR_REQUEST",
        "ZDVMBG_MR_REQUEST/IDOC",
        (
            "ZDVMBG_MR_REQUEST/IDOC/"
            "Z1DVMBG_MRINSTPL"
        ),
        (
            "ZDVMBG_MR_REQUEST/IDOC/"
            "Z1DVMBG_MRINSTPL/PM_ID"
        ),
        (
            "ZDVMBG_MR_REQUEST/IDOC/"
            "Z1DVMBG_MRINSTPL/"
            "Z1DVMBG_MRINSTDEV"
        ),
        (
            "ZDVMBG_MR_REQUEST/IDOC/"
            "Z1DVMBG_MRINSTPL/"
            "Z1DVMBG_MRINSTDEV/SERGE"
        ),
        (
            "ZDVMBG_MR_REQUEST/IDOC/"
            "Z1DVMBG_MRINSTPL/"
            "Z1DVMBG_MRINSTDEV/ISTABLART"
        ),
        (
            "ZDVMBG_MR_REQUEST/IDOC/"
            "Z1DVMBG_MRINSTPL/"
            "Z1DVMBG_MRINSTDEV/"
            "Z1DVMBG_MRINSTREG"
        ),
        (
            "ZDVMBG_MR_REQUEST/IDOC/"
            "Z1DVMBG_MRINSTPL/"
            "Z1DVMBG_MRINSTDEV/"
            "Z1DVMBG_MRINSTREG/ABLBELNR"
        ),
    }

    actual_paths = {
        element.path
        for element in result.elements
    }

    assert actual_paths == expected_paths


def test_analyzer_reads_repeating_segment_cardinality() -> None:
    result = analyze()

    installation = result.find_by_name(
        "Z1DVMBG_MRINSTPL"
    )[0]

    device = result.find_by_name(
        "Z1DVMBG_MRINSTDEV"
    )[0]

    register = result.find_by_name(
        "Z1DVMBG_MRINSTREG"
    )[0]

    for element in (
        installation,
        device,
        register,
    ):
        assert element.min_occurs == 1
        assert element.max_occurs == 999999999
        assert element.repeating is True


def test_analyzer_reads_leaf_constraints() -> None:
    result = analyze()

    pm_id = result.find_by_name(
        "PM_ID"
    )[0]

    serge = result.find_by_name(
        "SERGE"
    )[0]

    istablart = result.find_by_name(
        "ISTABLART"
    )[0]

    ablbelnr = result.find_by_name(
        "ABLBELNR"
    )[0]

    assert pm_id.min_occurs == 0
    assert pm_id.max_occurs == 1
    assert pm_id.max_length == 50
    assert pm_id.comments == (
        "Point of delivery ID"
    )

    assert serge.min_occurs == 0
    assert serge.max_occurs == 1
    assert serge.max_length == 30

    assert istablart.min_occurs == 0
    assert istablart.max_occurs == 1
    assert istablart.max_length == 2
    assert istablart.comments == (
        "Meter reading type"
    )

    assert ablbelnr.min_occurs == 0
    assert ablbelnr.max_occurs == 1
    assert ablbelnr.max_length == 20
    assert ablbelnr.comments == (
        "Internal ID for meter reading document"
    )


def test_analyzer_preserves_parent_and_child_paths() -> None:
    result = analyze()

    device_path = (
        "ZDVMBG_MR_REQUEST/IDOC/"
        "Z1DVMBG_MRINSTPL/"
        "Z1DVMBG_MRINSTDEV"
    )

    device = result.find_by_path(
        device_path
    )

    assert device is not None

    assert device.parent_path == (
        "ZDVMBG_MR_REQUEST/IDOC/"
        "Z1DVMBG_MRINSTPL"
    )

    assert device.depth == 3

    assert set(
        device.child_paths
    ) == {
        f"{device_path}/SERGE",
        f"{device_path}/ISTABLART",
        f"{device_path}/Z1DVMBG_MRINSTREG",
    }


def test_analyzer_reads_xml_attributes() -> None:
    result = analyze()

    idoc = result.find_by_name(
        "IDOC"
    )[0]

    assert len(idoc.attributes) == 1

    begin = idoc.attributes[0]

    assert begin.key == "200"
    assert begin.name == "BEGIN"
    assert begin.data_type == "character"
    assert begin.required is True
    assert begin.is_mappable is True
    assert begin.is_node is True
    assert begin.validate_data is False
    assert begin.use_namespace == "-1"

    installation = result.find_by_name(
        "Z1DVMBG_MRINSTPL"
    )[0]

    assert len(
        installation.attributes
    ) == 1

    assert (
        installation.attributes[0].name
        == "SEGMENT"
    )

    assert (
        installation.attributes[0].required
        is True
    )


def test_analyzer_preserves_type_metadata() -> None:
    result = analyze()

    idoc = result.find_by_name(
        "IDOC"
    )[0]

    assert idoc.type_expanded is True
    assert idoc.type_key == "5"
    assert idoc.type_name == (
        "ZDVMBG_MR_ORDER_AMR."
        "ZDVMBG_MR_REQUEST"
    )

    leaf = result.find_by_name(
        "ISTABLART"
    )[0]

    assert leaf.type_expanded is None
    assert leaf.type_key == "-1"
    assert leaf.type_name is None


def test_analyzer_reports_repeating_elements() -> None:
    result = analyze()

    repeating_names = {
        element.name
        for element in result.repeating_elements
    }

    assert repeating_names == {
        "Z1DVMBG_MRINSTPL",
        "Z1DVMBG_MRINSTDEV",
        "Z1DVMBG_MRINSTREG",
    }


def test_analyzer_rejects_empty_input() -> None:
    with pytest.raises(
        ValueError,
        match="xml_text must not be empty",
    ):
        BoomiXmlProfileAnalyzer().analyze(
            ""
        )


def test_analyzer_rejects_invalid_xml() -> None:
    with pytest.raises(
        BoomiXmlProfileAnalysisError,
        match="not well-formed",
    ):
        BoomiXmlProfileAnalyzer().analyze(
            "<Component>"
        )


def test_analyzer_rejects_non_profile_component() -> None:
    xml = PROFILE_XML.replace(
        'type="profile.xml"',
        'type="process"',
        1,
    )

    with pytest.raises(
        BoomiXmlProfileAnalysisError,
        match=(
            "Component type must be profile.xml"
        ),
    ):
        BoomiXmlProfileAnalyzer().analyze(
            xml
        )


def test_analyzer_rejects_missing_xml_profile() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="profile.xml">
  <object>
    <SomethingElse />
  </object>
</Component>
"""

    with pytest.raises(
        BoomiXmlProfileAnalysisError,
        match="XMLProfile definition is missing",
    ):
        BoomiXmlProfileAnalyzer().analyze(
            xml
        )


def test_analyzer_rejects_missing_data_elements() -> None:
    xml = """\
<Component
    xmlns="http://api.platform.boomi.com/"
    type="profile.xml">
  <object>
    <XMLProfile xmlns="" />
  </object>
</Component>
"""

    with pytest.raises(
        BoomiXmlProfileAnalysisError,
        match="DataElements is missing",
    ):
        BoomiXmlProfileAnalyzer().analyze(
            xml
        )


def test_analyzer_rejects_invalid_cardinality() -> None:
    xml = PROFILE_XML.replace(
        'maxOccurs="999999999"',
        'maxOccurs="many"',
        1,
    )

    with pytest.raises(
        BoomiXmlProfileAnalysisError,
        match=(
            "Attribute 'maxOccurs' "
            "must be an integer"
        ),
    ):
        BoomiXmlProfileAnalyzer().analyze(
            xml
        )


def test_analyzer_rejects_invalid_boolean() -> None:
    xml = PROFILE_XML.replace(
        'strict="true"',
        'strict="maybe"',
        1,
    )

    with pytest.raises(
        BoomiXmlProfileAnalysisError,
        match=(
            "Attribute 'strict' "
            "must be true or false"
        ),
    ):
        BoomiXmlProfileAnalyzer().analyze(
            xml
        )