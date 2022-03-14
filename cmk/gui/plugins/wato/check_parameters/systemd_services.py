#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence

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
    ListChoice,
    ListOf,
    MonitoringState,
    TextInput,
    TextOrRegExp,
    Transform,
)


def _discovery_forth(discovery_params: Mapping[str, Sequence[str]]) -> Mapping[str, Sequence[str]]:
    """
    >>> _discovery_forth({})
    {}
    >>> _discovery_forth({'descriptions': ['a', '~[bc]'], 'names': ['xy'], 'states': ['inactive']})
    {'descriptions': ['a', '~[bc]'], 'names': ['xy'], 'states': ['inactive']}
    >>> _discovery_forth({'states': ['active', 'active', 'inactive']})
    {'states': ['active', 'inactive']}
    """
    transformed_params = {**discovery_params}
    if "states" in transformed_params:
        # sorted() for testability
        transformed_params["states"] = sorted(set(transformed_params["states"]))
    return transformed_params


def _valuespec_discovery_systemd_units_services_rules() -> Transform:
    return Transform(
        valuespec=Dictionary(
            title=_("Systemd single services discovery"),
            elements=[
                (
                    "descriptions",
                    ListOf(
                        valuespec=TextOrRegExp(),
                        title=_("Restrict by description"),
                        help=_("Restrict the systemd services by description."),
                        allow_empty=False,
                    ),
                ),
                (
                    "names",
                    ListOf(
                        valuespec=TextOrRegExp(),
                        title=_("Restrict by service unit name"),
                        help=_("Restrict the systemd services by unit name."),
                        allow_empty=False,
                    ),
                ),
                (
                    "states",
                    ListChoice(
                        choices=[
                            ("active", "active"),
                            ("inactive", "inactive"),
                            ("failed", "failed"),
                        ],
                        title=_("Restrict by state"),
                        allow_empty=False,
                    ),
                ),
            ],
            help=_(
                "Configure the discovery of single systemd services. To be discovered, a service "
                "must match at least one description condition, one name condition and one state "
                "condition, if configured. To simply discover all systemd services, do not "
                "configure any restrictions. Note that independently of this ruleset, some systemd "
                "service units which are used by the Checkmk agent ('check-mk-agent@...') will "
                "never be discovered because they appear and disappear frequently."
            ),
            empty_text=_("No restrictions (discover all systemd service units)"),
        ),
        forth=_discovery_forth,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="discovery_systemd_units_services_rules",
        valuespec=_valuespec_discovery_systemd_units_services_rules,
    )
)


def _parameter_valuespec_systemd_services():
    return Dictionary(
        elements=[
            (
                "states",
                Dictionary(
                    title=_("Map systemd states to monitoring states"),
                    elements=[
                        (
                            "active",
                            MonitoringState(
                                title=_("Monitoring state if service is active"),
                                default_value=0,
                            ),
                        ),
                        (
                            "inactive",
                            MonitoringState(
                                title=_("Monitoring state if service is inactive"),
                                default_value=0,
                            ),
                        ),
                        (
                            "failed",
                            MonitoringState(
                                title=_("Monitoring state if service is failed"),
                                default_value=2,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "states_default",
                MonitoringState(
                    title=_("Monitoring state for any other service state"),
                    default_value=2,
                ),
            ),
            (
                "else",
                MonitoringState(
                    title=_("Monitoring state if a monitored service is not found at all."),
                    default_value=2,
                ),
            ),
        ],
        help=_(
            "This ruleset only applies when individual Systemd services are discovered. The user "
            "needs to configure this option in the discovery section."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="systemd_services",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of the service")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_services,
        title=lambda: _("Systemd single services"),
    )
)
