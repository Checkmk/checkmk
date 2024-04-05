#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import urllib.parse
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, assert_never, Callable, TypeVar

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.version import Edition

from cmk.gui import inventory as legacy_inventory_groups
from cmk.gui import valuespec as legacy_valuespecs
from cmk.gui import wato as legacy_wato
from cmk.gui.exceptions import MKUserError
from cmk.gui.mkeventd import wato as legacy_mkeventd_groups
from cmk.gui.utils.rule_specs.loader import RuleSpec as APIV1RuleSpec
from cmk.gui.wato import _check_mk_configuration as legacy_cmk_config_groups
from cmk.gui.wato import _rulespec_groups as legacy_wato_groups
from cmk.gui.watolib import config_domains as legacy_config_domains
from cmk.gui.watolib import rulespec_groups as legacy_rulespec_groups
from cmk.gui.watolib import rulespecs as legacy_rulespecs
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    ManualCheckParameterRulespec,
    rulespec_group_registry,
)

from cmk.rulesets import v1 as ruleset_api_v1

GENERATED_GROUP_PREFIX = "gen-"


def _localize_optional(
    to_localize: ruleset_api_v1.Localizable | None, localizer: Callable[[str], str]
) -> str | None:
    return None if to_localize is None else to_localize.localize(localizer)


def convert_to_legacy_rulespec(
    to_convert: APIV1RuleSpec, edition_only: Edition, localizer: Callable[[str], str]
) -> legacy_rulespecs.Rulespec:
    match to_convert:
        case ruleset_api_v1.rule_specs.ActiveChecks():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_wato_groups.RulespecGroupIntegrateOtherServices,
                localizer,
                config_scope_prefix=RuleGroup.ActiveChecks,
            )
        case ruleset_api_v1.rule_specs.AgentAccess():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_cmk_config_groups.RulespecGroupAgent,
                localizer,
            )
        case ruleset_api_v1.rule_specs.AgentConfig():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_rulespec_groups.RulespecGroupMonitoringAgents,
                localizer,
                config_scope_prefix=RuleGroup.AgentConfig,
            )
        case ruleset_api_v1.rule_specs.CheckParameterWithItem():
            return _convert_to_legacy_check_parameter_with_item_rulespec(
                to_convert, edition_only, localizer
            )
        case ruleset_api_v1.rule_specs.CheckParameterWithoutItem():
            return _convert_to_legacy_check_parameter_without_item_rulespec(
                to_convert, edition_only, localizer
            )
        case ruleset_api_v1.rule_specs.EnforcedServiceWithItem():
            item_spec = partial(_convert_to_legacy_item_spec, to_convert.item_form, localizer)
            return _convert_to_legacy_manual_check_parameter_rulespec(
                to_convert, edition_only, localizer, item_spec
            )
        case ruleset_api_v1.rule_specs.EnforcedServiceWithoutItem():
            return _convert_to_legacy_manual_check_parameter_rulespec(
                to_convert, edition_only, localizer
            )
        case ruleset_api_v1.rule_specs.ExtraHostConfEventConsole():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_mkeventd_groups.RulespecGroupEventConsole,
                localizer,
                config_scope_prefix=RuleGroup.ExtraHostConf,
            )
        case ruleset_api_v1.rule_specs.ExtraHostConfHostMonitoring():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_rulespec_groups.RulespecGroupHostsMonitoringRules,
                localizer,
                config_scope_prefix=RuleGroup.ExtraHostConf,
            )
        case ruleset_api_v1.rule_specs.ExtraServiceConf():
            return _convert_to_legacy_service_rule_spec_rulespec(
                to_convert,
                localizer,
                config_scope_prefix=RuleGroup.ExtraServiceConf,
            )
        case ruleset_api_v1.rule_specs.HostMonitoring():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_rulespec_groups.RulespecGroupHostsMonitoringRules,
                localizer,
            )
        case ruleset_api_v1.rule_specs.InventoryParameters():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_inventory_groups.RulespecGroupInventory,
                localizer,
                config_scope_prefix=RuleGroup.InvParameters,
            )
        case ruleset_api_v1.rule_specs.NotificationParameters():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
                localizer,
                config_scope_prefix=RuleGroup.NotificationParameters,
            )
        case ruleset_api_v1.rule_specs.DiscoveryParameters():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_wato.RulespecGroupDiscoveryCheckParameters,
                localizer,
            )
        case ruleset_api_v1.rule_specs.ServiceMonitoring():
            return _convert_to_legacy_service_rule_spec_rulespec(
                to_convert,
                localizer,
            )
        case ruleset_api_v1.rule_specs.ServiceMonitoringWithoutService():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
                localizer,
            )
        case ruleset_api_v1.rule_specs.SNMP():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_rulespec_groups.RulespecGroupAgentSNMP,
                localizer,
            )
        case ruleset_api_v1.rule_specs.SpecialAgent():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_wato.RulespecGroupDatasourcePrograms,
                localizer,
                config_scope_prefix=RuleGroup.SpecialAgents,
            )
        case other:
            assert_never(other)


def _convert_to_legacy_check_parameter_with_item_rulespec(
    to_convert: ruleset_api_v1.rule_specs.CheckParameterWithItem,
    edition_only: Edition,
    localizer: Callable[[str], str],
) -> CheckParameterRulespecWithItem:
    return CheckParameterRulespecWithItem(
        check_group_name=to_convert.name,
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        group=_convert_to_legacy_rulespec_group(
            legacy_rulespec_groups.RulespecGroupMonitoringConfiguration, to_convert.topic, localizer
        ),
        item_spec=partial(_convert_to_legacy_item_spec, to_convert.item_form, localizer),
        match_type="dict",
        parameter_valuespec=partial(
            _convert_to_legacy_valuespec, to_convert.parameter_form(), localizer
        ),
        is_deprecated=to_convert.is_deprecated,
        create_manual_check=False,
        # weird field since the CME, as well as the CSE is based on a CCE, but we currently only
        # want to mark rulespecs that are available in both the CCE and CME as such
        is_cloud_and_managed_edition_only=edition_only is Edition.CCE,
    )


