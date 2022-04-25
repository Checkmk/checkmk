#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import (
    Alternative,
    Checkbox,
    Dictionary,
    Float,
    Integer,
    ListChoice,
    Optional,
    Percentage,
    TextInput,
    Tuple,
)

_brocade_fcport_adm_choices = [
    (1, "online(1)"),
    (2, "offline(2)"),
    (3, "testing(3)"),
    (4, "faulty(4)"),
]

_brocade_fcport_op_choices = [
    (0, "unkown(0)"),
    (1, "online(1)"),
    (2, "offline(2)"),
    (3, "testing(3)"),
    (4, "faulty(4)"),
]

_brocade_fcport_phy_choices = [
    (1, "noCard(1)"),
    (2, "noTransceiver(2)"),
    (3, "laserFault(3)"),
    (4, "noLight(4)"),
    (5, "noSync(5)"),
    (6, "inSync(6)"),
    (7, "portFault(7)"),
    (8, "diagFault(8)"),
    (9, "lockRef(9)"),
    (10, "validating(10)"),
    (11, "invalidModule(11)"),
    (14, "noSigDet(14)"),
    (255, "unkown(255)"),
]


def _valuespec_brocade_fcport_inventory():
    return Dictionary(
        title=_("Brocade port discovery"),
        elements=[
            (
                "use_portname",
                Checkbox(
                    title=_("Use port name as service name"),
                    label=_("use port name"),
                    default_value=True,
                    help=_(
                        "This option lets Check_MK use the port name as item instead of the "
                        "port number. If no description is available then the port number is "
                        "used anyway."
                    ),
                ),
            ),
            (
                "show_isl",
                Checkbox(
                    title=_('add "ISL" to service description for interswitch links'),
                    label=_("add ISL"),
                    default_value=True,
                    help=_(
                        'This option lets Check_MK add the string "ISL" to the service '
                        "description for interswitch links."
                    ),
                ),
            ),
            (
                "admstates",
                ListChoice(
                    title=_("Administrative port states to discover"),
                    help=_(
                        "When doing service discovery on brocade switches only ports with the given administrative "
                        "states will be added to the monitoring system."
                    ),
                    choices=_brocade_fcport_adm_choices,
                    columns=1,
                    toggle_all=True,
                    default_value=["1", "3", "4"],
                ),
            ),
            (
                "phystates",
                ListChoice(
                    title=_("Physical port states to discover"),
                    help=_(
                        "When doing service discovery on brocade switches only ports with the given physical "
                        "states will be added to the monitoring system."
                    ),
                    choices=_brocade_fcport_phy_choices,
                    columns=1,
                    toggle_all=True,
                    default_value=[3, 4, 5, 6, 7, 8, 9, 10],
                ),
            ),
            (
                "opstates",
                ListChoice(
                    title=_("Operational port states to discover"),
                    help=_(
                        "When doing service discovery on brocade switches only ports with the given operational "
                        "states will be added to the monitoring system."
                    ),
                    choices=_brocade_fcport_op_choices,
                    columns=1,
                    toggle_all=True,
                    default_value=[1, 2, 3, 4],
                ),
            ),
        ],
        help=_(
            "This rule can be used to control the service discovery for brocade ports. "
            "You can configure the port states for inventory "
            "and the use of the description as service name."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="brocade_fcport_inventory",
        valuespec=_valuespec_brocade_fcport_inventory,
    )
)


def _item_spec_brocade_fcport():
    return TextInput(
        title=_("port name"),
        help=_("The name of the switch port"),
    )


def _parameter_valuespec_brocade_fcport():
    return Dictionary(
        elements=[
            (
                "bw",
                Alternative(
                    title=_("Throughput levels"),
                    help=_(
                        "Please note: in a few cases the automatic detection of the link speed "
                        "does not work. In these cases you have to set the link speed manually "
                        "below if you want to monitor percentage values"
                    ),
                    elements=[
                        Tuple(
                            title=_("Used bandwidth of port relative to the link speed"),
                            elements=[
                                Percentage(title=_("Warning at"), unit=_("percent")),
                                Percentage(title=_("Critical at"), unit=_("percent")),
                            ],
                        ),
                        Tuple(
                            title=_("Used Bandwidth of port in megabyte/s"),
                            elements=[
                                Integer(title=_("Warning at"), unit=_("MByte/s")),
                                Integer(title=_("Critical at"), unit=_("MByte/s")),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "assumed_speed",
                Float(
                    title=_("Assumed link speed"),
                    help=_(
                        "If the automatic detection of the link speed does "
                        "not work you can set the link speed here."
                    ),
                    unit=_("GByte/s"),
                ),
            ),
            (
                "rxcrcs",
                Tuple(
                    title=_("CRC errors rate"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("percent"), display_format="%.2f"),
                        Percentage(
                            title=_("Critical at"), unit=_("percent"), display_format="%.2f"
                        ),
                    ],
                ),
            ),
            (
                "rxencoutframes",
                Tuple(
                    title=_("Enc-Out frames rate"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("percent")),
                        Percentage(title=_("Critical at"), unit=_("percent")),
                    ],
                ),
            ),
            (
                "rxencinframes",
                Tuple(
                    title=_("Enc-In frames rate"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("percent")),
                        Percentage(title=_("Critical at"), unit=_("percent")),
                    ],
                ),
            ),
            (
                "notxcredits",
                Tuple(
                    title=_("No-TxCredits errors"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("percent")),
                        Percentage(title=_("Critical at"), unit=_("percent")),
                    ],
                ),
            ),
            (
                "c3discards",
                Tuple(
                    title=_("C3 discards"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("percent")),
                        Percentage(title=_("Critical at"), unit=_("percent")),
                    ],
                ),
            ),
            (
                "average",
                Integer(
                    title=_("Averaging"),
                    help=_(
                        "If this parameter is set, all throughputs will be averaged "
                        "over the specified time interval before levels are being applied. Per "
                        "default, averaging is turned off. "
                    ),
                    unit=_("minutes"),
                    minvalue=1,
                    default_value=60,
                ),
            ),
            (
                "phystate",
                Optional(
                    ListChoice(
                        title=_("Allowed states (otherwise check will be critical)"),
                        choices=[
                            (1, _("noCard")),
                            (2, _("noTransceiver")),
                            (3, _("laserFault")),
                            (4, _("noLight")),
                            (5, _("noSync")),
                            (6, _("inSync")),
                            (7, _("portFault")),
                            (8, _("diagFault")),
                            (9, _("lockRef")),
                        ],
                    ),
                    title=_("Physical state of port"),
                    negate=True,
                    label=_("ignore physical state"),
                ),
            ),
            (
                "opstate",
                Optional(
                    ListChoice(
                        title=_("Allowed states (otherwise check will be critical)"),
                        choices=[
                            (0, _("unknown")),
                            (1, _("online")),
                            (2, _("offline")),
                            (3, _("testing")),
                            (4, _("faulty")),
                        ],
                    ),
                    title=_("Operational state"),
                    negate=True,
                    label=_("ignore operational state"),
                ),
            ),
            (
                "admstate",
                Optional(
                    ListChoice(
                        title=_("Allowed states (otherwise check will be critical)"),
                        choices=[
                            (1, _("online")),
                            (2, _("offline")),
                            (3, _("testing")),
                            (4, _("faulty")),
                        ],
                    ),
                    title=_("Administrative state"),
                    negate=True,
                    label=_("ignore administrative state"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="brocade_fcport",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_brocade_fcport,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_brocade_fcport,
        title=lambda: _("Brocade FibreChannel ports"),
    )
)
