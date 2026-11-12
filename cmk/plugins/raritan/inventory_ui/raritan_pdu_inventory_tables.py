# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Display nine Raritan inventory tables below Hardware / Physical components."""

from cmk.inventory_ui.v1_unstable import BoolField, ChoiceField, Node, NumberField, Table, TextField, Title, View
from cmk.gui.utils.html import HTML
from cmk.plugins.raritan.inventory import SENSOR_TYPES, SENSOR_UNITS


def _render_capabilities(value: str) -> HTML:
    """Render one capability per line, escaping every inventory text fragment.

    Checkmk 2.5's GUI preserves its HTML wrapper through TextField rendering.
    Plain newlines collapse in HTML; plain <br> strings would be escaped.
    Keep this GUI-specific formatting out of the stored inventory data.
    """
    return HTML.without_escaping("<br>").join(value.split(", "))


def _capabilities_field(title: Title) -> TextField:
    # The unstable API types render results as text, while the installed GUI
    # also handles its HTML wrapper. Keep this version-specific use local.
    return TextField(title, render=_render_capabilities)  # type: ignore[arg-type]


node_raritan_pdu_inventory_transfer_switch = Node(
    name="raritan_pdu_inventory_transfer_switch",
    path=["hardware", "components", "raritan_pdu_transfer_switches"],
    title=Title("Raritan transfer switches"),
    table=Table(
        view=View(name="invraritanpdutransferswitch", title=Title("Raritan transfer switches")),
        columns={
            "pdu_id": NumberField(Title("PDU ID")),
            "transfer_switch_id": NumberField(Title("Transfer switch ID")),
            "name": TextField(Title("Name")),
            "label": TextField(Title("Label")),
            "preferred_inlet": NumberField(Title("Preferred inlet ID")),
            "pole_count": NumberField(Title("Poles")),
            "sensor_capabilities": _capabilities_field(Title("Sensor capabilities")),
            "power_source_1": TextField(Title("Power source 1")),
            "power_source_2": TextField(Title("Power source 2")),
        },
    ),
)


node_raritan_pdu_inventory_ocprot = Node(
    name="raritan_pdu_inventory_ocprot",
    path=["hardware", "components", "raritan_pdu_overcurrent_protectors"],
    title=Title("Raritan overcurrent protectors"),
    table=Table(
        view=View(name="invraritanpduocprot", title=Title("Raritan overcurrent protectors")),
        columns={
            "pdu_id": NumberField(Title("PDU ID")),
            "protector_id": NumberField(Title("Protector ID")),
            "name": TextField(Title("Name")),
            "label": TextField(Title("Label")),
            "protector_type": ChoiceField(Title("Type"), mapping={
                1: "1-pole circuit breaker", 2: "2-pole circuit breaker", 3: "3-pole circuit breaker",
                4: "Fuse", 5: "Fuse pair", 6: "2-pole RCBO", 7: "3-pole RCBO", 8: "4-pole RCBO",
            }),
            "rated_current": TextField(Title("Rated current")),
            "pole_count": NumberField(Title("Poles")),
            "sensor_capabilities": _capabilities_field(Title("Sensor capabilities")),
            "power_source": TextField(Title("Power source")),
        },
    ),
)