def _convert_to_legacy_check_parameter_without_item_rulespec(
    to_convert: ruleset_api_v1.rule_specs.CheckParameterWithoutItem,
    edition_only: Edition,
    localizer: Callable[[str], str],
) -> CheckParameterRulespecWithoutItem:
    return CheckParameterRulespecWithoutItem(
        check_group_name=to_convert.name,
        title=partial(to_convert.title.localize, localizer),
        group=_convert_to_legacy_rulespec_group(
            legacy_rulespec_groups.RulespecGroupMonitoringConfiguration, to_convert.topic, localizer
        ),
        match_type="dict",
        parameter_valuespec=partial(
            _convert_to_legacy_valuespec, to_convert.parameter_form(), localizer
        ),
        create_manual_check=False,
        is_cloud_and_managed_edition_only=edition_only is Edition.CCE,
    )


def _convert_to_legacy_manual_check_parameter_rulespec(
    to_convert: ruleset_api_v1.rule_specs.EnforcedServiceWithItem
    | ruleset_api_v1.rule_specs.EnforcedServiceWithoutItem,
    edition_only: Edition,
    localizer: Callable[[str], str],
    item_spec: Callable[[], legacy_valuespecs.ValueSpec] | None = None,
) -> ManualCheckParameterRulespec:
    return ManualCheckParameterRulespec(
        group=_convert_to_legacy_rulespec_group(
            legacy_rulespecs.RulespecGroupEnforcedServices, to_convert.topic, localizer
        ),
        check_group_name=to_convert.name,
        parameter_valuespec=partial(
            _convert_to_legacy_valuespec, to_convert.parameter_form(), localizer
        )
        if to_convert.parameter_form is not None
        else None,
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=False,
        match_type="dict",
        item_spec=item_spec,
        is_cloud_and_managed_edition_only=edition_only is Edition.CCE,
    )


def _convert_to_legacy_rulespec_group(
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    topic_to_convert: ruleset_api_v1.rule_specs.Topic | ruleset_api_v1.rule_specs.CustomTopic,
    localizer: Callable[[str], str],
) -> type[legacy_rulespecs.RulespecBaseGroup]:
    if isinstance(topic_to_convert, ruleset_api_v1.rule_specs.Topic):
        return _get_builtin_legacy_sub_group_with_main_group(
            legacy_main_group, topic_to_convert, localizer
        )
    if isinstance(topic_to_convert, ruleset_api_v1.rule_specs.CustomTopic):
        return _convert_to_custom_group(legacy_main_group, topic_to_convert.title, localizer)
    raise ValueError(topic_to_convert)


def _convert_to_legacy_host_rule_spec_rulespec(
    to_convert: ruleset_api_v1.rule_specs.ActiveChecks
    | ruleset_api_v1.rule_specs.AgentConfig
    | ruleset_api_v1.rule_specs.AgentAccess
    | ruleset_api_v1.rule_specs.ExtraHostConfEventConsole
    | ruleset_api_v1.rule_specs.ExtraHostConfHostMonitoring
    | ruleset_api_v1.rule_specs.HostMonitoring
    | ruleset_api_v1.rule_specs.NotificationParameters
    | ruleset_api_v1.rule_specs.InventoryParameters
    | ruleset_api_v1.rule_specs.DiscoveryParameters
    | ruleset_api_v1.rule_specs.ServiceMonitoringWithoutService
    | ruleset_api_v1.rule_specs.SNMP
    | ruleset_api_v1.rule_specs.SpecialAgent,
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    localizer: Callable[[str], str],
    config_scope_prefix: Callable[[str | None], str] = lambda x: x or "",
) -> legacy_rulespecs.HostRulespec:
    return legacy_rulespecs.HostRulespec(
        group=_convert_to_legacy_rulespec_group(legacy_main_group, to_convert.topic, localizer),
        name=config_scope_prefix(to_convert.name),
        valuespec=partial(_convert_to_legacy_valuespec, to_convert.parameter_form(), localizer),
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=to_convert.is_deprecated,
        match_type="dict"
        if to_convert.eval_type == ruleset_api_v1.rule_specs.EvalType.MERGE
        else "all",
    )


def _convert_to_legacy_service_rule_spec_rulespec(
    to_convert: ruleset_api_v1.rule_specs.ServiceMonitoring
    | ruleset_api_v1.rule_specs.ExtraServiceConf,
    localizer: Callable[[str], str],
    config_scope_prefix: Callable[[str | None], str] = lambda x: x or "",
) -> legacy_rulespecs.ServiceRulespec:
    return legacy_rulespecs.ServiceRulespec(
        group=_convert_to_legacy_rulespec_group(
            legacy_rulespec_groups.RulespecGroupMonitoringConfiguration, to_convert.topic, localizer
        ),
        item_type="service",
        name=config_scope_prefix(to_convert.name),
        valuespec=partial(_convert_to_legacy_valuespec, to_convert.parameter_form(), localizer),
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=to_convert.is_deprecated,
        match_type="dict"
        if to_convert.eval_type == ruleset_api_v1.rule_specs.EvalType.MERGE
        else "all",
    )


