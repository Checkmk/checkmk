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
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import (
    Alternative,
    Checkbox,
    Dictionary,
    Integer,
    Percentage,
    TextInput,
    Transform,
    Tuple,
)


def _valuespec_discovery_win_dhcp_pools():
    return Dictionary(
        title=_("Windows DHCP pool discovery"),
        elements=[
            (
                "empty_pools",
                Checkbox(
                    title=_("Discovery of empty DHCP pools"),
                    label=_("Include empty pools into the monitoring"),
                    help=_(
                        "You can activate the creation of services for "
                        "DHCP pools, which contain no IP addresses."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_win_dhcp_pools",
        valuespec=_valuespec_discovery_win_dhcp_pools,
    )
)


def _item_spec_win_dhcp_pools():
    return TextInput(
        title=_("Pool name"),
        allow_empty=False,
    )


def _parameter_valuespec_win_dhcp_pools():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "free_leases",
                    Alternative(
                        title=_("Free leases levels"),
                        elements=[
                            Tuple(
                                title=_("Free leases levels in percent"),
                                elements=[
                                    Percentage(title=_("Warning if below"), default_value=10.0),
                                    Percentage(title=_("Critical if below"), default_value=5.0),
                                ],
                            ),
                            Tuple(
                                title=_("Absolute free leases levels"),
                                elements=[
                                    Integer(title=_("Warning if below"), unit=_("free leases")),
                                    Integer(title=_("Critical if below"), unit=_("free leases")),
                                ],
                            ),
                        ],
                    ),
                ),
                (
                    "used_leases",
                    Alternative(
                        title=_("Used leases levels"),
                        elements=[
                            Tuple(
                                title=_("Used leases levels in percent"),
                                elements=[
                                    Percentage(title=_("Warning if below")),
                                    Percentage(title=_("Critical if below")),
                                ],
                            ),
                            Tuple(
                                title=_("Absolute used leases levels"),
                                elements=[
                                    Integer(title=_("Warning if below"), unit=_("used leases")),
                                    Integer(title=_("Critical if below"), unit=_("used leases")),
                                ],
                            ),
                        ],
                    ),
                ),
            ]
        ),
        forth=lambda params: isinstance(params, tuple)
        and {
            "free_leases": (
                float(
                    params[0],
                ),
                float(
                    params[1],
                ),
            )
        }
        or params,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="win_dhcp_pools",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_win_dhcp_pools,
        parameter_valuespec=_parameter_valuespec_win_dhcp_pools,
        title=lambda: _("DHCP Pools for Windows and Linux"),
    )
)
