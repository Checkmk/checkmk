#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, Dict

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    Float,
    ID,
    Integer,
    ListOf,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.watolib.rulespecs import Rulespec


def _special_agents_siemens_plc_validate_siemens_plc_values(value, varprefix):
    valuetypes: Dict[Any, Any] = {}
    for index, (_db_number, _address, _datatype, valuetype, ident) in enumerate(value):
        valuetypes.setdefault(valuetype, [])
        if ident in valuetypes[valuetype]:
            raise MKUserError(
                "%s_%d_%d" % (varprefix, index + 1, 4),
                _("The ident of a value needs to be unique per valuetype."),
            )
        valuetypes[valuetype].append(ident)


def _special_agents_siemens_plc_siemens_plc_value():
    return [
        Transform(
            valuespec=CascadingDropdown(
                title=_("The Area"),
                choices=[
                    (
                        "db",
                        _("Datenbaustein"),
                        Integer(
                            title="<nobr>%s</nobr>" % _("DB Number"),
                            minvalue=1,
                        ),
                    ),
                    ("input", _("Input")),
                    ("output", _("Output")),
                    ("merker", _("Merker")),
                    ("timer", _("Timer")),
                    ("counter", _("Counter")),
                ],
                orientation="horizontal",
                sorted=True,
            ),
            # Transform old Integer() value spec to new cascading dropdown value
            forth=lambda x: isinstance(x, int) and ("db", x) or x,
        ),
        Float(
            title=_("Address"),
            display_format="%.1f",
            help=_(
                "Addresses are specified with a dot notation, where number "
                "before the dot specify the byte to fetch and the number after the "
                "dot specifies the bit to fetch. The number of the bit is always "
                "between 0 and 7."
            ),
        ),
        CascadingDropdown(
            title=_("Datatype"),
            choices=[
                ("dint", _("Double Integer (DINT)")),
                ("real", _("Real Number (REAL)")),
                ("bit", _("Single Bit (BOOL)")),
                (
                    "str",
                    _("String (STR)"),
                    Integer(
                        minvalue=1,
                        title=_("Size"),
                        unit=_("Bytes"),
                    ),
                ),
                (
                    "raw",
                    _("Raw Bytes (HEXSTR)"),
                    Integer(
                        minvalue=1,
                        title=_("Size"),
                        unit=_("Bytes"),
                    ),
                ),
            ],
            orientation="horizontal",
            sorted=True,
        ),
        DropdownChoice(
            title=_("Type of the value"),
            choices=[
                (None, _("Unclassified")),
                ("temp", _("Temperature")),
                ("hours_operation", _("Hours of operation")),
                ("hours_since_service", _("Hours since service")),
                ("hours", _("Hours")),
                ("seconds_operation", _("Seconds of operation")),
                ("seconds_since_service", _("Seconds since service")),
                ("seconds", _("Seconds")),
                ("counter", _("Increasing counter")),
                ("flag", _("State flag (on/off)")),
                ("text", _("Text")),
            ],
            sorted=True,
        ),
        ID(
            title=_("Ident of the value"),
            help=_(
                " An identifier of your choice. This identifier "
                "is used by the Check_MK checks to access "
                "and identify the single values. The identifier "
                "needs to be unique within a group of VALUETYPES."
            ),
        ),
    ]


def _factory_default_special_agents_siemens_plc():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_siemens_plc():
    return Dictionary(
        elements=[
            (
                "devices",
                ListOf(
                    valuespec=Dictionary(
                        elements=[
                            (
                                "host_name",
                                TextInput(
                                    title=_("Name of the PLC"),
                                    allow_empty=False,
                                    help=_(
                                        "Specify the logical name, e.g. the hostname, of the PLC. This name "
                                        "is used to name the resulting services."
                                    ),
                                ),
                            ),
                            (
                                "host_address",
                                TextInput(
                                    title=_("Network address"),
                                    allow_empty=False,
                                    help=_(
                                        "Specify the hostname or IP address of the PLC to communicate with."
                                    ),
                                ),
                            ),
                            (
                                "rack",
                                Integer(
                                    title=_("Number of the Rack"),
                                    minvalue=0,
                                ),
                            ),
                            (
                                "slot",
                                Integer(
                                    title=_("Number of the Slot"),
                                    minvalue=0,
                                ),
                            ),
                            (
                                "tcp_port",
                                Integer(
                                    title=_("TCP Port number"),
                                    help=_("Port number for communicating with the PLC"),
                                    default_value=102,
                                    minvalue=1,
                                    maxvalue=65535,
                                ),
                            ),
                            (
                                "timeout",
                                Integer(
                                    title=_("Connect Timeout"),
                                    help=_(
                                        "The connect timeout in seconds when establishing a connection "
                                        "with the PLC."
                                    ),
                                    default_value=60,
                                    minvalue=1,
                                    unit=_("seconds"),
                                ),
                            ),
                            (
                                "values",
                                ListOf(
                                    valuespec=Tuple(
                                        elements=_special_agents_siemens_plc_siemens_plc_value(),
                                        orientation="horizontal",
                                    ),
                                    title=_("Values to fetch from this device"),
                                    validate=_special_agents_siemens_plc_validate_siemens_plc_values,
                                    magic="@;@",
                                ),
                            ),
                        ],
                        optional_keys=["timeout"],
                    ),
                    title=_("Devices to fetch information from"),
                ),
            ),
            (
                "values",
                ListOf(
                    valuespec=Tuple(
                        elements=_special_agents_siemens_plc_siemens_plc_value(),
                        orientation="horizontal",
                    ),
                    title=_("Values to fetch from all devices"),
                    validate=_special_agents_siemens_plc_validate_siemens_plc_values,
                ),
            ),
        ],
        optional_keys=["timeout"],
        title=_("Siemens PLC (SPS)"),
        help=_(
            "This rule selects the Siemens PLC agent instead of the normal Check_MK Agent "
            "and allows monitoring of Siemens PLC using the Snap7 API. You can configure "
            "your connection settings and values to fetch here."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_siemens_plc(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:siemens_plc",
        valuespec=_valuespec_special_agents_siemens_plc,
    )
)