def _get_builtin_legacy_sub_group_with_main_group(  # pylint: disable=too-many-branches
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    topic_to_convert: ruleset_api_v1.rule_specs.Topic,
    localizer: Callable[[str], str],
) -> type[legacy_rulespecs.RulespecSubGroup]:
    match topic_to_convert:
        case ruleset_api_v1.rule_specs.Topic.AGENT_PLUGINS:
            return _to_generated_builtin_sub_group(legacy_main_group, "Agent plug-ins", localizer)
        case ruleset_api_v1.rule_specs.Topic.APPLICATIONS:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersApplications
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsApps
            return _to_generated_builtin_sub_group(legacy_main_group, "Applications", localizer)
        case ruleset_api_v1.rule_specs.Topic.CACHING_MESSAGE_QUEUES:
            return _to_generated_builtin_sub_group(
                legacy_main_group, "Caching / Message Queues", localizer
            )
        case ruleset_api_v1.rule_specs.Topic.CLOUD:
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsCloud
            return _to_generated_builtin_sub_group(legacy_main_group, "Cloud", localizer)
        case ruleset_api_v1.rule_specs.Topic.CONFIGURATION_DEPLOYMENT:
            return _to_generated_builtin_sub_group(
                legacy_main_group, "Configuration & Deployment", localizer
            )
        case ruleset_api_v1.rule_specs.Topic.DATABASES:
            return _to_generated_builtin_sub_group(legacy_main_group, "Databases", localizer)
        case ruleset_api_v1.rule_specs.Topic.GENERAL:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_rulespec_groups.RulespecGroupMonitoringConfigurationVarious
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsCustom
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupHostsMonitoringRules:
                return legacy_rulespec_groups.RulespecGroupHostsMonitoringRulesVarious
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents:
                return legacy_rulespec_groups.RulespecGroupMonitoringAgentsGenericOptions
            if legacy_main_group == legacy_wato.RulespecGroupDiscoveryCheckParameters:
                return legacy_wato_groups.RulespecGroupCheckParametersDiscovery
            return _to_generated_builtin_sub_group(legacy_main_group, "General", localizer)
        case ruleset_api_v1.rule_specs.Topic.ENVIRONMENTAL:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersEnvironment
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesEnvironment
            return _to_generated_builtin_sub_group(legacy_main_group, "Environmental", localizer)
        case ruleset_api_v1.rule_specs.Topic.LINUX:
            return _to_generated_builtin_sub_group(legacy_main_group, "Linux", localizer)
        case ruleset_api_v1.rule_specs.Topic.NETWORKING:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersNetworking
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesNetworking
            return _to_generated_builtin_sub_group(legacy_main_group, "Networking", localizer)
        case ruleset_api_v1.rule_specs.Topic.MIDDLEWARE:
            return _to_generated_builtin_sub_group(legacy_main_group, "Middleware", localizer)
        case ruleset_api_v1.rule_specs.Topic.NOTIFICATIONS:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_rulespec_groups.RulespecGroupMonitoringConfigurationNotifications
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupHostsMonitoringRules:
                return legacy_rulespec_groups.RulespecGroupHostsMonitoringRulesNotifications
            return _to_generated_builtin_sub_group(legacy_main_group, "Notifications", localizer)
        case ruleset_api_v1.rule_specs.Topic.OPERATING_SYSTEM:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersOperatingSystem
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesOperatingSystem
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsOS
            return _to_generated_builtin_sub_group(legacy_main_group, "Operating System", localizer)
        case ruleset_api_v1.rule_specs.Topic.PERIPHERALS:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersPrinters
            return _to_generated_builtin_sub_group(legacy_main_group, "Peripherals", localizer)
        case ruleset_api_v1.rule_specs.Topic.POWER:
            return _to_generated_builtin_sub_group(legacy_main_group, "Power", localizer)
        case ruleset_api_v1.rule_specs.Topic.SERVER_HARDWARE:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersHardware
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesHardware
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsHardware
            return _to_generated_builtin_sub_group(legacy_main_group, "Server hardware", localizer)
        case ruleset_api_v1.rule_specs.Topic.STORAGE:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersStorage
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesStorage
            return _to_generated_builtin_sub_group(legacy_main_group, "Storage", localizer)
        case ruleset_api_v1.rule_specs.Topic.VIRTUALIZATION:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersVirtualization
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesVirtualization
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsContainer
            return _to_generated_builtin_sub_group(legacy_main_group, "Virtualization", localizer)
        case ruleset_api_v1.rule_specs.Topic.WINDOWS:
            return _to_generated_builtin_sub_group(legacy_main_group, "Windows", localizer)
        case other:
            assert_never(other)

    raise NotImplementedError(topic_to_convert)


def _convert_to_custom_group(
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    title: ruleset_api_v1.Localizable,
    localizer: Callable[[str], str],
) -> type[legacy_rulespecs.RulespecSubGroup]:
    identifier = f"{GENERATED_GROUP_PREFIX}{hash(title.localize(lambda x: x))}"
    if registered_group := rulespec_group_registry.get(f"{legacy_main_group().name}/{identifier}"):
        if not issubclass(registered_group, legacy_rulespecs.RulespecSubGroup):
            raise TypeError(registered_group)
        return registered_group

    group_class = type(
        identifier,
        (legacy_rulespecs.RulespecSubGroup,),
        {
            "title": title.localize(localizer),
            "main_group": legacy_main_group,
            "sub_group_name": identifier,
        },
    )
    rulespec_group_registry.register(group_class)
    return group_class


def _to_generated_builtin_sub_group(
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    raw_title: str,
    localizer: Callable[[str], str],
) -> type[legacy_rulespecs.RulespecSubGroup]:
    title = ruleset_api_v1.Localizable(raw_title)
    return _convert_to_custom_group(legacy_main_group, title, localizer)


@dataclass(frozen=True)
class _LegacyDictKeyProps:
    required: list[str]
    hidden: list[str]


def _extract_dictionary_key_props(
    dic_elements: Mapping[str, ruleset_api_v1.form_specs.DictElement]
) -> _LegacyDictKeyProps:
    key_props = _LegacyDictKeyProps(required=[], hidden=[])

    for key, dic_elem in dic_elements.items():
        if dic_elem.required:
            key_props.required.append(key)
        if dic_elem.read_only:
            key_props.hidden.append(key)

    return key_props