node_raritan_pdu_inventory_nameplate = Node(
    name="raritan_pdu_inventory_nameplate",
    path=["hardware", "components", "raritan_pdu_nameplates"],
    title=Title("Raritan PDU nameplates"),
    table=Table(
        view=View(name="invraritanpdunameplate", title=Title("Raritan PDU nameplates")),
        columns={
            "pdu_id": NumberField(Title("PDU ID")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model")),
            "serial_number": TextField(Title("Serial number")),
            "rated_voltage": TextField(Title("Rated voltage")),
            "rated_current": TextField(Title("Rated current")),
            "rated_frequency": TextField(Title("Rated frequency")),
            "rated_va": TextField(Title("Rated apparent power")),
            "wiring_diagram_url": TextField(Title("Wiring diagram URL")),
        },
    ),
)

node_raritan_pdu_inventory_unit = Node(
    name="raritan_pdu_inventory_unit",
    path=["hardware", "components", "raritan_pdu_units"],
    title=Title("Raritan PDU hardware"),
    table=Table(
        view=View(name="invraritanpduunit", title=Title("Raritan PDU hardware")),
        columns={
            "pdu_id": NumberField(Title("PDU ID")),
            "name": TextField(Title("Name")),
            "inlet_count": NumberField(Title("Inlets")),
            "overcurrent_protector_count": NumberField(Title("Overcurrent protectors")),
            "outlet_count": NumberField(Title("Outlets")),
            "inlet_controller_count": NumberField(Title("Inlet controllers")),
            "outlet_controller_count": NumberField(Title("Outlet controllers")),
            "external_sensor_capacity": NumberField(Title("External sensor capacity")),
            "managed_external_sensor_count": NumberField(Title("Managed external sensors")),
            "transfer_switch_count": NumberField(Title("Transfer switches")),
            "metering_controller_count": NumberField(Title("Metering controllers")),
            "circuit_count": NumberField(Title("Branch circuits")),
            "peripheral_device_package_count": NumberField(Title("Peripheral device packages")),
            "product_type": ChoiceField(Title("Product type"), mapping={0: "Rack PDU", 1: "Branch circuit monitor", 2: "Transfer switch", 3: "Power meter"}),
            "sensor_capabilities": _capabilities_field(Title("Unit sensor capabilities")),
            "has_dc_inlets": BoolField(Title("Has DC inlets")),
            "cascade_role": ChoiceField(Title("Cascade role"), mapping={0: "Standalone", 1: "Primary unit", 2: "Expansion unit"}),
            "cascade_type": ChoiceField(Title("Cascade type"), mapping={0: "Bridging", 1: "Port forwarding", 2: "None"}),
            "cascade_position": NumberField(Title("Cascade position")),
            "orientation": ChoiceField(Title("Orientation"), mapping={0: "None / not supported", 1: "Bottom feed", 2: "Top feed"}),
        },
    ),
)

node_raritan_pdu_inventory_inlet_summary = Node(
    name="raritan_pdu_inventory_inlet_summary",
    path=["hardware", "components", "raritan_pdu_inlets"],
    title=Title("Raritan inlet summaries"),
    table=Table(
        view=View(name="invraritanpduinletsummary", title=Title("Raritan inlet summaries")),
        columns={
            "pdu_id": NumberField(Title("PDU ID")),
            "inlet_id": NumberField(Title("Inlet ID")),
            "name": TextField(Title("Name")),
            "label": TextField(Title("Label")),
            "pole_count": NumberField(Title("Poles")),
            "rated_voltage": TextField(Title("Rated voltage")),
            "rated_current": TextField(Title("Rated current")),
            "plug": TextField(Title("Plug type")),
            "sensor_capabilities": _capabilities_field(Title("Summary sensor capabilities")),
            "is_dc": BoolField(Title("DC inlet")),
            "line_pair_count": NumberField(Title("Line pairs")),
        },
    ),
)

node_raritan_pdu_inventory_outlet_summary = Node(
    name="raritan_pdu_inventory_outlet_summary",
    path=["hardware", "components", "raritan_pdu_outlets"],
    title=Title("Raritan outlet summaries"),
    table=Table(
        view=View(name="invraritanpduoutletsummary", title=Title("Raritan outlet summaries")),
        columns={
            "pdu_id": NumberField(Title("PDU ID")),
            "outlet_id": NumberField(Title("Outlet ID")),
            "name": TextField(Title("Name")),
            "label": TextField(Title("Label")),
            "pole_count": NumberField(Title("Poles")),
            "rated_voltage": TextField(Title("Rated voltage")),
            "rated_current": TextField(Title("Rated current")),
            "rated_va": TextField(Title("Rated apparent power")),
            "receptacle": TextField(Title("Receptacle type")),
            "switchable": BoolField(Title("Switchable")),
            "sensor_capabilities": _capabilities_field(Title("Summary sensor capabilities")),
            "power_source": TextField(Title("Power source")),
        },
    ),
)

node_raritan_pdu_inventory_sensors = Node(
    name="raritan_pdu_inventory_sensors",
    path=["hardware", "components", "raritan_pdu_external_sensors"],
    title=Title("Raritan external sensors"),
    table=Table(
        view=View(name="invraritanpdusensors", title=Title("Raritan external sensors")),
        columns={
            "pdu_id": NumberField(Title("PDU ID")),
            "sensor_id": NumberField(Title("Sensor ID")),
            "name": TextField(Title("Name")),
            "sensor_type": ChoiceField(Title("Sensor type"), mapping=SENSOR_TYPES),
            "serial_number": TextField(Title("Serial number")),
            "description": TextField(Title("Description")),
            "x_coordinate": TextField(Title("X coordinate")),
            "y_coordinate": TextField(Title("Y coordinate")),
            "z_coordinate": TextField(Title("Z coordinate")),
            "channel": NumberField(Title("Contact channel")),
            "binary_subtype": ChoiceField(Title("Binary subtype"), mapping=SENSOR_TYPES),
            "unit": ChoiceField(Title("Measurement unit"), mapping=SENSOR_UNITS),
            "decimal_digits": NumberField(Title("Decimal digits")),
            "is_actuator": BoolField(Title("Actuator")),
            "position": TextField(Title("Bus position")),
        },
    ),
)

node_raritan_pdu_inventory_inlet = Node(
    name="raritan_pdu_inventory_inlet",
    path=["hardware", "components", "raritan_pdu_inlet_poles"],
    title=Title("Raritan inlet poles"),
    table=Table(
        view=View(name="invraritanpduinletpoles", title=Title("Raritan inlet poles")),
        columns={
            "pdu_id": NumberField(Title("PDU ID")),
            "inlet_id": NumberField(Title("Inlet ID")),
            "pole_index": NumberField(Title("Pole index")),
            "name": TextField(Title("Name")),
            "label": TextField(Title("Label")),
            "line": ChoiceField(Title("Conductor"), mapping={1: "L1", 2: "L2", 3: "L3", 4: "N", 5: "DC+", 6: "DC-"}),
            "node": NumberField(Title("Topology node")),
            "sensor_capabilities": _capabilities_field(Title("Pole sensor capabilities")),
        },
    ),
)

node_raritan_pdu_inventory_outlet = Node(
    name="raritan_pdu_inventory_outlet",
    path=["hardware", "components", "raritan_pdu_outlet_poles"],
    title=Title("Raritan outlet poles"),
    table=Table(
        view=View(name="invraritanpduoutletpoles", title=Title("Raritan outlet poles")),
        columns={
            "pdu_id": NumberField(Title("PDU ID")),
            "outlet_id": NumberField(Title("Outlet ID")),
            "pole_index": NumberField(Title("Pole index")),
            "name": TextField(Title("Name")),
            "label": TextField(Title("Label")),
            "line": ChoiceField(Title("Conductor"), mapping={1: "L1", 2: "L2", 3: "L3", 4: "N", 5: "DC+", 6: "DC-"}),
            "node": NumberField(Title("Topology node")),
            "sensor_capabilities": _capabilities_field(Title("Pole sensor capabilities")),
        },
    ),
)
