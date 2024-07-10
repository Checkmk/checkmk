#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, Integer, NetworkPort, TextInput
from cmk.gui.wato import MigrateToIndividualOrStoredPassword, RulespecGroupDatasourceProgramsApps
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_special_agents_appdynamics():
    return Dictionary(
        title=_("AppDynamics via REST API"),
        help=_(
            "This rule allows querying an AppDynamics server for information about Java applications"
            "via the AppDynamics REST API. You can configure your connection settings here."
        ),
        elements=[
            (
                "username",
                TextInput(
                    title=_("AppDynamics login user name"),
                    allow_empty=False,
                ),
            ),
            (
                "password",
                MigrateToIndividualOrStoredPassword(
                    title=_("AppDynamics login password"),
                    allow_empty=False,
                ),
            ),
            (
                "application",
                TextInput(
                    title=_("AppDynamics application name"),
                    help=_(
                        "This is the application name used in the URL. If you enter for example the application "
                        "name <tt>foobar</tt>, this would result in the URL being used to contact the REST API: "
                        "<tt>/controller/rest/applications/foobar/metric-data</tt>"
                    ),
                    allow_empty=False,
                    size=40,
                ),
            ),
            (
                "port",
                NetworkPort(
                    title=_("TCP port number"),
                    help=_("Port number that AppDynamics is listening on. The default is 8090."),
                    default_value=8090,
                    minvalue=1,
                    maxvalue=65535,
                ),
            ),
            (
                "timeout",
                Integer(
                    title=_("Connection timeout"),
                    help=_(
                        "The network timeout in seconds when communicating with AppDynamics."
                        "The default is 30 seconds."
                    ),
                    default_value=30,
                    minvalue=1,
                    unit=_("seconds"),
                ),
            ),
        ],
        optional_keys=["port", "timeout"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name=RuleGroup.SpecialAgents("appdynamics"),
        valuespec=_valuespec_special_agents_appdynamics,
    )
)
