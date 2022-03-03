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
    Dictionary,
    DualListChoice,
    ListOfStrings,
    MonitoringState,
    RegExp,
    TextInput,
)

_DEFAULT_DATADOG_AND_CHECKMK_STATES = (
    ("Alert", 2),
    ("Ignored", 3),
    ("No Data", 0),
    ("OK", 0),
    ("Skipped", 3),
    ("Unknown", 3),
    ("Warn", 1),
)


def _valuespec_datadog_monitors_discovery() -> Dictionary:
    return Dictionary(
        [
            (
                "states_discover",
                DualListChoice(
                    title=_("Only discover monitors in the following states"),
                    choices=[
                        (
                            datadog_state,
                            datadog_state,
                        )
                        for datadog_state, _checkmk_state in _DEFAULT_DATADOG_AND_CHECKMK_STATES
                    ],
                    default_value=[
                        datadog_state
                        for datadog_state, _checkmk_state in _DEFAULT_DATADOG_AND_CHECKMK_STATES
                    ],
                    rows=len(_DEFAULT_DATADOG_AND_CHECKMK_STATES) + 2,
                    size=50,
                ),
            ),
        ],
        title=_("Discovery of Datadog monitors"),
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="datadog_monitors_discovery",
        valuespec=_valuespec_datadog_monitors_discovery,
    ),
)


def _item_spec_datadog_monitors():
    return TextInput(
        title=_("Datadog monitor"),
        help=_("The name of the Datadog monitor."),
    )


def _parameter_valuespec_datadog_monitors() -> Dictionary:
    return Dictionary(
        [
            (
                "state_mapping",
                Dictionary(
                    [
                        (
                            datadog_state,
                            MonitoringState(
                                title=datadog_state,
                                default_value=checkmk_state,
                            ),
                        )
                        for datadog_state, checkmk_state in _DEFAULT_DATADOG_AND_CHECKMK_STATES
                    ],
                    title=_("Map monitor states to Checkmk monitoring states"),
                    optional_keys=False,
                ),
            ),
            (
                "tags_to_show",
                ListOfStrings(
                    valuespec=RegExp(
                        mode=RegExp.prefix,
                        size=30,
                        allow_empty=False,
                    ),
                    title=_("Datadog tags shown in service output"),
                    help=_(
                        "This option allows you to configure which Datadog tags will be shown in "
                        "the service output. This is done by entering regular expressions matching "
                        "one or more Datadog tags. Any matching tag will be displayed in the "
                        "service output."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="datadog_monitors_check",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_datadog_monitors,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_datadog_monitors,
        title=lambda: _("Checking of Datadog monitors"),
    )
)