def _convert_to_inner_legacy_valuespec(
    to_convert: ruleset_api_v1.form_specs.FormSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.ValueSpec:
    match to_convert:
        case ruleset_api_v1.form_specs.Integer():
            return _convert_to_legacy_integer(to_convert, localizer)

        case ruleset_api_v1.form_specs.Float():
            return _convert_to_legacy_float(to_convert, localizer)

        case ruleset_api_v1.form_specs.DataSize():
            return _convert_to_legacy_filesize(to_convert, localizer)

        case ruleset_api_v1.form_specs.Percentage():
            return _convert_to_legacy_percentage(to_convert, localizer)

        case ruleset_api_v1.form_specs.TextInput():
            return _convert_to_legacy_text_input(to_convert, localizer)

        case ruleset_api_v1.form_specs.Tuple():
            return _convert_to_legacy_tuple(to_convert, localizer)

        case ruleset_api_v1.form_specs.Dictionary():
            elements = [
                (key, _convert_to_legacy_valuespec(elem.parameter_form, localizer))
                for key, elem in to_convert.elements.items()
            ]

            legacy_key_props = _extract_dictionary_key_props(to_convert.elements)

            return legacy_valuespecs.Dictionary(
                elements=elements,
                title=_localize_optional(to_convert.title, localizer),
                help=_localize_optional(to_convert.help_text, localizer),
                empty_text=_localize_optional(to_convert.no_elements_text, localizer),
                required_keys=legacy_key_props.required,
                ignored_keys=to_convert.deprecated_elements,
                hidden_keys=legacy_key_props.hidden,
                validate=_convert_to_legacy_validation(to_convert.custom_validate, localizer)
                if to_convert.custom_validate is not None
                else None,
            )

        case ruleset_api_v1.form_specs.DropdownChoice():
            return _convert_to_legacy_dropdown_choice(to_convert, localizer)

        case ruleset_api_v1.form_specs.CascadingDropdown():
            return _convert_to_legacy_cascading_dropdown(to_convert, localizer)

        case ruleset_api_v1.form_specs.ServiceState():
            return _convert_to_legacy_monitoring_state(to_convert, localizer)

        case ruleset_api_v1.form_specs.HostState():
            return _convert_to_legacy_host_state(to_convert, localizer)

        case ruleset_api_v1.form_specs.List():
            return _convert_to_legacy_list(to_convert, localizer)

        case ruleset_api_v1.form_specs.FixedValue():
            return _convert_to_legacy_fixed_value(to_convert, localizer)

        case ruleset_api_v1.form_specs.TimeSpan():
            return _convert_to_legacy_age(to_convert, localizer)

        case ruleset_api_v1.form_specs.Levels():
            return _convert_to_legacy_levels(to_convert, localizer)

        case ruleset_api_v1.form_specs.Proxy():
            return _convert_to_legacy_http_proxy(to_convert, localizer)

        case ruleset_api_v1.form_specs.BooleanChoice():
            return _convert_to_legacy_checkbox(to_convert, localizer)

        case other:
            assert_never(other)


def _convert_to_legacy_valuespec(
    to_convert: ruleset_api_v1.form_specs.FormSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.ValueSpec:
    if isinstance(to_convert.transform, ruleset_api_v1.form_specs.Migrate):
        return legacy_valuespecs.Migrate(
            valuespec=_convert_to_inner_legacy_valuespec(to_convert, localizer),
            migrate=to_convert.transform.raw_to_form,
        )
    if isinstance(to_convert.transform, ruleset_api_v1.form_specs.Transform):
        return legacy_valuespecs.Transform(
            valuespec=_convert_to_inner_legacy_valuespec(to_convert, localizer),
            to_valuespec=to_convert.transform.raw_to_form,
            from_valuespec=to_convert.transform.form_to_raw,
        )
    return _convert_to_inner_legacy_valuespec(to_convert, localizer)


def _convert_to_legacy_integer(
    to_convert: ruleset_api_v1.form_specs.Integer, localizer: Callable[[str], str]
) -> legacy_valuespecs.Integer:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
    }
    converted_kwargs["unit"] = ""
    if to_convert.unit is not None:
        converted_kwargs["unit"] = to_convert.unit.localize(localizer)

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Integer(**converted_kwargs)


def _convert_to_legacy_float(
    to_convert: ruleset_api_v1.form_specs.Float, localizer: Callable[[str], str]
) -> legacy_valuespecs.Float:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
    }
    converted_kwargs["unit"] = ""
    if to_convert.unit is not None:
        converted_kwargs["unit"] = to_convert.unit.localize(localizer)

    if to_convert.display_precision is not None:
        converted_kwargs["display_format"] = f"%.{to_convert.display_precision}f"

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Float(**converted_kwargs)


def _convert_to_legacy_filesize(
    to_convert: ruleset_api_v1.form_specs.DataSize, localizer: Callable[[str], str]
) -> legacy_valuespecs.Filesize:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
    }

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Filesize(**converted_kwargs)


def _convert_to_legacy_percentage(
    to_convert: ruleset_api_v1.form_specs.Percentage, localizer: Callable[[str], str]
) -> legacy_valuespecs.Percentage:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
    }

    if to_convert.display_precision is not None:
        converted_kwargs["display_format"] = f"%.{to_convert.display_precision}f"

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Percentage(**converted_kwargs)


def _convert_to_legacy_text_input(
    to_convert: ruleset_api_v1.form_specs.TextInput, localizer: Callable[[str], str]
) -> legacy_valuespecs.TextInput:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }

    if to_convert.input_hint is not None:
        converted_kwargs["placeholder"] = to_convert.input_hint

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.TextInput(**converted_kwargs)


