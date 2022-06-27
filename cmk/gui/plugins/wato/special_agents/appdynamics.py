#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import Dictionary, Integer, TextInput
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_appdynamics():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


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
                    title=_("AppDynamics login username"),
                    allow_empty=False,
                ),
            ),
            (
                "password",
                IndividualOrStoredPassword(
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
                Integer(
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
        factory_default=_factory_default_special_agents_appdynamics(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:appdynamics",
        valuespec=_valuespec_special_agents_appdynamics,
    )
)
