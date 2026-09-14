from __future__ import annotations

from pathlib import Path

from boomi_builder.adapters.boomi_engine import (
    BoomiComponentDefinitionResult,
)
from boomi_builder.services.boomi_discovery_service import (
    BoomiDiscoveryService,
)


PROCESS_ID = (
    "1548d6fa-15b7-41e0-84ca-45dd46668bed"
)

MAP_ID = (
    "d857667b-4fba-41e2-a41c-6cea75010029"
)

CONNECTION_ID = (
    "fba410c2-58ee-43c6-a0e0-ef37a6847afd"
)

OPERATION_ID = (
    "79a1c043-9af1-4615-b063-61fa690520a9"
)

PROFILE_ID = (
    "798a16a7-de85-4dd1-bee7-5b80fd84a734"
)


def component_xml(
    *,
    component_id: str,
    name: str,
    component_type: str,
    version: int,
    definition: str,
) -> str:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Component
    xmlns="http://api.platform.boomi.com/"
    componentId="{component_id}"
    name="{name}"
    type="{component_type}"
    version="{version}">
  <object>
    {definition}
  </object>
</Component>
"""


PROCESS_XML = component_xml(
    component_id=PROCESS_ID,
    name="SP S1 - Process MR Order to ZTE",
    component_type="process",
    version=7,
    definition=f"""\
<process>
  <shapes>
    <shape name="shape1" shapetype="start" />
    <shape name="shape2" shapetype="map">
      <map mapId="{MAP_ID}" />
    </shape>
    <shape name="shape3" shapetype="returndocuments" />
    <shape name="shape4" shapetype="connectoraction">
      <connectoraction
          actionType="EXECUTE"
          connectionId="{CONNECTION_ID}"
          operationId="{OPERATION_ID}" />
    </shape>
  </shapes>
</process>""",
)


MAP_XML = component_xml(
    component_id=MAP_ID,
    name="MAP S1 - SAP MR Request to ZTE MR Order",
    component_type="transform.map",
    version=7,
    definition=f"""\
<Map
    fromProfile="{PROFILE_ID}"
    toProfile="{PROFILE_ID}">
  <Mappings />
</Map>""",
)


CONNECTION_XML = component_xml(
    component_id=CONNECTION_ID,
    name="ZTE - SOAP Connection",
    component_type="connector-settings",
    version=2,
    definition="""\
<GenericConnectionConfig>
  <field id="url" type="string" value="" />
</GenericConnectionConfig>""",
)


OPERATION_XML = component_xml(
    component_id=OPERATION_ID,
    name="OPR S1 - ZTE MR Order - SOAP Operation",
    component_type="connector-action",
    version=2,
    definition="""\
<Operation>
  <GenericOperationConfig operationType="EXECUTE" />
</Operation>""",
)


PROFILE_XML = component_xml(
    component_id=PROFILE_ID,
    name="PRF S1 - SAP MR Request - ZDVMBG_MR_REQUEST",
    component_type="profile.xml",
    version=7,
    definition="""\
<XMLProfile>
  <DataElements>
    <XMLElement
        name="ZDVMBG_MR_REQUEST"
        minOccurs="1"
        maxOccurs="1" />
  </DataElements>
</XMLProfile>""",
)


class FakeEngine:
    def __init__(self) -> None:
        self.calls: list[str] = []

        self.definitions = {
            PROCESS_ID: BoomiComponentDefinitionResult(
                component_id=PROCESS_ID,
                name="SP S1 - Process MR Order to ZTE",
                type="process",
                version=7,
                xml=PROCESS_XML,
            ),
            MAP_ID: BoomiComponentDefinitionResult(
                component_id=MAP_ID,
                name="MAP S1 - SAP MR Request to ZTE MR Order",
                type="transform.map",
                version=7,
                xml=MAP_XML,
            ),
            CONNECTION_ID: BoomiComponentDefinitionResult(
                component_id=CONNECTION_ID,
                name="ZTE - SOAP Connection",
                type="connector-settings",
                version=2,
                xml=CONNECTION_XML,
            ),
            OPERATION_ID: BoomiComponentDefinitionResult(
                component_id=OPERATION_ID,
                name="OPR S1 - ZTE MR Order - SOAP Operation",
                type="connector-action",
                version=2,
                xml=OPERATION_XML,
            ),
            PROFILE_ID: BoomiComponentDefinitionResult(
                component_id=PROFILE_ID,
                name=(
                    "PRF S1 - SAP MR Request - "
                    "ZDVMBG_MR_REQUEST"
                ),
                type="profile.xml",
                version=7,
                xml=PROFILE_XML,
            ),
        }

    def get_component_definition(
        self,
        *,
        workspace,
        component_id,
        environment,
    ):
        self.calls.append(
            component_id
        )

        return self.definitions[
            component_id
        ]


def test_discovery_builds_scenario1_graph_and_deduplicates_profile(
    tmp_path: Path,
) -> None:
    engine = FakeEngine()

    service = BoomiDiscoveryService(
        engine
    )

    discovery_root = (
        tmp_path
        / "discovery"
    )

    result = service.discover(
        workspace=tmp_path,
        discovery_root=discovery_root,
        root_component_id=PROCESS_ID,
        environment={
            "BOOMI_ACCOUNT_ID": "TEST",
            "BOOMI_USERNAME": "test@example.invalid",
            "BOOMI_API_TOKEN": "SYNTHETIC",
        },
    )

    assert result.root_component_id == PROCESS_ID

    assert len(result.components) == 5
    assert len(result.edges) == 5

    component_ids = {
        component.component_id
        for component in result.components
    }

    assert component_ids == {
        PROCESS_ID,
        MAP_ID,
        CONNECTION_ID,
        OPERATION_ID,
        PROFILE_ID,
    }

    edge_keys = {
        (
            edge.source_component_id,
            edge.target_component_id,
            edge.relation,
        )
        for edge in result.edges
    }

    assert edge_keys == {
        (
            PROCESS_ID,
            MAP_ID,
            "process-map",
        ),
        (
            PROCESS_ID,
            CONNECTION_ID,
            "process-connection",
        ),
        (
            PROCESS_ID,
            OPERATION_ID,
            "process-operation",
        ),
        (
            MAP_ID,
            PROFILE_ID,
            "map-source-profile",
        ),
        (
            MAP_ID,
            PROFILE_ID,
            "map-target-profile",
        ),
    }

    assert engine.calls.count(
        PROFILE_ID
    ) == 1

    assert len(engine.calls) == 5

    assert result.unsupported_components == ()

    for component_id in component_ids:
        path = (
            discovery_root
            / component_id
            / "component.xml"
        )

        assert path.is_file()


def test_discovery_keeps_process_call_edge(
    tmp_path: Path,
) -> None:
    child_process_id = (
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )

    root_xml = component_xml(
        component_id=PROCESS_ID,
        name="Root Process",
        component_type="process",
        version=1,
        definition=f"""\