def _convert_to_legacy_tuple(
    to_convert: ruleset_api_v1.form_specs.Tuple, localizer: Callable[[str], str]
) -> legacy_valuespecs.Tuple:
    legacy_elements = [
        _convert_to_legacy_valuespec(element, localizer) for element in to_convert.elements
    ]
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )
    return legacy_valuespecs.Tuple(elements=legacy_elements, **converted_kwargs)


def _convert_to_legacy_monitoring_state(
    to_convert: ruleset_api_v1.form_specs.ServiceState, localizer: Callable[[str], str]
) -> legacy_valuespecs.DropdownChoice:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }
    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    return legacy_valuespecs.MonitoringState(**converted_kwargs)


def _convert_to_legacy_host_state(
    to_convert: ruleset_api_v1.form_specs.HostState, localizer: Callable[[str], str]
) -> legacy_valuespecs.DropdownChoice:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }
    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    return legacy_valuespecs.DropdownChoice(
        choices=[
            (0, ruleset_api_v1.Localizable("Up").localize(localizer)),
            (1, ruleset_api_v1.Localizable("Down").localize(localizer)),
            (2, ruleset_api_v1.Localizable("Unreachable").localize(localizer)),
        ],
        sorted=False,
        **converted_kwargs,
    )


def _convert_to_legacy_dropdown_choice(
    to_convert: ruleset_api_v1.form_specs.DropdownChoice, localizer: Callable[[str], str]
) -> legacy_valuespecs.DropdownChoice:
    choices = [
        (
            element.name.value if isinstance(element.name, enum.Enum) else element.name,
            element.title.localize(localizer),
        )
        for element in to_convert.elements
    ]
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "empty_text": _localize_optional(to_convert.no_elements_text, localizer),
        "read_only": to_convert.frozen,
    }

    if to_convert.invalid_element_validation is not None:
        match to_convert.invalid_element_validation.mode:
            case ruleset_api_v1.form_specs.InvalidElementMode.COMPLAIN:
                converted_kwargs["invalid_choice"] = "complain"
            case ruleset_api_v1.form_specs.InvalidElementMode.KEEP:
                converted_kwargs["invalid_choice"] = None
            case _:
                assert_never(to_convert.invalid_element_validation.mode)

        converted_kwargs["invalid_choice_title"] = _localize_optional(
            to_convert.invalid_element_validation.display, localizer
        )
        converted_kwargs["invalid_choice_error"] = _localize_optional(
            to_convert.invalid_element_validation.error_msg, localizer
        )

    if to_convert.deprecated_elements is not None:
        converted_kwargs["deprecated_choices"] = to_convert.deprecated_elements

    if to_convert.prefill_selection is not None:
        converted_kwargs["default_value"] = (
            to_convert.prefill_selection.value
            if isinstance(to_convert.prefill_selection, enum.Enum)
            else to_convert.prefill_selection
        )

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.DropdownChoice(choices, **converted_kwargs)


def _convert_to_legacy_cascading_dropdown(
    to_convert: ruleset_api_v1.form_specs.CascadingDropdown, localizer: Callable[[str], str]
) -> legacy_valuespecs.CascadingDropdown:
    legacy_choices = [
        (
            element.name.value if isinstance(element.name, enum.StrEnum) else element.name,
            element.parameter_form.title.localize(localizer)
            if hasattr(element.parameter_form, "title") and element.parameter_form.title is not None
            else str(element.name),
            _convert_to_legacy_valuespec(element.parameter_form, localizer),
        )
        for element in to_convert.elements
    ]

    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }
    if to_convert.prefill_selection is None:
        converted_kwargs["no_preselect_title"] = ""
    else:
        converted_kwargs["default_value"] = to_convert.prefill_selection
    return legacy_valuespecs.CascadingDropdown(choices=legacy_choices, **converted_kwargs)


def _convert_to_legacy_item_spec(
    to_convert: ruleset_api_v1.form_specs.ItemFormSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.TextInput | legacy_valuespecs.DropdownChoice:
    if isinstance(to_convert, ruleset_api_v1.form_specs.TextInput):
        return _convert_to_legacy_text_input(to_convert, localizer)
    if isinstance(to_convert, ruleset_api_v1.form_specs.DropdownChoice):
        return _convert_to_legacy_dropdown_choice(to_convert, localizer)

    raise ValueError(to_convert)


_ValidateFuncType = TypeVar("_ValidateFuncType")


def _convert_to_legacy_validation(
    v1_validate_func: Callable[[_ValidateFuncType], object],
    localizer: Callable[[str], str],
) -> Callable[[_ValidateFuncType, str], None]:
    def wrapper(value: _ValidateFuncType, var_prefix: str) -> None:
        try:
            v1_validate_func(value)
        except ruleset_api_v1.validators.ValidationError as e:
            raise MKUserError(var_prefix, e.message.localize(localizer))

    return wrapper


def _convert_to_legacy_list(
    to_convert: ruleset_api_v1.form_specs.List, localizer: Callable[[str], str]
) -> legacy_valuespecs.ListOf | legacy_valuespecs.ListOfStrings:
    converted_kwargs: MutableMapping[str, Any] = {
        "valuespec": _convert_to_legacy_valuespec(to_convert.parameter_form, localizer),
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "movable": to_convert.order_editable,
    }

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    return legacy_valuespecs.ListOf(**converted_kwargs)


def _convert_to_legacy_fixed_value(
    to_convert: ruleset_api_v1.form_specs.FixedValue, localizer: Callable[[str], str]
) -> legacy_valuespecs.FixedValue:
    return legacy_valuespecs.FixedValue(
        value=to_convert.value,
        totext=_localize_optional(to_convert.label, localizer)
        if to_convert.label is not None
        else "",
        title=_localize_optional(to_convert.title, localizer),
        help=_localize_optional(to_convert.help_text, localizer),
    )


def _convert_to_legacy_age(
    to_convert: ruleset_api_v1.form_specs.TimeSpan, localizer: Callable[[str], str]
) -> legacy_valuespecs.Age:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
    }

    if to_convert.displayed_units is not None:
        converted_kwargs["display"] = [u.value for u in to_convert.displayed_units]

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Age(**converted_kwargs)


