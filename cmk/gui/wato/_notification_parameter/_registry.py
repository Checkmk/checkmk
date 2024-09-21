#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.version import edition

from cmk.utils.paths import omd_root
from cmk.utils.rulesets.definition import RuleGroup

import cmk.gui.rulespec as _rulespec
import cmk.gui.watolib.rulespecs as _rulespecs
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationNotifications
from cmk.gui.watolib.users import notification_script_title

from cmk.rulesets.v1 import rule_specs, Title

from ._base import NotificationParameter


class NotificationParameterRegistry(Registry[type[NotificationParameter]]):
    def plugin_name(self, instance):
        return instance().ident

    # TODO: Make this registration_hook actually take an instance. Atm it takes a class and
    #       instantiates it
    def registration_hook(self, instance):
        plugin = instance()

        # TODO Add FormSpec converted plugins here, remove else if all are converted
        if plugin.ident in ["mail"]:
            loaded_rulespec = rule_specs.NotificationParameters(
                title=Title("%s") % notification_script_title(plugin.ident),
                name=plugin.ident,
                topic=rule_specs.Topic.NOTIFICATIONS,
                parameter_form=plugin._form_spec,
            )
            _rulespec.register_plugins(
                [LoadedRuleSpec(rule_spec=loaded_rulespec, edition_only=edition(omd_root))]
            )
        else:
            _rulespecs.rulespec_registry.register(
                _rulespecs.HostRulespec(
                    name=RuleGroup.NotificationParameters(plugin.ident),
                    title=lambda: notification_script_title(plugin.ident),
                    group=RulespecGroupMonitoringConfigurationNotifications,
                    valuespec=lambda: plugin.spec,
                    match_type="dict",
                )
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
