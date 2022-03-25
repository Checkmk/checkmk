#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsCustom
from cmk.gui.plugins.wato.utils import HostRulespec, monitoring_macro_help, rulespec_registry
from cmk.gui.valuespec import TextInput


def _valuespec_datasource_programs():
    return TextInput(
        title=_("Individual program call instead of agent access"),
        help=_(
            "For agent based checks Check_MK allows you to specify an alternative "
            "program that should be called by Check_MK instead of connecting the agent "
            "via TCP. That program must output the agent's data on standard output in "
            "the same format the agent would do. This is for example useful for monitoring "
            "via SSH."
        )
        + monitoring_macro_help()
        + _('This option can only be used with the permission "Can add or modify executables".')
        + _(
            "<br> HINT: The individual program is called from the current working directory. "
            "You should therefore specify absolute path names in scripts (by using environment variables like OMD_SITE) "
            "to make the individual program call run correctly in all execution contexts (UI and console)."
        ),
        label=_("Command line to execute"),
        empty_text=_("Access Checkmk Agent via TCP"),
        size=80,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsCustom,
        name="datasource_programs",
        valuespec=_valuespec_datasource_programs,
    )
)