class _LevelDirection(enum.Enum):
    UPPER = "upper"
    LOWER = "lower"


def _get_fixed_level_titles(
    level_direction: _LevelDirection, localizer: Callable[[str], str]
) -> tuple[str, str]:
    if level_direction is _LevelDirection.LOWER:
        warn_title = localizer("Warning below")
        crit_title = localizer("Critical below")
    elif level_direction is _LevelDirection.UPPER:
        warn_title = localizer("Warning at")
        crit_title = localizer("Critical at")
    else:
        assert_never(level_direction)
    return warn_title, crit_title


_TNumericSpec = (
    ruleset_api_v1.form_specs.Integer
    | ruleset_api_v1.form_specs.Float
    | ruleset_api_v1.form_specs.DataSize
    | ruleset_api_v1.form_specs.Percentage
)


def _get_legacy_level_spec(
    form_spec: type[_TNumericSpec],
    title: str,
    unit: str,
    prefill: float | legacy_valuespecs.Sentinel,
) -> (
    legacy_valuespecs.Integer
    | legacy_valuespecs.Float
    | legacy_valuespecs.Filesize
    | legacy_valuespecs.Percentage
):
    if issubclass(form_spec, ruleset_api_v1.form_specs.Integer):
        return legacy_valuespecs.Integer(
            title=title,
            unit=unit,
            default_value=int(prefill) if isinstance(prefill, float) else prefill,
        )
    if issubclass(form_spec, ruleset_api_v1.form_specs.Float):
        return legacy_valuespecs.Float(
            title=title,
            unit=unit,
            default_value=int(prefill) if isinstance(prefill, float) else prefill,
        )
    if issubclass(form_spec, ruleset_api_v1.form_specs.DataSize):
        return legacy_valuespecs.Filesize(
            title=title,
            default_value=int(prefill) if isinstance(prefill, float) else prefill,
        )

    if issubclass(form_spec, ruleset_api_v1.form_specs.Percentage):
        return legacy_valuespecs.Percentage(title=title, unit="%", default_value=prefill)

    # TODO: allow all numeric specs
    raise NotImplementedError(form_spec)