<process>
  <shapes>
    <shape shapetype="processcall">
      <processcall
          processId="{child_process_id}" />
    </shape>
  </shapes>
</process>""",
    )

    child_xml = component_xml(
        component_id=child_process_id,
        name="Child Process",
        component_type="process",
        version=1,
        definition="""\
<process>
  <shapes />
</process>""",
    )

    class ProcessCallEngine:
        def __init__(self) -> None:
            self.calls = []

        def get_component_definition(
            self,
            *,
            workspace,
            component_id,
            environment,
        ):
            self.calls.append(
                component_id
            )

            if component_id == PROCESS_ID:
                return BoomiComponentDefinitionResult(
                    component_id=PROCESS_ID,
                    name="Root Process",
                    type="process",
                    version=1,
                    xml=root_xml,
                )

            return BoomiComponentDefinitionResult(
                component_id=child_process_id,
                name="Child Process",
                type="process",
                version=1,
                xml=child_xml,
            )

    engine = ProcessCallEngine()

    result = BoomiDiscoveryService(
        engine
    ).discover(
        workspace=tmp_path,
        discovery_root=tmp_path / "discovery",
        root_component_id=PROCESS_ID,
        environment={},
    )

    assert len(result.components) == 2

    assert result.edges == (
        result.edges[0],
    )

    edge = result.edges[0]

    assert edge.source_component_id == PROCESS_ID
    assert edge.target_component_id == child_process_id
    assert edge.relation == "process-call"


def test_discovery_marks_unknown_type_unsupported_and_stops_recursion(
    tmp_path: Path,
) -> None:
    unknown_id = (
        "11111111-2222-3333-4444-555555555555"
    )

    root_xml = component_xml(
        component_id=PROCESS_ID,
        name="Root Process",
        component_type="process",
        version=1,
        definition=f"""\
<process>
  <shapes>
    <shape shapetype="map">
      <map mapId="{unknown_id}" />
    </shape>
  </shapes>
</process>""",
    )

    unknown_xml = component_xml(
        component_id=unknown_id,
        name="Unknown Component",
        component_type="some.future.type",
        version=1,
        definition="""\
<FutureDefinition
    childComponentId="99999999-8888-7777-6666-555555555555" />""",
    )

    class UnknownEngine:
        def __init__(self) -> None:
            self.calls = []

        def get_component_definition(
            self,
            *,
            workspace,
            component_id,
            environment,
        ):
            self.calls.append(
                component_id
            )

            if component_id == PROCESS_ID:
                return BoomiComponentDefinitionResult(
                    component_id=PROCESS_ID,
                    name="Root Process",
                    type="process",
                    version=1,
                    xml=root_xml,
                )

            return BoomiComponentDefinitionResult(
                component_id=unknown_id,
                name="Unknown Component",
                type="some.future.type",
                version=1,
                xml=unknown_xml,
            )

    engine = UnknownEngine()

    result = BoomiDiscoveryService(
        engine
    ).discover(
        workspace=tmp_path,
        discovery_root=tmp_path / "discovery",
        root_component_id=PROCESS_ID,
        environment={},
    )

    assert len(result.components) == 2
    assert len(result.unsupported_components) == 1

    unsupported = (
        result.unsupported_components[0]
    )

    assert unsupported.component_id == unknown_id
    assert unsupported.type == "some.future.type"
    assert unsupported.supported is False

    assert len(engine.calls) == 2