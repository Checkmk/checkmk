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
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import (
    Alternative,
    Checkbox,
    Dictionary,
    Integer,
    Percentage,
    TextInput,
    Tuple,
)


def _valuespec_inventory_multipath_rules():
    return Dictionary(
        title=_("Linux Multipath Inventory"),
        elements=[
            (
                "use_alias",
                Checkbox(
                    title=_("Use the multipath alias as service name, if one is set"),
                    label=_("use alias"),
                    help=_(
                        "If a multipath device has an alias then you can use it for specifying "
                        "the device instead of the UUID. The alias will then be part of the service "
                        "description. The UUID will be displayed in the plugin output."
                    ),
                ),
            ),
        ],
        help=_(
            "This rule controls whether the UUID or the alias is used in the service description during "
            "discovery of Multipath devices on Linux."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        name="inventory_multipath_rules",
        valuespec=_valuespec_inventory_multipath_rules,
    )
)


def _item_spec_multipath():
    return TextInput(
        title=_("Name of the MP LUN"),
        help=_(
            "For Linux multipathing this is either the UUID (e.g. "
            "60a9800043346937686f456f59386741), or the configured "
            "alias."
        ),
    )


def _parameter_valuespec_multipath():
    return Alternative(
        help=_(
            "This rules sets the expected number of active paths for a multipath LUN "
            "on Linux and Solaris hosts"
        ),
        title=_("Expected number of active paths"),
        elements=[
            Integer(title=_("Expected number of active paths")),
            Tuple(
                title=_("Expected percentage of active paths"),
                elements=[
                    Percentage(title=_("Warning if less then")),
                    Percentage(title=_("Critical if less then")),
                ],
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="multipath",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_multipath,
        parameter_valuespec=_parameter_valuespec_multipath,
        title=lambda: _("Linux and Solaris Multipath Count"),
    )
)
