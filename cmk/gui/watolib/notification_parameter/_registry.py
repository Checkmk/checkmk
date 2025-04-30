#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import inspect
from collections.abc import Callable

from cmk.ccc.i18n import _
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.version import edition

from cmk.utils.paths import omd_root
from cmk.utils.rulesets.definition import RuleGroup

import cmk.gui.rulespec as _rulespec
import cmk.gui.watolib.rulespecs as _rulespecs
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.gui.form_specs.private import (
    Catalog,
    CommentTextArea,
    LegacyValueSpec,
    ListOfStrings,
    not_empty,
    Topic,
)
from cmk.gui.form_specs.private.catalog import TopicElement
from cmk.gui.form_specs.vue.visitors import DefaultValue
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.valuespec import Migrate as ValueSpecMigrate
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationNotifications
from cmk.gui.watolib.users import notification_script_choices, notification_script_title

from cmk.rulesets.v1 import Help, rule_specs, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FieldSize, String

from ._base import NotificationParameter


class NotificationParameterRegistry(Registry[NotificationParameter]):
    def plugin_name(self, instance):
        return instance.ident

    # TODO: Make this registration_hook actually take an instance. Atm it takes a class and
    #       instantiates it
    def registration_hook(self, instance):
        plugin = instance

        method_source = inspect.getsource(plugin._form_spec)
        if "raise NotImplementedError" in method_source:
            # old ValueSpec
            _rulespecs.rulespec_registry.register(
                _rulespecs.HostRulespec(
                    name=RuleGroup.NotificationParameters(plugin.ident),
                    title=lambda: notification_script_title(plugin.ident),
                    group=RulespecGroupMonitoringConfigurationNotifications,
                    valuespec=lambda: plugin.spec,
                    match_type="dict",
                )
            )
        else:
            loaded_rulespec = rule_specs.NotificationParameters(
                title=Title("%s") % notification_script_title(plugin.ident),
                name=plugin.ident,
                topic=rule_specs.Topic.NOTIFICATIONS,
                parameter_form=plugin._form_spec,
            )
            _rulespec.register_plugins(
                [LoadedRuleSpec(rule_spec=loaded_rulespec, edition_only=edition(omd_root))]
            )

    def parameter_called(self) -> Dictionary:
        return Dictionary(
            title=Title("Parameters"),
            elements={
                "params": DictElement(
                    required=True,
                    parameter_form=ListOfStrings(
                        title=Title("Call with the following parameters"),
                        help_text=Help(
                            "The given parameters are available in scripts as NOTIFY_PARAMETER_1, NOTIFY_PARAMETER_2, etc."
                        ),
                        string_spec=String(),
                    ),
                )
            },
        )

    def form_spec(self, method: str) -> TransformDataForLegacyFormatOrRecomposeFunction:
        try:
            param_form_spec = self._entries[method]._form_spec()
        except KeyError:
            if any(method == script_name for script_name, _title in notification_script_choices()):
                param_form_spec = self.parameter_called()
            else:
                raise MKUserError(
                    None, _("No notification parameters for method '%s' found") % method
                )
        except NotImplementedError:
            try:
                param_form_spec = self._construct_form_spec_from_valuespec(method)
            except Exception as e:
                raise MKUserError(
                    None,
                    _("Error on creating FormSpec from old ValueSpec for method %s: %s")
                    % (method, e),
                )

        def _add_method_key(value: object) -> object:
            if not isinstance(value, dict):
                return value

            if "parameter_properties" in value:
                if isinstance(
                    (parameter_properties := value["parameter_properties"]), DefaultValue
                ):
                    return value
                if "method_parameters" not in parameter_properties:
                    value["parameter_properties"] = {"method_parameters": parameter_properties}

            return value

        def _remove_method_key(value: object) -> object:
            if not isinstance(value, dict):
                return value
            if parameter_properties := value.get("parameter_properties"):
                if "method_parameters" in parameter_properties:
                    value["parameter_properties"] = parameter_properties["method_parameters"]
            return value

        return TransformDataForLegacyFormatOrRecomposeFunction(
            from_disk=_add_method_key,
            to_disk=_remove_method_key,
            wrapped_form_spec=Catalog(
                elements={
                    "general": Topic(
                        title=Title("General properties"),
                        elements={
                            "description": TopicElement(
                                parameter_form=String(
                                    title=Title("Description"),
                                    field_size=FieldSize.LARGE,
                                    custom_validate=[not_empty()],
                                ),
                                required=True,
                            ),
                            "comment": TopicElement(
                                required=True,
                                parameter_form=CommentTextArea(
                                    title=Title("Comment"),
                                ),
                            ),
                            "docu_url": TopicElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Documentation URL"),
                                    help_text=Help(
                                        "An optional URL pointing to documentation or any other page. This will be "
                                        "displayed as an icon and open "
                                        "a new page when clicked. You can use either global URLs (beginning with "
                                        "<tt>http://</tt>), absolute local urls (beginning with <tt>/</tt>) or relative "
                                        "URLs (that are relative to <tt>check_mk/</tt>)."
                                    ),
                                ),
                            ),
                        },
                    ),
                    "parameter_properties": Topic(
                        title=Title("Parameter properties"),
                        elements={
                            "method_parameters": TopicElement(
                                required=True,
                                parameter_form=param_form_spec,
                            ),
                        },
                    ),
                }
            ),
        )

    def _construct_form_spec_from_valuespec(self, method: str) -> Dictionary:
        """
        In case we have an old ValueSpec (e.g. custom notification), try
        to convert it to a FormSpec. We assume that nearly all customizations
        use a Dictionary (see typing of NotificationParameter). As we have at
        least one built-in parameter that uses a Migrate, handle also this case.
        """
        migrate: Callable | None = None
        if isinstance((valuespec := self._entries[method].spec), ValueSpecMigrate):
            if isinstance(valuespec._valuespec, ValueSpecDictionary):
                valuespec_elements = valuespec._valuespec._elements()
                required_keys = valuespec._valuespec._required_keys
                migrate = valuespec.to_valuespec
            else:
                raise MKUserError(
                    None,
                    _("No Dictionary ValueSpec within Migrate: %s") % valuespec._valuespec,
                )
        else:
            # Dictionary
            valuespec_elements = valuespec._elements()
            required_keys = valuespec._required_keys

        new_elements: dict[str, DictElement] = {}
        for entry in valuespec_elements:
            new_elements[entry[0]] = DictElement(
                parameter_form=LegacyValueSpec.wrap(entry[1]),
                required=entry[0] in required_keys,
            )

        return Dictionary(
            elements=new_elements,
            migrate=migrate,
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
    notification_parameter_registry.register(parameter_class())
