#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from cmk.ccc.i18n import _
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.version import edition

from cmk.utils.paths import omd_root
from cmk.utils.rulesets.definition import RuleGroup

import cmk.gui.rulespec as _rulespec
import cmk.gui.watolib.rulespecs as _rulespecs
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.private import Catalog, CommentTextArea, not_empty, Topic
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationNotifications
from cmk.gui.watolib.users import notification_script_title

from cmk.rulesets.v1 import Help, rule_specs, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FieldSize, String

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

    def form_spec(self, method: str) -> Catalog:
        try:
            param_form_spec = self._entries[method]()._form_spec()
        except KeyError:
            raise MKUserError(None, _("No notification parameters for method '%s' found") % method)
        except NotImplementedError:
            raise MKUserError(
                None,
                _("No FormSpec implementation for method '%s' found.") % method,
            )

        return Catalog(
            topics=[
                Topic(
                    ident="general",
                    dictionary=Dictionary(
                        title=Title("Parameter properties"),
                        elements={
                            "description": DictElement(
                                parameter_form=String(
                                    title=Title("Description"),
                                    field_size=FieldSize.LARGE,
                                    custom_validate=[not_empty()],
                                ),
                                required=True,
                            ),
                            "comment": DictElement(
                                parameter_form=CommentTextArea(
                                    title=Title("Comment"),
                                )
                            ),
                            "docu_url": DictElement(
                                parameter_form=String(
                                    title=Title("Documentation URL"),
                                    help_text=Help(
                                        "An optional URL pointing to documentation or any other page. This will be "
                                        "displayed as an icon and open "
                                        "a new page when clicked. You can use either global URLs (beginning with "
                                        "<tt>http://</tt>), absolute local urls (beginning with <tt>/</tt>) or relative "
                                        "URLs (that are relative to <tt>check_mk/</tt>)."
                                    ),
                                )
                            ),
                        },
                    ),
                ),
                Topic(
                    ident="parameter_properties",
                    # TODO if sections are not rendered by fixed DictGroup(),
                    # we will need this:
                    # dictionary=FormSpecDictionary(
                    #    title=Title("Parameter properties"),
                    #    elements={
                    #        "properties": DictElement(
                    #            parameter_form=param_form_spec,
                    #        )
                    #    },
                    # ),
                    dictionary=param_form_spec,
                ),
            ]
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
