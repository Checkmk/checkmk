#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.utils import vs_interface_traffic
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Integer,
    ListOf,
    OptionalDropdownChoice,
    TextInput,
)


def _parameter_valuespec_fcp():
    return Dictionary(
        ignored_keys=["inv_speed", "inv_state"],
        elements=[
            (
                "speed",
                OptionalDropdownChoice(
                    title=_("Operating speed"),
                    help=_(
                        "If you use this parameter then the check goes warning if the "
                        "interface is not operating at the expected speed (e.g. it "
                        "is working with 8Gbit/s instead of 16Gbit/s)."
                    ),
                    choices=[
                        (None, _("ignore speed")),
                        (4000000000, "4 Gbit/s"),
                        (8000000000, "8 Gbit/s"),
                        (16000000000, "16 Gbit/s"),
                    ],
                    otherlabel=_("specify manually ->"),
                    explicit=Integer(
                        title=_("Other speed in bits per second"), label=_("Bits per second")
                    ),
                ),
            ),
            (
                "traffic",
                ListOf(
                    valuespec=CascadingDropdown(
                        title=_("Direction"),
                        orientation="horizontal",
                        choices=[
                            ("both", _("In / Out"), vs_interface_traffic()),
                            ("in", _("In"), vs_interface_traffic()),
                            ("out", _("Out"), vs_interface_traffic()),
                        ],
                    ),
                    title=_("Used bandwidth (minimum or maximum traffic)"),
                    help=_(
                        "Setting levels on the used bandwidth is optional. If you do set "
                        "levels you might also consider using averaging."
                    ),
                ),
            ),
            (
                "read_latency",
                Levels(
                    title=_("Read latency"),
                    unit=_("ms"),
                    default_value=None,
                    default_levels=(50.0, 100.0),
                ),
            ),
            (
                "write_latency",
                Levels(
                    title=_("Write latency"),
                    unit=_("ms"),
                    default_value=None,
                    default_levels=(50.0, 100.0),
                ),
            ),
            (
                "latency",
                Levels(
                    title=_("Overall latency"),
                    unit=_("ms"),
                    default_value=None,
                    default_levels=(50.0, 100.0),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fcp",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Port"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fcp,
        title=lambda: _("Fibrechannel Interfaces"),
    )
)
