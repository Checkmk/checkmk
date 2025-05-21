#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.plugin_registry import Registry
from cmk.utils.rulesets.definition import RuleGroup

import cmk.gui.watolib.rulespecs as _rulespecs
from cmk.gui.i18n import _
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupMonitoringConfigurationNotifications,
)
from cmk.gui.watolib.users import notification_script_title

from cmk.rulesets.v1.rule_specs import NotificationParameters

from ._base import NotificationParameter


class NotificationParameterRegistry(Registry[type[NotificationParameter] | NotificationParameters]):
    def plugin_name(self, instance: type[NotificationParameter] | NotificationParameters) -> str:
        return instance.name if isinstance(instance, NotificationParameters) else instance().ident

    # TODO: Make this registration_hook actually take an instance. Atm it takes a class and
    #       instantiates it
    def registration_hook(
        self, instance: type[NotificationParameter] | NotificationParameters
    ) -> None:
        if isinstance(instance, NotificationParameters):
            # Ruleset API v1
            # _rulespecs registration occurs in cmk.gui.rulespec.register_plugins
            return

        plugin = instance()

        script_title = notification_script_title(plugin.ident)

        valuespec = plugin.spec
        # TODO: Cleanup this hack
        valuespec._title = _("Call with the following parameters:")

        _rulespecs.register_rule(
            RulespecGroupMonitoringConfigurationNotifications,
            RuleGroup.NotificationParameters(plugin.ident),
            valuespec,
            _("Parameters for %s") % script_title,
            itemtype=None,
            match="dict",
        )


notification_parameter_registry = NotificationParameterRegistry()


# TODO: Kept for pre 1.6 plug-in compatibility
def register_notification_parameters(scriptname, valuespec):
    parameter_class = type(
        "NotificationParameter%s" % scriptname.title(),
        (NotificationParameter,),
        {
            "ident": scriptname,
            "spec": valuespec,
        },
    )
    notification_parameter_registry.register(parameter_class)