def _get_fixed_levels_choice_element(
    form_spec: type[_TNumericSpec],
    levels: ruleset_api_v1.form_specs.FixedLevels,
    level_direction: _LevelDirection,
    unit: str,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.Tuple:
    warn_title, crit_title = _get_fixed_level_titles(level_direction, localizer)

    prefill_value: tuple[float, float] | tuple[
        legacy_valuespecs.Sentinel, legacy_valuespecs.Sentinel
    ] = (legacy_valuespecs.DEF_VALUE, legacy_valuespecs.DEF_VALUE)
    if levels.prefill_value is not None:
        prefill_value = levels.prefill_value

    return legacy_valuespecs.Tuple(
        elements=[
            _get_legacy_level_spec(form_spec, warn_title, unit, prefill_value[0]),
            _get_legacy_level_spec(form_spec, crit_title, unit, prefill_value[1]),
        ],
    )


@dataclass
class _WarnCritTupleInfo:
    warn: str
    crit: str
    unit: str
    prefill: tuple[int, int] | tuple[float, float]


@dataclass
class _FixedLimitsInfo:
    warn: str
    crit: str
    help: str


def _get_level_computation_info(
    valuespec: type[legacy_valuespecs.Integer | legacy_valuespecs.Float],
    to_convert: ruleset_api_v1.form_specs.PredictiveLevels,
    unit: str,
    level_dir: str,
    limit: str,
    limit_dir: str,
    level_magnitude: str,
    localizer: Callable[[str], str],
) -> tuple[_WarnCritTupleInfo, _WarnCritTupleInfo, _WarnCritTupleInfo, _FixedLimitsInfo]:
    def _default_prefill(
        prefill: tuple[float, float] | None, default: tuple[float, float]
    ) -> tuple[float, float]:
        return prefill if prefill is not None else default

    def _get_warn_crit_tuple_info(prefill: tuple[float, float], _unit: str) -> _WarnCritTupleInfo:
        return _WarnCritTupleInfo(
            warn=localizer("Warning %s") % level_dir,
            crit=localizer("Critical %s") % level_dir,
            unit=_unit,
            prefill=prefill,
        )

    if issubclass(valuespec, legacy_valuespecs.Percentage):
        default = (0.0, 0.0)
        unit = "%"
    elif issubclass(valuespec, legacy_valuespecs.Integer):
        default = (0, 0)
    elif issubclass(valuespec, legacy_valuespecs.Float):
        default = (0.0, 0.0)
    else:
        raise NotImplementedError(valuespec)

    abs_info = _get_warn_crit_tuple_info(
        _default_prefill(to_convert.prefill_abs_diff, default), unit
    )
    rel_info = _get_warn_crit_tuple_info(
        _default_prefill(to_convert.prefill_rel_diff, (10.0, 20.0)), "%"
    )
    stddev_info = _get_warn_crit_tuple_info(
        _default_prefill(to_convert.prefill_stddev_diff, (2.0, 4.0)),
        localizer("times the standard deviation"),
    )

    fixed_info = _FixedLimitsInfo(
        warn=localizer("Warning level is at %s") % limit,
        crit=localizer("Critical level is at %s") % limit,
        help=localizer(
            "Regardless of how the dynamic levels are computed according to the prediction: they "
            "will never be set %s the following limits. This avoids false alarms during times where"
            " the predicted levels would be very %s."
        )
        % (limit_dir, level_magnitude),
    )
    return abs_info, rel_info, stddev_info, fixed_info


def _get_level_computation_dropdown_choice(
    ident: str,
    spec: type[legacy_valuespecs.Integer] | type[legacy_valuespecs.Float],
    title: str,
    help_text: str,
    info: _WarnCritTupleInfo,
) -> tuple[str, str, legacy_valuespecs.Tuple]:
    elements: list[legacy_valuespecs.Integer | legacy_valuespecs.Float] = []
    if issubclass(spec, legacy_valuespecs.Integer):
        elements.extend(
            [
                spec(title=info.warn, unit=info.unit, default_value=int(info.prefill[0])),
                spec(title=info.crit, unit=info.unit, default_value=int(info.prefill[1])),
            ]
        )
    elif issubclass(spec, legacy_valuespecs.Float):
        elements.extend(
            [
                spec(title=info.warn, unit=info.unit, default_value=info.prefill[0]),
                spec(title=info.crit, unit=info.unit, default_value=info.prefill[1]),
            ]
        )
    else:
        raise NotImplementedError(spec)
    return ident, title, legacy_valuespecs.Tuple(help=help_text, elements=elements)


class _PredictiveLevelDefinition(enum.StrEnum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    STDDEV = "stddev"


def _get_level_computation_dropdown(
    valuespec: type[legacy_valuespecs.Integer] | type[legacy_valuespecs.Float],
    abs_info: _WarnCritTupleInfo,
    rel_info: _WarnCritTupleInfo,
    stddev_info: _WarnCritTupleInfo,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.CascadingDropdown:
    return legacy_valuespecs.CascadingDropdown(
        title=localizer("Level definition in relation to the predicted value"),
        choices=[
            _get_level_computation_dropdown_choice(
                _PredictiveLevelDefinition.ABSOLUTE.value,
                valuespec,
                localizer("Absolute difference"),
                localizer(
                    "The thresholds are calculated by increasing or decreasing the predicted value by a fixed absolute value"
                ),
                abs_info,
            ),
            _get_level_computation_dropdown_choice(
                _PredictiveLevelDefinition.RELATIVE.value,
                legacy_valuespecs.Percentage,
                localizer("Relative difference"),
                localizer(
                    "The thresholds are calculated by increasing or decreasing the predicted value by a percentage"
                ),
                rel_info,
            ),
            _get_level_computation_dropdown_choice(
                _PredictiveLevelDefinition.STDDEV.value,
                legacy_valuespecs.Float,
                localizer("Standard deviation difference"),
                localizer(
                    "The thresholds are calculated by increasing or decreasing the predicted value by a multiple of the standard deviation"
                ),
                stddev_info,
            ),
        ],
    )


def _get_predictive_levels_choice_element(
    form_spec: type[_TNumericSpec],
    to_convert: ruleset_api_v1.form_specs.PredictiveLevels,
    level_direction: _LevelDirection,
    unit: str,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.Dictionary:
    valuespec = type(_get_legacy_level_spec(form_spec, "", "", legacy_valuespecs.Sentinel()))

    if level_direction is _LevelDirection.UPPER:
        abs_info, rel_info, stddev_info, fixed_info = _get_level_computation_info(
            valuespec, to_convert, unit, "above", "least", "below", "low", localizer
        )
    elif level_direction is _LevelDirection.LOWER:
        abs_info, rel_info, stddev_info, fixed_info = _get_level_computation_info(
            valuespec, to_convert, unit, "below", "most", "above", "high", localizer
        )
    else:
        assert_never(level_direction)

    # This is a placeholder:
    # The backend uses this marker to inject a callback to get the prediction.
    # Its main purpose it to bind the host name and service description,
    # which are not known to the plugin.
    predictive_callback_key = "__get_predictive_levels__"

    predictive_elements: Sequence[tuple[str, legacy_valuespecs.ValueSpec]] = [
        (
            "period",
            legacy_valuespecs.DropdownChoice(
                choices=[
                    ("wday", localizer("Day of the week")),
                    ("day", localizer("Day of the month")),
                    ("hour", localizer("Hour of the day")),
                    ("minute", localizer("Minute of the hour")),
                ],
                title=localizer("Base prediction on"),
                help=localizer(
                    "Define the periodicity in which the repetition of the measured data is expected (monthly, weekly, daily or hourly)"
                ),
            ),
        ),
        (
            "horizon",
            legacy_valuespecs.Integer(
                title=localizer("Length of historic data to consider"),
                help=localizer(
                    "How many days in the past Checkmk should evaluate the measurement data"
                ),
                unit=localizer("days"),
                minvalue=1,
                default_value=90,
            ),
        ),
        (
            "levels",
            _get_level_computation_dropdown(valuespec, abs_info, rel_info, stddev_info, localizer),
        ),
        (
            "bound",
            legacy_valuespecs.Tuple(
                title=localizer("Fixed limits"),
                help=fixed_info.help,
                elements=[
                    _get_legacy_level_spec(
                        form_spec, fixed_info.warn, unit, legacy_valuespecs.Sentinel()
                    ),
                    _get_legacy_level_spec(
                        form_spec, fixed_info.crit, unit, legacy_valuespecs.Sentinel()
                    ),
                ],
            ),
        ),
        (predictive_callback_key, legacy_valuespecs.FixedValue(None)),
    ]
    return legacy_valuespecs.Dictionary(
        elements=predictive_elements,
        optional_keys=["bound"],
        ignored_keys=[predictive_callback_key],
        hidden_keys=[predictive_callback_key],
    )


class _LevelDynamicChoice(enum.StrEnum):
    NO_LEVELS = "no_levels"
    FIXED = "fixed"
    PREDICTIVE = "predictive"


def _get_level_dynamic(
    form_spec: type[_TNumericSpec],
    levels: tuple[
        ruleset_api_v1.form_specs.FixedLevels, ruleset_api_v1.form_specs.PredictiveLevels | None
    ]
    | None,
    level_direction: _LevelDirection,
    unit: str,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.CascadingDropdown:
    default_value = _LevelDynamicChoice.NO_LEVELS.value
    choices: list[tuple[str, str, legacy_valuespecs.ValueSpec]] = [
        (
            _LevelDynamicChoice.NO_LEVELS.value,
            localizer("No levels"),
            legacy_valuespecs.FixedValue(
                value=None,
                title=localizer("No levels"),
                totext=localizer("Do not impose levels, always be OK"),
            ),
        ),
    ]

    if levels is not None:
        default_value = _LevelDynamicChoice.FIXED.value
        choices.append(
            (
                _LevelDynamicChoice.FIXED.value,
                localizer("Fixed levels"),
                _get_fixed_levels_choice_element(
                    form_spec, levels[0], level_direction, unit, localizer
                ),
            )
        )
        if (predictive_levels := levels[1]) is not None:
            choices.append(
                (
                    _LevelDynamicChoice.PREDICTIVE.value,
                    localizer("Predictive levels (only on CMC)"),
                    _get_predictive_levels_choice_element(
                        form_spec,
                        predictive_levels,
                        level_direction,
                        unit,
                        localizer,
                    ),
                )
            )
    return legacy_valuespecs.CascadingDropdown(
        choices=choices,
        title=localizer("Upper levels")
        if level_direction is _LevelDirection.UPPER
        else localizer("Lower levels"),
        default_value=default_value,
    )


def _convert_to_legacy_levels(
    to_convert: ruleset_api_v1.form_specs.Levels, localizer: Callable[[str], str]
) -> legacy_valuespecs.Dictionary:
    unit = "" if to_convert.unit is None else to_convert.unit.localize(localizer)

    elements = [
        (
            "levels_lower",
            _get_level_dynamic(
                to_convert.form_spec, to_convert.lower, _LevelDirection.LOWER, unit, localizer
            ),
        ),
        (
            "levels_upper",
            _get_level_dynamic(
                to_convert.form_spec, to_convert.upper, _LevelDirection.UPPER, unit, localizer
            ),
        ),
    ]

    return legacy_valuespecs.Dictionary(
        title=_localize_optional(to_convert.title, localizer),
        elements=elements,
        required_keys=["levels_lower", "levels_upper"],
    )


def _convert_to_legacy_http_proxy(
    to_convert: ruleset_api_v1.form_specs.Proxy, localizer: Callable[[str], str]
) -> legacy_valuespecs.CascadingDropdown:
    allowed_schemas = {s.value for s in to_convert.allowed_schemas}

    def _global_proxy_choices() -> legacy_valuespecs.DropdownChoiceEntries:
        settings = legacy_config_domains.ConfigDomainCore().load()
        return [
            (p["ident"], p["title"])
            for p in settings.get("http_proxies", {}).values()
            if urllib.parse.urlparse(p["proxy_url"]).scheme in allowed_schemas
        ]

    return legacy_valuespecs.CascadingDropdown(
        title=ruleset_api_v1.Localizable("HTTP proxy").localize(localizer),
        default_value=("environment", "environment"),
        choices=[
            (
                "environment",
                ruleset_api_v1.Localizable("Use from environment").localize(localizer),
                legacy_valuespecs.FixedValue(
                    value="environment",
                    help=ruleset_api_v1.Localizable(
                        "Use the proxy settings from the environment variables. The variables <tt>NO_PROXY</tt>, "
                        "<tt>HTTP_PROXY</tt> and <tt>HTTPS_PROXY</tt> are taken into account during execution. "
                        "Have a look at the python requests module documentation for further information. Note "
                        "that these variables must be defined as a site-user in ~/etc/environment and that "
                        "this might affect other notification methods which also use the requests module."
                    ).localize(localizer),
                    totext=ruleset_api_v1.Localizable(
                        "Use proxy settings from the process environment. This is the default."
                    ).localize(localizer),
                ),
            ),
            (
                "no_proxy",
                ruleset_api_v1.Localizable("Connect without proxy").localize(localizer),
                legacy_valuespecs.FixedValue(
                    value=None,
                    totext=ruleset_api_v1.Localizable(
                        "Connect directly to the destination instead of using a proxy."
                    ).localize(localizer),
                ),
            ),
            (
                "global",
                ruleset_api_v1.Localizable("Use globally configured proxy").localize(localizer),
                legacy_valuespecs.DropdownChoice(
                    choices=_global_proxy_choices,
                    sorted=True,
                ),
            ),
            (
                "url",
                ruleset_api_v1.Localizable("Use explicit proxy settings").localize(localizer),
                legacy_valuespecs.Url(
                    title=ruleset_api_v1.Localizable("Proxy URL").localize(localizer),
                    default_scheme="http",
                    allowed_schemes=allowed_schemas,
                ),
            ),
        ],
        sorted=False,
    )


def _convert_to_legacy_checkbox(
    to_convert: ruleset_api_v1.form_specs.BooleanChoice, localizer: Callable[[str], str]
) -> legacy_valuespecs.Checkbox:
    checkbox_default: bool | legacy_valuespecs.Sentinel = (
        to_convert.prefill_value
        if to_convert.prefill_value is not None
        else legacy_valuespecs.DEF_VALUE
    )
    return legacy_valuespecs.Checkbox(
        label=_localize_optional(to_convert.label, localizer),
        title=_localize_optional(to_convert.title, localizer),
        help=_localize_optional(to_convert.help_text, localizer),
        default_value=checkbox_default,
    )
