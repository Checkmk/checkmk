#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, Integer, ListChoice, TextInput, Transform


def _factory_default_special_agents_jenkins():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _transform_jenkins_infos(value):
    if "infos" in value:
        value["sections"] = value.pop("infos")
    return value


def _valuespec_special_agents_jenkins():
    return Transform(
        valuespec=Dictionary(
            title=_("Jenkins jobs and builds"),
            help=_("Requests data from a jenkins instance."),
            optional_keys=["port"],
            elements=[
                (
                    "instance",
                    TextInput(
                        title=_("Jenkins instance to query."),
                        help=_(
                            "Use this option to set which instance should be "
                            "checked by the special agent. Please add the "
                            "hostname here, eg. my_jenkins.com."
                        ),
                        size=32,
                        allow_empty=False,
                    ),
                ),
                (
                    "user",
                    TextInput(
                        title=_("Username"),
                        help=_(
                            "The username that should be used for accessing the "
                            "jenkins API. Has to have read permissions at least."
                        ),
                        size=32,
                        allow_empty=False,
                    ),
                ),
                (
                    "password",
                    PasswordFromStore(
                        help=_("The password or API key of the user."),
                        title=_("Password of the user"),
                        allow_empty=False,
                    ),
                ),
                (
                    "protocol",
                    DropdownChoice(
                        title=_("Protocol"),
                        choices=[
                            ("http", "HTTP"),
                            ("https", "HTTPS"),
                        ],
                        default_value="https",
                    ),
                ),
                (
                    "port",
                    Integer(
                        title=_("Port"),
                        help=_(
                            "Use this option to query a port which is different from standard port 8080."
                        ),
                        default_value=443,
                    ),
                ),
                (
                    "sections",
                    ListChoice(
                        title=_("Informations to query"),
                        help=_(
                            "Defines what information to query. You can choose "
                            "between the instance state, job states, node states "
                            "and the job queue."
                        ),
                        choices=[
                            ("instance", _("Instance state")),
                            ("jobs", _("Job state")),
                            ("nodes", _("Node state")),
                            ("queue", _("Queue info")),
                        ],
                        default_value=["instance", "jobs", "nodes", "queue"],
                        allow_empty=False,
                    ),
                ),
            ],
        ),
        forth=_transform_jenkins_infos,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_jenkins(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:jenkins",
        valuespec=_valuespec_special_agents_jenkins,
    )
)
