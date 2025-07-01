#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import enum
import urllib.parse
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, assert_never, Literal, Self, TypeVar

from cmk.ccc.user import UserId
from cmk.ccc.version import Edition

from cmk.utils.password_store import ad_hoc_password_id
from cmk.utils.rulesets.definition import RuleGroup

import cmk.gui.graphing._valuespecs as legacy_graphing_valuespecs
from cmk.gui import inventory as legacy_inventory_groups
from cmk.gui import valuespec as legacy_valuespecs
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.converter import SimplePassword, Tuple
from cmk.gui.form_specs.private import (
    DictionaryExtended,
    LegacyValueSpec,
    ListExtended,
    ListOfStrings,
    MonitoredHostExtended,
    SingleChoiceExtended,
    StringAutocompleter,
    UserSelection,
)
from cmk.gui.userdb._user_selection import UserSelection as LegacyUserSelection
from cmk.gui.utils.autocompleter_config import AutocompleterConfig, ContextAutocompleterConfig
from cmk.gui.utils.rule_specs.loader import RuleSpec as APIV1RuleSpec
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import AjaxDropdownChoice, Transform
from cmk.gui.wato import _rulespec_groups as legacy_wato_groups
from cmk.gui.wato._check_mk_configuration import RulespecGroupAgent
from cmk.gui.watolib import config_domains as legacy_config_domains
from cmk.gui.watolib import rulespec_groups as legacy_rulespec_groups
from cmk.gui.watolib import rulespecs as legacy_rulespecs
from cmk.gui.watolib import timeperiods as legacy_timeperiods
from cmk.gui.watolib.password_store import IndividualOrStoredPassword
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    FormSpecDefinition,
    ManualCheckParameterRulespec,
    rulespec_group_registry,
    RulespecSubGroup,
)

from cmk.rulesets import v1 as ruleset_api_v1
from cmk.shared_typing.vue_formspec_components import ListOfStringsLayout

RulespecGroupMonitoringAgentsAgentPlugins: type[RulespecSubGroup] | None
RulespecGroupMonitoringAgentsLinuxUnixAgent: type[RulespecSubGroup] | None
RulespecGroupMonitoringAgentsWindowsAgent: type[RulespecSubGroup] | None

try:
    from cmk.gui.cee.agent_bakery import (  # type: ignore[no-redef, import-not-found, import-untyped, unused-ignore]  # pylint: disable=cmk-module-layer-violation
        RulespecGroupMonitoringAgentsAgentPlugins,
        RulespecGroupMonitoringAgentsLinuxUnixAgent,
        RulespecGroupMonitoringAgentsWindowsAgent,
    )
except ImportError:
    RulespecGroupMonitoringAgentsAgentPlugins = None
    RulespecGroupMonitoringAgentsLinuxUnixAgent = None
    RulespecGroupMonitoringAgentsWindowsAgent = None


@dataclass(frozen=True)
class FormSpecCallable:
    spec: Callable[[], ruleset_api_v1.form_specs.FormSpec[Any]]

    def __call__(self) -> ruleset_api_v1.form_specs.FormSpec:
        return self.spec()


GENERATED_GROUP_PREFIX = "gen-"

RULESET_DOC_REFERENCES_MAP = {
    RuleGroup.SpecialAgents("aws"): {
        DocReference.AWS: ruleset_api_v1.Title("Monitoring Amazon Web Services (AWS)")
    },
    RuleGroup.SpecialAgents("aws_status"): {
        DocReference.AWS: ruleset_api_v1.Title("Monitoring Amazon Web Services (AWS)")
    },
    RuleGroup.SpecialAgents("azure"): {
        DocReference.AZURE: ruleset_api_v1.Title("Monitoring Microsoft Azure")
    },
    RuleGroup.SpecialAgents("azure_status"): {
        DocReference.AZURE: ruleset_api_v1.Title("Monitoring Microsoft Azure")
    },
    RuleGroup.SpecialAgents("gcp"): {
        DocReference.GCP: ruleset_api_v1.Title("Monitoring Google Cloud Platform (GCP)")
    },
    RuleGroup.SpecialAgents("gcp_status"): {
        DocReference.GCP: ruleset_api_v1.Title("Monitoring Google Cloud Platform (GCP)")
    },
    RuleGroup.SpecialAgents("kube"): {
        DocReference.KUBERNETES: ruleset_api_v1.Title("Monitoring Kubernetes")
    },
    RuleGroup.SpecialAgents("prometheus"): {
        DocReference.PROMETHEUS: ruleset_api_v1.Title("Integrating Prometheus")
    },
    RuleGroup.SpecialAgents("vsphere"): {
        DocReference.VMWARE: ruleset_api_v1.Title("Monitoring VMWare ESXi")
    },
}


def _get_doc_references(
    ruleset_name: str, localizer: Callable[[str], str]
) -> dict[DocReference, str] | None:
    if (doc_ref_mapping := RULESET_DOC_REFERENCES_MAP.get(ruleset_name, None)) is None:
        return None
    return {
        doc_reference: title.localize(localizer) for doc_reference, title in doc_ref_mapping.items()
    }


def _localize_optional(
    to_localize: (
        ruleset_api_v1.Help
        | ruleset_api_v1.Message
        | ruleset_api_v1.Label
        | ruleset_api_v1.Title
        | None
    ),
    localizer: Callable[[str], str],
) -> str | None:
    return None if to_localize is None else to_localize.localize(localizer)


def convert_to_legacy_rulespec(
    to_convert: APIV1RuleSpec, edition_only: Edition, localizer: Callable[[str], str]
) -> legacy_rulespecs.Rulespec:
    match to_convert:
        case ruleset_api_v1.rule_specs.ActiveCheck():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_wato_groups.RulespecGroupActiveChecks,
                localizer,
                config_scope_prefix=RuleGroup.ActiveChecks,
            )
        case ruleset_api_v1.rule_specs.AgentAccess():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                RulespecGroupAgent,
                localizer,
            )
        case ruleset_api_v1.rule_specs.AgentConfig():
            return _convert_to_legacy_agent_config_rule_spec(
                to_convert, legacy_rulespec_groups.RulespecGroupMonitoringAgents, localizer
            )
        case ruleset_api_v1.rule_specs.CheckParameters():
            return _convert_to_legacy_check_parameter_rulespec(to_convert, edition_only, localizer)
        case ruleset_api_v1.rule_specs.EnforcedService():
            return _convert_to_legacy_manual_check_parameter_rulespec(
                to_convert, edition_only, localizer
            )
        case ruleset_api_v1.rule_specs.Host():
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
                legacy_wato_groups.RulespecGroupDiscoveryCheckParameters,
                localizer,
            )
        case ruleset_api_v1.rule_specs.Service():
            match to_convert.condition:
                case ruleset_api_v1.rule_specs.HostCondition():
                    return _convert_to_legacy_host_rule_spec_rulespec(
                        to_convert,
                        legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
                        localizer,
                    )
                case ruleset_api_v1.rule_specs.HostAndServiceCondition():
                    return _convert_to_legacy_service_rule_spec_rulespec(
                        to_convert,
                        localizer,
                    )
                case other:
                    assert_never(other)
        case ruleset_api_v1.rule_specs.SNMP():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_rulespec_groups.RulespecGroupAgentSNMP,
                localizer,
            )
        case ruleset_api_v1.rule_specs.SpecialAgent():
            return _convert_to_legacy_host_rule_spec_rulespec(
                to_convert,
                legacy_wato_groups.RulespecGroupDatasourcePrograms,
                localizer,
                config_scope_prefix=RuleGroup.SpecialAgents,
            )
        case other:
            assert_never(other)


def _convert_to_legacy_check_parameter_rulespec(
    to_convert: ruleset_api_v1.rule_specs.CheckParameters,
    edition_only: Edition,
    localizer: Callable[[str], str],
) -> CheckParameterRulespecWithItem | CheckParameterRulespecWithoutItem:
    convert_condition = to_convert.condition
    if isinstance(convert_condition, ruleset_api_v1.rule_specs.HostAndItemCondition):
        item_spec, item_form_spec = _get_item_spec_maker(convert_condition, localizer)
        return CheckParameterRulespecWithItem(
            check_group_name=to_convert.name,
            title=(
                None if to_convert.title is None else partial(to_convert.title.localize, localizer)
            ),
            group=_convert_to_legacy_rulespec_group(
                legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
                to_convert.topic,
                localizer,
            ),
            item_spec=item_spec,
            match_type="dict",
            parameter_valuespec=partial(
                convert_to_legacy_valuespec, FormSpecCallable(to_convert.parameter_form), localizer
            ),
            is_deprecated=to_convert.is_deprecated,
            create_manual_check=False,
            # weird field since the CME, as well as the CSE is based on a CCE, but we currently only
            # want to mark rulespecs that are available in both the CCE and CME as such
            is_cloud_and_managed_edition_only=edition_only is Edition.CCE,
            form_spec_definition=FormSpecDefinition(
                to_convert.parameter_form, lambda: item_form_spec
            ),
        )
    return CheckParameterRulespecWithoutItem(
        check_group_name=to_convert.name,
        title=partial(to_convert.title.localize, localizer),
        group=_convert_to_legacy_rulespec_group(
            legacy_rulespec_groups.RulespecGroupMonitoringConfiguration, to_convert.topic, localizer
        ),
        match_type="dict",
        parameter_valuespec=partial(
            convert_to_legacy_valuespec, FormSpecCallable(to_convert.parameter_form), localizer
        ),
        create_manual_check=False,
        is_cloud_and_managed_edition_only=edition_only is Edition.CCE,
        form_spec_definition=FormSpecDefinition(to_convert.parameter_form, None),
    )


def _convert_to_legacy_manual_check_parameter_rulespec(
    to_convert: ruleset_api_v1.rule_specs.EnforcedService,
    edition_only: Edition,
    localizer: Callable[[str], str],
) -> ManualCheckParameterRulespec:
    match to_convert.condition:
        case ruleset_api_v1.rule_specs.HostCondition():
            item_spec = None
            item_form_spec = None
        case ruleset_api_v1.rule_specs.HostAndItemCondition():
            item_spec, item_as_form_spec = _get_item_spec_maker(to_convert.condition, localizer)

            def wrapped_value():
                return item_as_form_spec

            item_form_spec = wrapped_value
        case other:
            assert_never(other)

    return ManualCheckParameterRulespec(
        group=_convert_to_legacy_rulespec_group(
            legacy_rulespecs.RulespecGroupEnforcedServices, to_convert.topic, localizer
        ),
        check_group_name=to_convert.name,
        parameter_valuespec=(
            partial(
                convert_to_legacy_valuespec, FormSpecCallable(to_convert.parameter_form), localizer
            )
            if to_convert.parameter_form is not None
            else None
        ),
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=False,
        match_type="all",
        item_spec=item_spec,
        is_cloud_and_managed_edition_only=edition_only is Edition.CCE,
        form_spec_definition=None
        if to_convert.parameter_form is None
        else FormSpecDefinition(to_convert.parameter_form, item_form_spec),
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
        return _custom_to_builtin_legacy_group(
            legacy_main_group, topic_to_convert
        ) or _convert_to_custom_group(legacy_main_group, topic_to_convert.title, localizer)
    raise ValueError(topic_to_convert)


def _convert_to_legacy_match_type(
    to_convert: (
        ruleset_api_v1.rule_specs.ActiveCheck
        | ruleset_api_v1.rule_specs.AgentConfig
        | ruleset_api_v1.rule_specs.AgentAccess
        | ruleset_api_v1.rule_specs.Host
        | ruleset_api_v1.rule_specs.NotificationParameters
        | ruleset_api_v1.rule_specs.InventoryParameters
        | ruleset_api_v1.rule_specs.DiscoveryParameters
        | ruleset_api_v1.rule_specs.Service
        | ruleset_api_v1.rule_specs.SNMP
        | ruleset_api_v1.rule_specs.SpecialAgent
    ),
) -> Literal["first", "all", "list", "dict", "varies"]:
    match to_convert:
        case ruleset_api_v1.rule_specs.ActiveCheck():
            return "all"
        case ruleset_api_v1.rule_specs.SpecialAgent():
            return "first"
        case (
            ruleset_api_v1.rule_specs.AgentConfig()
            | ruleset_api_v1.rule_specs.InventoryParameters()
            | ruleset_api_v1.rule_specs.NotificationParameters()
        ):
            return "dict"
        case ruleset_api_v1.rule_specs.DiscoveryParameters():
            return "varies"
        case other:
            return "dict" if other.eval_type == ruleset_api_v1.rule_specs.EvalType.MERGE else "all"


def _convert_to_legacy_host_rule_spec_rulespec(
    to_convert: (
        ruleset_api_v1.rule_specs.ActiveCheck
        | ruleset_api_v1.rule_specs.AgentAccess
        | ruleset_api_v1.rule_specs.Host
        | ruleset_api_v1.rule_specs.NotificationParameters
        | ruleset_api_v1.rule_specs.InventoryParameters
        | ruleset_api_v1.rule_specs.DiscoveryParameters
        | ruleset_api_v1.rule_specs.Service
        | ruleset_api_v1.rule_specs.SNMP
        | ruleset_api_v1.rule_specs.SpecialAgent
    ),
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    localizer: Callable[[str], str],
    config_scope_prefix: Callable[[str | None], str] = lambda x: x or "",
) -> legacy_rulespecs.HostRulespec:
    return legacy_rulespecs.HostRulespec(
        group=_convert_to_legacy_rulespec_group(legacy_main_group, to_convert.topic, localizer),
        name=config_scope_prefix(to_convert.name),
        valuespec=partial(
            convert_to_legacy_valuespec, FormSpecCallable(to_convert.parameter_form), localizer
        ),
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=to_convert.is_deprecated,
        match_type=_convert_to_legacy_match_type(to_convert),
        doc_references=_get_doc_references(config_scope_prefix(to_convert.name), localizer),
        form_spec_definition=FormSpecDefinition(to_convert.parameter_form, None),
    )


def _convert_to_legacy_agent_config_rule_spec(
    to_convert: ruleset_api_v1.rule_specs.AgentConfig,
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    localizer: Callable[[str], str],
) -> legacy_rulespecs.HostRulespec:
    return legacy_rulespecs.HostRulespec(
        group=_convert_to_legacy_rulespec_group(legacy_main_group, to_convert.topic, localizer),
        name=RuleGroup.AgentConfig(to_convert.name),
        valuespec=partial(
            _transform_agent_config_rule_spec_match_type,
            FormSpecCallable(to_convert.parameter_form),
            localizer,
        ),
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=to_convert.is_deprecated,
        match_type=_convert_to_legacy_match_type(to_convert),
        doc_references=_get_doc_references(RuleGroup.AgentConfig(to_convert.name), localizer),
        form_spec_definition=FormSpecDefinition(to_convert.parameter_form, None),
    )


def _add_agent_config_match_type_key(value: object) -> object:
    if isinstance(value, dict):
        value["cmk-match-type"] = "dict"
        return value

    raise TypeError(value)


def _remove_agent_config_match_type_key(value: object) -> object:
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if k != "cmk-match-type"}

    raise TypeError(value)


def _transform_agent_config_rule_spec_match_type(
    parameter_form: FormSpecCallable, localizer: Callable[[str], str]
) -> legacy_valuespecs.ValueSpec:
    legacy_vs = convert_to_legacy_valuespec(parameter_form, localizer)
    inner_transform = (
        legacy_vs if isinstance(legacy_vs, Transform) and parameter_form().migrate else None
    )
    if not inner_transform:
        return Transform(
            legacy_vs,
            forth=_remove_agent_config_match_type_key,
            back=_add_agent_config_match_type_key,
        )

    # We cannot simply wrap legacy_vs into a Transform to handle the match type key. Wrapping a
    # valuespec into a Transform results in the following order of transformations:
    # 1. outer transform   (_remove_agent_config_match_type_key)
    # 2. inner transforms
    # _remove_agent_config_match_type_key fails for non-dictionaries, however, it is the job of the
    # inner transforms to migrate to a dictionairy in case of a migration from a non-dictionary
    # rule spec.
    return Transform(
        valuespec=Transform(
            inner_transform._valuespec,
            to_valuespec=_remove_agent_config_match_type_key,
            from_valuespec=_add_agent_config_match_type_key,
        ),
        to_valuespec=inner_transform.to_valuespec,
        from_valuespec=inner_transform.from_valuespec,
    )


def _convert_to_legacy_service_rule_spec_rulespec(
    to_convert: ruleset_api_v1.rule_specs.Service,
    localizer: Callable[[str], str],
    config_scope_prefix: Callable[[str | None], str] = lambda x: x or "",
) -> legacy_rulespecs.ServiceRulespec:
    return legacy_rulespecs.ServiceRulespec(
        group=_convert_to_legacy_rulespec_group(
            legacy_rulespec_groups.RulespecGroupMonitoringConfiguration, to_convert.topic, localizer
        ),
        item_type="service",
        name=config_scope_prefix(to_convert.name),
        valuespec=partial(
            convert_to_legacy_valuespec, FormSpecCallable(to_convert.parameter_form), localizer
        ),
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=to_convert.is_deprecated,
        match_type=(
            "dict" if to_convert.eval_type == ruleset_api_v1.rule_specs.EvalType.MERGE else "all"
        ),
        doc_references=_get_doc_references(config_scope_prefix(to_convert.name), localizer),
        form_spec_definition=FormSpecDefinition(to_convert.parameter_form, None),
    )


def _get_builtin_legacy_sub_group_with_main_group(
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    topic_to_convert: ruleset_api_v1.rule_specs.Topic,
    localizer: Callable[[str], str],
) -> type[legacy_rulespecs.RulespecBaseGroup]:
    match topic_to_convert:
        case ruleset_api_v1.rule_specs.Topic.APPLICATIONS:
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersApplications
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsApps
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            return _to_generated_builtin_sub_group(legacy_main_group, "Applications", localizer)
        case ruleset_api_v1.rule_specs.Topic.CACHING_MESSAGE_QUEUES:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            return _to_generated_builtin_sub_group(
                legacy_main_group, "Caching / Message Queues", localizer
            )
        case ruleset_api_v1.rule_specs.Topic.CLOUD:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupVMCloudContainer
            return _to_generated_builtin_sub_group(legacy_main_group, "Cloud", localizer)
        case ruleset_api_v1.rule_specs.Topic.CONFIGURATION_DEPLOYMENT:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            return _to_generated_builtin_sub_group(
                legacy_main_group, "Configuration & Deployment", localizer
            )
        case ruleset_api_v1.rule_specs.Topic.DATABASES:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
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
            if legacy_main_group == legacy_wato_groups.RulespecGroupDiscoveryCheckParameters:
                return legacy_wato_groups.RulespecGroupCheckParametersDiscovery
            return _to_generated_builtin_sub_group(legacy_main_group, "General", localizer)
        case ruleset_api_v1.rule_specs.Topic.ENVIRONMENTAL:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersEnvironment
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesEnvironment
            return _to_generated_builtin_sub_group(legacy_main_group, "Environmental", localizer)
        case ruleset_api_v1.rule_specs.Topic.LINUX:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsLinuxUnixAgent is not None
            ):
                return RulespecGroupMonitoringAgentsLinuxUnixAgent
            return _to_generated_builtin_sub_group(legacy_main_group, "Linux", localizer)
        case ruleset_api_v1.rule_specs.Topic.NETWORKING:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersNetworking
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesNetworking
            return _to_generated_builtin_sub_group(legacy_main_group, "Networking", localizer)
        case ruleset_api_v1.rule_specs.Topic.MIDDLEWARE:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            return _to_generated_builtin_sub_group(legacy_main_group, "Middleware", localizer)
        case ruleset_api_v1.rule_specs.Topic.NOTIFICATIONS:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_rulespec_groups.RulespecGroupMonitoringConfigurationNotifications
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupHostsMonitoringRules:
                return legacy_rulespec_groups.RulespecGroupHostsMonitoringRulesNotifications
            return _to_generated_builtin_sub_group(legacy_main_group, "Notifications", localizer)
        case ruleset_api_v1.rule_specs.Topic.OPERATING_SYSTEM:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersOperatingSystem
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesOperatingSystem
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsOS
            return _to_generated_builtin_sub_group(legacy_main_group, "Operating System", localizer)
        case ruleset_api_v1.rule_specs.Topic.PERIPHERALS:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersPrinters
            return _to_generated_builtin_sub_group(legacy_main_group, "Peripherals", localizer)
        case ruleset_api_v1.rule_specs.Topic.POWER:
            return _to_generated_builtin_sub_group(legacy_main_group, "Power", localizer)
        case ruleset_api_v1.rule_specs.Topic.SERVER_HARDWARE:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersHardware
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesHardware
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsHardware
            return _to_generated_builtin_sub_group(legacy_main_group, "Server hardware", localizer)
        case ruleset_api_v1.rule_specs.Topic.STORAGE:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersStorage
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesStorage
            return _to_generated_builtin_sub_group(legacy_main_group, "Storage", localizer)
        case ruleset_api_v1.rule_specs.Topic.SYNTHETIC_MONITORING:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            return _to_generated_builtin_sub_group(
                legacy_main_group, "Synthetic Monitoring", localizer
            )
        case ruleset_api_v1.rule_specs.Topic.VIRTUALIZATION:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsAgentPlugins is not None
            ):
                return RulespecGroupMonitoringAgentsAgentPlugins
            if legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringConfiguration:
                return legacy_wato_groups.RulespecGroupCheckParametersVirtualization
            if legacy_main_group == legacy_rulespecs.RulespecGroupEnforcedServices:
                return legacy_rulespec_groups.RulespecGroupEnforcedServicesVirtualization
            if legacy_main_group == legacy_wato_groups.RulespecGroupDatasourcePrograms:
                return legacy_wato_groups.RulespecGroupDatasourceProgramsContainer
            return _to_generated_builtin_sub_group(legacy_main_group, "Virtualization", localizer)
        case ruleset_api_v1.rule_specs.Topic.WINDOWS:
            if (
                legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
                and RulespecGroupMonitoringAgentsWindowsAgent is not None
            ):
                return RulespecGroupMonitoringAgentsWindowsAgent
            return _to_generated_builtin_sub_group(legacy_main_group, "Windows", localizer)
        case other:
            assert_never(other)

    raise NotImplementedError(topic_to_convert)


def _custom_to_builtin_legacy_group(
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    custom_topic_to_convert: ruleset_api_v1.rule_specs.CustomTopic,
) -> type[legacy_rulespecs.RulespecBaseGroup] | None:
    if custom_topic_to_convert == ruleset_api_v1.rule_specs.CustomTopic(
        ruleset_api_v1.Title("Linux/UNIX agent options")
    ):
        if (
            legacy_main_group == legacy_rulespec_groups.RulespecGroupMonitoringAgents
            and RulespecGroupMonitoringAgentsLinuxUnixAgent is not None
        ):
            return RulespecGroupMonitoringAgentsLinuxUnixAgent
    return None


def _convert_to_custom_group(
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    title: ruleset_api_v1.Title,
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
    title = ruleset_api_v1.Title(raw_title)
    return _convert_to_custom_group(legacy_main_group, title, localizer)


@dataclass(frozen=True)
class _LegacyDictKeyProps:
    required: list[str]
    hidden: list[str]

    @classmethod
    def from_elements(cls, elements: Mapping[str, ruleset_api_v1.form_specs.DictElement]) -> Self:
        return cls(
            required=[key for key, element in elements.items() if element.required],
            hidden=[key for key, element in elements.items() if element.render_only],
        )


def _convert_to_inner_legacy_valuespec(
    to_convert: ruleset_api_v1.form_specs.FormSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.ValueSpec:
    match to_convert:
        case ruleset_api_v1.form_specs.Integer():
            return _convert_to_legacy_integer(to_convert, localizer)

        case ruleset_api_v1.form_specs.Float():
            return _convert_to_legacy_float(to_convert, localizer)

        case ruleset_api_v1.form_specs.DataSize():
            return _convert_to_legacy_datasize(to_convert, localizer)

        case ruleset_api_v1.form_specs.Percentage():
            return _convert_to_legacy_percentage(to_convert, localizer)

        case ruleset_api_v1.form_specs.String():
            return _convert_to_legacy_text_input(to_convert, localizer)

        case ruleset_api_v1.form_specs.RegularExpression():
            return _convert_to_legacy_regular_expression(to_convert, localizer)

        case ruleset_api_v1.form_specs.Dictionary() | DictionaryExtended():
            return _convert_to_legacy_dictionary(to_convert, localizer)

        case ruleset_api_v1.form_specs.SingleChoice() | SingleChoiceExtended():
            return _convert_to_legacy_dropdown_choice(to_convert, localizer)

        case ruleset_api_v1.form_specs.CascadingSingleChoice():
            return _convert_to_legacy_cascading_dropdown(to_convert, localizer)

        case ruleset_api_v1.form_specs.ServiceState():
            return _convert_to_legacy_monitoring_state(to_convert, localizer)

        case ruleset_api_v1.form_specs.HostState():
            return _convert_to_legacy_host_state(to_convert, localizer)

        case ruleset_api_v1.form_specs.List() | ListExtended():
            return _convert_to_legacy_list(to_convert, localizer)

        case ListOfStrings():
            return _convert_to_legacy_list_of_strings(to_convert, localizer)

        case ruleset_api_v1.form_specs.FixedValue():
            return _convert_to_legacy_fixed_value(to_convert, localizer)

        case ruleset_api_v1.form_specs.TimeSpan():
            return _convert_to_legacy_time_span(to_convert, localizer)

        case ruleset_api_v1.form_specs.Levels() | ruleset_api_v1.form_specs.SimpleLevels():
            return _convert_to_legacy_levels(to_convert, localizer)

        case ruleset_api_v1.form_specs.BooleanChoice():
            return _convert_to_legacy_checkbox(to_convert, localizer)

        case ruleset_api_v1.form_specs.FileUpload():
            return _convert_to_legacy_file_upload(to_convert, localizer)

        case ruleset_api_v1.form_specs.Proxy():
            return _convert_to_legacy_http_proxy(to_convert, localizer)

        case ruleset_api_v1.form_specs.Metric():
            return _convert_to_legacy_metric_name(to_convert, localizer)

        case ruleset_api_v1.form_specs.MonitoredHost() | MonitoredHostExtended():
            return _convert_to_legacy_monitored_host_name(to_convert, localizer)

        case ruleset_api_v1.form_specs.MonitoredService():
            return _convert_to_legacy_monitored_service_description(to_convert, localizer)

        case ruleset_api_v1.form_specs.Password():
            return _convert_to_legacy_individual_or_stored_password(to_convert, localizer)

        case ruleset_api_v1.form_specs.MultipleChoice():
            return _convert_to_legacy_list_choice_match_type(to_convert, localizer)

        case ruleset_api_v1.form_specs.MultilineText():
            return _convert_to_legacy_text_area(to_convert, localizer)

        case ruleset_api_v1.form_specs.TimePeriod():
            return _convert_to_legacy_timeperiod_selection(to_convert, localizer)

        case Tuple():
            return _convert_to_legacy_tuple(to_convert, localizer)

        case SimplePassword():
            return _convert_to_legacy_password(to_convert, localizer)

        case LegacyValueSpec():
            return to_convert.valuespec

        case UserSelection():
            return _convert_to_legacy_user_selection(to_convert, localizer)

        case StringAutocompleter():
            return _convert_to_legacy_autocompleter(to_convert, localizer)

        case other:
            raise NotImplementedError(other)


def convert_to_legacy_valuespec(
    to_convert: ruleset_api_v1.form_specs.FormSpec | FormSpecCallable,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.ValueSpec:
    if isinstance(to_convert, FormSpecCallable):
        to_convert = to_convert()

    def allow_empty_value_wrapper(
        update_func: Callable[[object], object],
    ) -> Callable[[object], object]:
        def wrapper(v: object) -> object:
            try:
                return update_func(v)
            except Exception:
                if v is None:
                    return v
                raise

        return wrapper

    if to_convert.migrate is not None:
        migrate_func = (
            allow_empty_value_wrapper(to_convert.migrate)
            if isinstance(to_convert, ruleset_api_v1.form_specs.CascadingSingleChoice)
            else to_convert.migrate
        )
        return legacy_valuespecs.Transform(
            valuespec=_convert_to_inner_legacy_valuespec(to_convert, localizer),
            forth=migrate_func,
        )
    return _convert_to_inner_legacy_valuespec(to_convert, localizer)


def _get_allow_empty_conf(
    to_convert: ruleset_api_v1.form_specs.FormSpec, localizer: Callable[[str], str]
) -> Mapping[str, bool | str]:
    min_len_validator = None
    if to_convert.custom_validate is not None:
        min_len_validator = next(
            (
                val
                for val in to_convert.custom_validate
                if isinstance(val, ruleset_api_v1.form_specs.validators.LengthInRange)
                and val.range[0] is not None
            ),
            None,
        )

    if isinstance(min_len_validator, ruleset_api_v1.form_specs.validators.LengthInRange):
        return {"allow_empty": False, "empty_text": min_len_validator.error_msg.localize(localizer)}
    return {"allow_empty": True}


def _convert_to_legacy_integer(
    to_convert: ruleset_api_v1.form_specs.Integer, localizer: Callable[[str], str]
) -> legacy_valuespecs.Integer:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "unit": to_convert.unit_symbol,
    }

    match to_convert.prefill:
        case ruleset_api_v1.form_specs.DefaultValue():
            converted_kwargs["default_value"] = to_convert.prefill.value
        case ruleset_api_v1.form_specs.InputHint():
            pass  # not implemented for legacy VS

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Integer(**converted_kwargs)


def _convert_to_legacy_float(
    to_convert: ruleset_api_v1.form_specs.Float, localizer: Callable[[str], str]
) -> legacy_valuespecs.Float:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "display_format": "%r",
        "unit": to_convert.unit_symbol,
    }

    match to_convert.prefill:
        case ruleset_api_v1.form_specs.DefaultValue():
            converted_kwargs["default_value"] = to_convert.prefill.value
        case ruleset_api_v1.form_specs.InputHint():
            pass  # not implemented for legacy VS

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Float(**converted_kwargs)


def _convert_to_legacy_binary_unit(
    unit: ruleset_api_v1.form_specs.SIMagnitude | ruleset_api_v1.form_specs.IECMagnitude,
) -> legacy_valuespecs.LegacyBinaryUnit:
    match unit:
        case ruleset_api_v1.form_specs.SIMagnitude.BYTE:
            return legacy_valuespecs.LegacyBinaryUnit.Byte
        case ruleset_api_v1.form_specs.SIMagnitude.KILO:
            return legacy_valuespecs.LegacyBinaryUnit.KB
        case ruleset_api_v1.form_specs.SIMagnitude.MEGA:
            return legacy_valuespecs.LegacyBinaryUnit.MB
        case ruleset_api_v1.form_specs.SIMagnitude.GIGA:
            return legacy_valuespecs.LegacyBinaryUnit.GB
        case ruleset_api_v1.form_specs.SIMagnitude.TERA:
            return legacy_valuespecs.LegacyBinaryUnit.TB
        case ruleset_api_v1.form_specs.SIMagnitude.PETA:
            return legacy_valuespecs.LegacyBinaryUnit.PB
        case ruleset_api_v1.form_specs.SIMagnitude.EXA:
            return legacy_valuespecs.LegacyBinaryUnit.EB
        case ruleset_api_v1.form_specs.SIMagnitude.ZETTA:
            return legacy_valuespecs.LegacyBinaryUnit.ZB
        case ruleset_api_v1.form_specs.SIMagnitude.YOTTA:
            return legacy_valuespecs.LegacyBinaryUnit.YB

        case ruleset_api_v1.form_specs.IECMagnitude.BYTE:
            return legacy_valuespecs.LegacyBinaryUnit.Byte
        case ruleset_api_v1.form_specs.IECMagnitude.KIBI:
            return legacy_valuespecs.LegacyBinaryUnit.KiB
        case ruleset_api_v1.form_specs.IECMagnitude.MEBI:
            return legacy_valuespecs.LegacyBinaryUnit.MiB
        case ruleset_api_v1.form_specs.IECMagnitude.GIBI:
            return legacy_valuespecs.LegacyBinaryUnit.GiB
        case ruleset_api_v1.form_specs.IECMagnitude.TEBI:
            return legacy_valuespecs.LegacyBinaryUnit.TiB
        case ruleset_api_v1.form_specs.IECMagnitude.PEBI:
            return legacy_valuespecs.LegacyBinaryUnit.PiB
        case ruleset_api_v1.form_specs.IECMagnitude.EXBI:
            return legacy_valuespecs.LegacyBinaryUnit.EiB
        case ruleset_api_v1.form_specs.IECMagnitude.ZEBI:
            return legacy_valuespecs.LegacyBinaryUnit.ZiB
        case ruleset_api_v1.form_specs.IECMagnitude.YOBI:
            return legacy_valuespecs.LegacyBinaryUnit.YiB


def _convert_to_legacy_datasize(
    to_convert: ruleset_api_v1.form_specs.DataSize, localizer: Callable[[str], str]
) -> legacy_valuespecs.LegacyDataSize:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "units": [
            _convert_to_legacy_binary_unit(magnitude)
            for magnitude in to_convert.displayed_magnitudes
        ],
    }

    match to_convert.prefill:
        case ruleset_api_v1.form_specs.DefaultValue():
            converted_kwargs["default_value"] = to_convert.prefill.value
        case ruleset_api_v1.form_specs.InputHint():
            pass  # not implemented for legacy VS

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.LegacyDataSize(**converted_kwargs)


def _convert_to_legacy_percentage(
    to_convert: ruleset_api_v1.form_specs.Percentage, localizer: Callable[[str], str]
) -> legacy_valuespecs.Percentage:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "display_format": "%r",
        "minvalue": None,
        "maxvalue": None,
    }

    match to_convert.prefill:
        case ruleset_api_v1.form_specs.DefaultValue():
            converted_kwargs["default_value"] = to_convert.prefill.value
        case ruleset_api_v1.form_specs.InputHint():
            pass  # not implemented for legacy VS

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Percentage(**converted_kwargs)


def _convert_to_legacy_text_input(
    to_convert: ruleset_api_v1.form_specs.String, localizer: Callable[[str], str]
) -> legacy_valuespecs.TextInput:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        **_get_allow_empty_conf(to_convert, localizer),
    }

    help_text = _localize_optional(to_convert.help_text, localizer)
    if to_convert.macro_support:
        macros_help_text = (
            "This field supports the use of macros. "
            "The corresponding plug-in replaces the macros with the actual values."
        )
        localized_text = ruleset_api_v1.Help(macros_help_text).localize(localizer)
        converted_kwargs["help"] = f"{help_text} {localized_text}" if help_text else localized_text
    else:
        converted_kwargs["help"] = help_text

    match to_convert.prefill:
        case ruleset_api_v1.form_specs.DefaultValue():
            converted_kwargs["default_value"] = to_convert.prefill.value
        case ruleset_api_v1.form_specs.InputHint():
            converted_kwargs["placeholder"] = to_convert.prefill.value

    match to_convert.field_size:
        case ruleset_api_v1.form_specs.FieldSize.SMALL:
            converted_kwargs["size"] = 7
        case ruleset_api_v1.form_specs.FieldSize.MEDIUM:
            converted_kwargs["size"] = 35
        case ruleset_api_v1.form_specs.FieldSize.LARGE:
            converted_kwargs["size"] = 100

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.TextInput(**converted_kwargs)


def _convert_to_legacy_regular_expression(
    to_convert: ruleset_api_v1.form_specs.RegularExpression, localizer: Callable[[str], str]
) -> legacy_valuespecs.RegExp:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        **_get_allow_empty_conf(to_convert, localizer),
    }

    match to_convert.prefill:
        case ruleset_api_v1.form_specs.InputHint():
            converted_kwargs["placeholder"] = to_convert.prefill.value
        case ruleset_api_v1.form_specs.DefaultValue():
            converted_kwargs["default_value"] = to_convert.prefill.value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    match to_convert.predefined_help_text:
        case ruleset_api_v1.form_specs.MatchingScope.PREFIX:
            mode: Literal["infix", "prefix", "complete"] = legacy_valuespecs.RegExp.prefix
        case ruleset_api_v1.form_specs.MatchingScope.INFIX:
            mode = legacy_valuespecs.RegExp.infix
        case ruleset_api_v1.form_specs.MatchingScope.FULL:
            mode = legacy_valuespecs.RegExp.complete
        case other_match:
            assert_never(other_match)

    return legacy_valuespecs.RegExp(mode=mode, case_sensitive=True, **converted_kwargs)


def _get_dict_group_key(dict_group: ruleset_api_v1.form_specs.DictGroup) -> str:
    """Strip dict group down to html-id friendly string."""
    return "".join(filter(str.isalnum, repr(dict_group)))


def _get_group_keys(
    dict_elements: Mapping[str, ruleset_api_v1.form_specs.DictElement],
) -> Sequence[str]:
    return [
        _get_dict_group_key(elem.group)
        for elem in dict_elements.values()
        if not isinstance(elem.group, ruleset_api_v1.form_specs.NoGroup)
    ]


def _make_group_keys_dict(
    dict_elements: Mapping[str, ruleset_api_v1.form_specs.DictElement],
) -> dict:
    # to render the groups in a nicer way the group names are required keys, so have to exist per
    # default
    return {key: {} for key in _get_group_keys(dict_elements)}


def _get_packed_value(
    nested_form: ruleset_api_v1.form_specs.FormSpec,
    value_to_pack: object,
    packed_dict: dict,
) -> object:
    match nested_form, value_to_pack:
        case DictionaryExtended() as dict_form, dict() as dict_to_pack:
            return _pack_dict_groups(
                dict_form.elements, dict_form.ignored_elements, dict_to_pack, packed_dict
            )
        case ruleset_api_v1.form_specs.Dictionary() as dict_form, dict() as dict_to_pack:
            return _pack_dict_groups(
                dict_form.elements, dict_form.ignored_elements, dict_to_pack, packed_dict
            )
        case _:
            return value_to_pack


def _pack_dict_groups(
    dict_elements: Mapping[str, ruleset_api_v1.form_specs.DictElement],
    ignored_elements: Sequence[str],
    dict_to_pack: Mapping[str, object],
    packed_dict: dict,
) -> Mapping[str, object]:
    if not set(_get_group_keys(dict_elements)).isdisjoint(
        dict_to_pack.keys()
    ):  # already transformed
        return dict_to_pack

    for key_to_pack, value_to_pack in dict_to_pack.items():
        if key_to_pack in ignored_elements:
            packed_dict[key_to_pack] = value_to_pack
            continue

        nested_packed_dict = {}
        if isinstance(
            (nested_form := dict_elements[key_to_pack].parameter_form),
            ruleset_api_v1.form_specs.Dictionary | DictionaryExtended,
        ):
            # handle innermost migrations
            if nested_form.migrate is not None:
                value_to_pack = nested_form.migrate(value_to_pack)
            nested_packed_dict = _make_group_keys_dict(nested_form.elements)

        if isinstance(
            (group := dict_elements[key_to_pack].group), ruleset_api_v1.form_specs.NoGroup
        ):
            packed_dict[key_to_pack] = _get_packed_value(
                nested_form, value_to_pack, nested_packed_dict
            )
        else:
            packed_dict[_get_dict_group_key(group)][key_to_pack] = _get_packed_value(
                nested_form, value_to_pack, nested_packed_dict
            )
    return packed_dict


def _transform_dict_groups_forth(
    dict_elements: Mapping[str, ruleset_api_v1.form_specs.DictElement],
    ignored_elements: Sequence[str],
) -> Callable[[Mapping[str, object] | None], Mapping[str, object] | None]:
    def _forth(value: Mapping[str, object] | None) -> Mapping[str, object] | None:
        if value is None:
            return value

        return _pack_dict_groups(
            dict_elements, ignored_elements, value, _make_group_keys_dict(dict_elements)
        )

    return _forth


def _get_unpacked_value(
    nested_form: ruleset_api_v1.form_specs.FormSpec, value_to_unpack: object
) -> object:
    match nested_form, value_to_unpack:
        case DictionaryExtended() as dict_form, dict() as dict_to_unpack:
            return _unpack_dict_group(
                dict_form.elements, dict_form.ignored_elements, dict_to_unpack
            )
        case ruleset_api_v1.form_specs.Dictionary() as dict_form, dict() as dict_to_unpack:
            return _unpack_dict_group(
                dict_form.elements, dict_form.ignored_elements, dict_to_unpack
            )
        case _:
            return value_to_unpack


def _unpack_dict_group(
    dict_elements: Mapping[str, ruleset_api_v1.form_specs.DictElement],
    ignored_elements: Sequence[str],
    dict_to_unpack: Mapping[str, object],
) -> Mapping[str, object]:
    if not isinstance(dict_to_unpack, dict):
        return dict_to_unpack

    unpacked_dict = {}
    for key_to_unpack, value_to_unpack in dict_to_unpack.items():
        if key_to_unpack in ignored_elements:
            unpacked_dict[key_to_unpack] = value_to_unpack
            continue

        if key_to_unpack in _get_group_keys(dict_elements):
            for grouped_key_to_unpack, grouped_value_to_unpack in value_to_unpack.items():
                unpacked_dict[grouped_key_to_unpack] = _get_unpacked_value(
                    dict_elements[grouped_key_to_unpack].parameter_form, grouped_value_to_unpack
                )
        else:
            unpacked_dict[key_to_unpack] = _get_unpacked_value(
                dict_elements[key_to_unpack].parameter_form, value_to_unpack
            )
    return unpacked_dict


def _transform_dict_group_back(
    dict_elements: Mapping[str, ruleset_api_v1.form_specs.DictElement],
    ignored_elements: Sequence[str],
) -> Callable[[Mapping[str, object] | None], Mapping[str, object] | None]:
    def _back(value: Mapping[str, object] | None) -> Mapping[str, object] | None:
        if value is None:
            return value
        return _unpack_dict_group(dict_elements, ignored_elements, value)

    return _back


def _convert_to_dict_legacy_validation(
    v1_validate_funcs: Iterable[Callable[[Mapping[str, object]], object]],
    dict_elements: Mapping[str, ruleset_api_v1.form_specs.DictElement],
    ignore_elements: Sequence[str],
    localizer: Callable[[str], str],
) -> Callable[[Mapping[str, object], str], None]:
    def wrapper(value: Mapping[str, object], var_prefix: str) -> None:
        unpacked_value = _unpack_dict_group(dict_elements, ignore_elements, value)
        try:
            _ = [v1_validate_func(unpacked_value) for v1_validate_func in v1_validate_funcs]
        except ruleset_api_v1.form_specs.validators.ValidationError as e:
            raise MKUserError(var_prefix, e.message.localize(localizer))

    return wrapper


def _convert_to_legacy_dictionary(
    to_convert: ruleset_api_v1.form_specs.Dictionary | DictionaryExtended,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.Transform | legacy_valuespecs.Dictionary:
    ungrouped_element_key_props, ungrouped_elements = _get_ungrouped_elements(
        to_convert.elements, localizer
    )
    grouped_elements_map, hidden_group_keys = _group_elements(to_convert.elements, localizer)
    required_group_keys = set(grouped_elements_map.keys()) - hidden_group_keys

    default_keys: list[str] | None = None
    if isinstance(to_convert, DictionaryExtended):
        default_keys = to_convert.default_checked

    return legacy_valuespecs.Transform(
        legacy_valuespecs.Dictionary(
            elements=list(ungrouped_elements) + list(grouped_elements_map.items()),
            title=_localize_optional(to_convert.title, localizer),
            help=_localize_optional(to_convert.help_text, localizer),
            empty_text=_localize_optional(to_convert.no_elements_text, localizer),
            required_keys=ungrouped_element_key_props.required + list(required_group_keys),
            ignored_keys=list(to_convert.ignored_elements),
            hidden_keys=ungrouped_element_key_props.hidden + list(hidden_group_keys),
            default_keys=default_keys,
            validate=(
                _convert_to_dict_legacy_validation(
                    to_convert.custom_validate,
                    to_convert.elements,
                    to_convert.ignored_elements,
                    localizer,
                )
                if to_convert.custom_validate is not None
                else None
            ),
        ),
        back=_transform_dict_group_back(to_convert.elements, to_convert.ignored_elements),
        forth=_transform_dict_groups_forth(to_convert.elements, to_convert.ignored_elements),
    )


def _get_ungrouped_elements(
    dict_elements_map: Mapping[str, ruleset_api_v1.form_specs.DictElement],
    localizer: Callable[[str], str],
) -> tuple[_LegacyDictKeyProps, list[tuple[str, legacy_valuespecs.ValueSpec]]]:
    element_key_props = _LegacyDictKeyProps.from_elements(
        {
            key: element
            for key, element in dict_elements_map.items()
            if isinstance(element.group, ruleset_api_v1.form_specs.NoGroup)
        },
    )
    elements = [
        (key, convert_to_legacy_valuespec(dict_element.parameter_form, localizer))
        for key, dict_element in dict_elements_map.items()
        if isinstance(dict_element.group, ruleset_api_v1.form_specs.NoGroup)
    ]
    return element_key_props, elements


def _get_grouped_dict_orientation(
    elements: Sequence[tuple[str, legacy_valuespecs.ValueSpec]], key_props: _LegacyDictKeyProps
) -> bool:
    return set(key_props.required) == {elem[0] for elem in elements} and not any(
        isinstance(elem[1], legacy_valuespecs.Dictionary) for elem in elements
    )


def _make_group_as_nested_dict(
    title: ruleset_api_v1.Title | None,
    help_text: ruleset_api_v1.Help | None,
    dict_elements: Mapping[str, ruleset_api_v1.form_specs.DictElement],
    localizer: Callable[[str], str],
) -> tuple[legacy_valuespecs.Dictionary, bool]:
    key_props = _LegacyDictKeyProps.from_elements(dict_elements)
    elements = [
        (key, convert_to_legacy_valuespec(dict_element.parameter_form, localizer))
        for key, dict_element in dict_elements.items()
    ]

    all_group_elements_hidden = set(key_props.hidden) == {key for key, _ in elements}
    return (
        legacy_valuespecs.Dictionary(
            elements=elements,
            title=_localize_optional(title, localizer),
            help=_localize_optional(help_text, localizer),
            required_keys=key_props.required,
            hidden_keys=key_props.hidden,
            horizontal=_get_grouped_dict_orientation(elements, key_props),
        ),
        all_group_elements_hidden,
    )


def _group_elements(
    dict_elements_map: Mapping[str, ruleset_api_v1.form_specs.DictElement],
    localizer: Callable[[str], str],
) -> tuple[Mapping[str, legacy_valuespecs.Dictionary], set[str]]:
    grouped_dict_elements_map: dict[
        ruleset_api_v1.form_specs.DictGroup,
        dict[str, ruleset_api_v1.form_specs.DictElement],
    ] = defaultdict(dict)

    for key, dict_element in dict_elements_map.items():
        if isinstance(dict_element.group, ruleset_api_v1.form_specs.DictGroup):
            grouped_dict_elements_map[dict_element.group][key] = dict_element

    hidden_group_keys: set[str] = set()
    grouped_elements_map: dict[str, legacy_valuespecs.Dictionary] = {}
    for g, group_elements in grouped_dict_elements_map.items():
        nested_dict, all_hidden = _make_group_as_nested_dict(
            g.title, g.help_text, group_elements, localizer
        )
        group_key = _get_dict_group_key(g)
        grouped_elements_map[group_key] = nested_dict
        if all_hidden:
            hidden_group_keys.add(group_key)

    return grouped_elements_map, hidden_group_keys


def _convert_to_legacy_monitoring_state(
    to_convert: ruleset_api_v1.form_specs.ServiceState, localizer: Callable[[str], str]
) -> legacy_valuespecs.DropdownChoice:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "default_value": to_convert.prefill.value,
    }

    return legacy_valuespecs.MonitoringState(**converted_kwargs)


def _convert_to_legacy_host_state(
    to_convert: ruleset_api_v1.form_specs.HostState, localizer: Callable[[str], str]
) -> legacy_valuespecs.HostState:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "default_value": to_convert.prefill.value,
    }

    return legacy_valuespecs.HostState(
        **converted_kwargs,
    )


def _convert_to_legacy_dropdown_choice(
    to_convert: ruleset_api_v1.form_specs.SingleChoice | SingleChoiceExtended,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.DropdownChoice:
    choices = [
        (
            element.name.value if isinstance(element.name, enum.Enum) else element.name,
            element.title.localize(localizer),
        )
        for element in to_convert.elements
    ]
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "empty_text": _localize_optional(to_convert.no_elements_text, localizer),
        "read_only": to_convert.frozen,
        "deprecated_choices": to_convert.ignored_elements,
    }

    match to_convert.prefill:
        case ruleset_api_v1.form_specs.DefaultValue():
            converted_kwargs["default_value"] = to_convert.prefill.value
        case ruleset_api_v1.form_specs.InputHint():
            converted_kwargs["no_preselect_title"] = to_convert.prefill.value.localize(localizer)

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

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.DropdownChoice(choices, **converted_kwargs)


def _convert_to_legacy_cascading_dropdown(
    to_convert: ruleset_api_v1.form_specs.CascadingSingleChoice,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.CascadingDropdown:
    legacy_choices = [
        (
            str(element.name),
            element.title.localize(localizer),
            convert_to_legacy_valuespec(element.parameter_form, localizer),
        )
        for element in to_convert.elements
    ]

    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }
    match to_convert.prefill:
        case ruleset_api_v1.form_specs.InputHint():
            converted_kwargs["no_preselect_title"] = to_convert.prefill.value.localize(localizer)
        case ruleset_api_v1.form_specs.DefaultValue():
            # CascadingSingleChoice.__post_init__ checks that prefill_selection is one of the elements
            default_choice = next(
                legacy_choice
                for legacy_choice in legacy_choices
                if legacy_choice[0] == to_convert.prefill.value
            )
            converted_kwargs["default_value"] = (
                to_convert.prefill.value,
                default_choice[2].default_value(),
            )

    return legacy_valuespecs.CascadingDropdown(choices=legacy_choices, **converted_kwargs)


def _get_item_spec_maker(
    condition: ruleset_api_v1.rule_specs.HostAndItemCondition,
    localizer: Callable[[str], str],
) -> tuple[
    Callable[
        [],
        legacy_valuespecs.TextInput
        | legacy_valuespecs.DropdownChoice
        | legacy_valuespecs.TextAreaUnicode
        | legacy_valuespecs.FixedValue,
    ],
    ruleset_api_v1.form_specs.FormSpec,
]:
    item_form_with_title = dataclasses.replace(condition.item_form, title=condition.item_title)

    match item_form_with_title:
        case ruleset_api_v1.form_specs.String():
            return partial(
                _convert_to_legacy_text_input, item_form_with_title, localizer
            ), item_form_with_title
        case ruleset_api_v1.form_specs.SingleChoice():
            return partial(
                _convert_to_legacy_dropdown_choice, item_form_with_title, localizer
            ), item_form_with_title
        case ruleset_api_v1.form_specs.MultilineText():
            return partial(
                _convert_to_legacy_text_area, item_form_with_title, localizer
            ), item_form_with_title
        case ruleset_api_v1.form_specs.FixedValue():
            return partial(
                _convert_to_legacy_fixed_value, item_form_with_title, localizer
            ), item_form_with_title
        case other:
            raise ValueError(other)


_ValidateFuncType = TypeVar("_ValidateFuncType")


def _convert_to_legacy_validation(
    v1_validate_funcs: Iterable[Callable[[_ValidateFuncType], object]],
    localizer: Callable[[str], str],
) -> Callable[[_ValidateFuncType, str], None]:
    def wrapper(value: _ValidateFuncType, var_prefix: str) -> None:
        try:
            _ = [v1_validate_func(value) for v1_validate_func in v1_validate_funcs]
        except ruleset_api_v1.form_specs.validators.ValidationError as e:
            raise MKUserError(var_prefix, e.message.localize(localizer))

    return wrapper


def _convert_to_legacy_list(
    to_convert: ruleset_api_v1.form_specs.List | ListExtended, localizer: Callable[[str], str]
) -> legacy_valuespecs.ListOf:
    template = convert_to_legacy_valuespec(to_convert.element_template, localizer)
    converted_kwargs: dict[str, Any] = {
        "valuespec": template,
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "movable": to_convert.editable_order,
        "add_label": to_convert.add_element_label.localize(localizer),
        "del_label": to_convert.remove_element_label.localize(localizer),
        "text_if_empty": to_convert.no_element_label.localize(localizer),
        **_get_allow_empty_conf(to_convert, localizer),
    }

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    if isinstance(to_convert, ListExtended):
        converted_kwargs["default_value"] = to_convert.prefill.value

    return legacy_valuespecs.ListOf(**converted_kwargs)


def _convert_to_legacy_list_of_strings(
    to_convert: ListOfStrings, localizer: Callable[[str], str]
) -> legacy_valuespecs.ListOfStrings:
    template = convert_to_legacy_valuespec(to_convert.string_spec, localizer)
    match to_convert.layout:
        case ListOfStringsLayout.horizontal:
            orientation = "horizontal"
        case ListOfStringsLayout.vertical:
            orientation = "vertical"
        case _:
            assert_never(to_convert.layout)

    converted_kwargs: dict[str, Any] = {
        "valuespec": template,
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "orientation": orientation,
        "default_value": to_convert.prefill.value,
        **_get_allow_empty_conf(to_convert, localizer),
    }

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.ListOfStrings(**converted_kwargs)


def _convert_to_legacy_fixed_value(
    to_convert: ruleset_api_v1.form_specs.FixedValue, localizer: Callable[[str], str]
) -> legacy_valuespecs.FixedValue:
    return legacy_valuespecs.FixedValue(
        value=to_convert.value,
        totext=(
            _localize_optional(to_convert.label, localizer) if to_convert.label is not None else ""
        ),
        title=_localize_optional(to_convert.title, localizer),
        help=_localize_optional(to_convert.help_text, localizer),
    )


def _convert_to_legacy_time_unit(
    unit: ruleset_api_v1.form_specs.TimeMagnitude,
) -> Literal["days", "hours", "minutes", "seconds", "milliseconds"]:
    match unit:
        case ruleset_api_v1.form_specs.TimeMagnitude.MILLISECOND:
            return "milliseconds"
        case ruleset_api_v1.form_specs.TimeMagnitude.SECOND:
            return "seconds"
        case ruleset_api_v1.form_specs.TimeMagnitude.MINUTE:
            return "minutes"
        case ruleset_api_v1.form_specs.TimeMagnitude.HOUR:
            return "hours"
        case ruleset_api_v1.form_specs.TimeMagnitude.DAY:
            return "days"


def _convert_to_legacy_time_span(
    to_convert: ruleset_api_v1.form_specs.TimeSpan, localizer: Callable[[str], str]
) -> legacy_valuespecs.TimeSpan:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
    }

    if to_convert.displayed_magnitudes is not None:
        converted_kwargs["display"] = [
            _convert_to_legacy_time_unit(u) for u in to_convert.displayed_magnitudes
        ]

    match to_convert.prefill:
        case ruleset_api_v1.form_specs.DefaultValue():
            converted_kwargs["default_value"] = to_convert.prefill.value
        case ruleset_api_v1.form_specs.InputHint():
            pass  # not implemented for legacy VS

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.TimeSpan(**converted_kwargs)


_NumberT = TypeVar("_NumberT", float, int)


def _get_legacy_level_spec(
    form_spec_template: ruleset_api_v1.form_specs.FormSpec[_NumberT],
    title: ruleset_api_v1.Title,
    prefill_value: _NumberT,
    prefill_type: (
        type[ruleset_api_v1.form_specs.DefaultValue] | type[ruleset_api_v1.form_specs.InputHint]
    ),
    localizer: Callable[[str], str],
) -> legacy_valuespecs.ValueSpec:
    # Currently all FormSpec[_NumberT] types have a prefill attribute,
    # but we don't know it statically. Let's just skip it in case
    # we someday invent one that does not have this attribute.
    if hasattr(form_spec_template, "prefill"):
        form_spec_template = dataclasses.replace(
            form_spec_template,
            prefill=prefill_type(prefill_value),  # type: ignore[call-arg]
        )
    return convert_to_legacy_valuespec(
        dataclasses.replace(form_spec_template, title=title), localizer
    )


def _get_prefill_type(
    prefill: ruleset_api_v1.form_specs.Prefill,
) -> type[ruleset_api_v1.form_specs.DefaultValue] | type[ruleset_api_v1.form_specs.InputHint]:
    return (
        ruleset_api_v1.form_specs.DefaultValue
        if isinstance(prefill, ruleset_api_v1.form_specs.DefaultValue)
        else ruleset_api_v1.form_specs.InputHint
    )


def _get_fixed_levels_choice_element(
    form_spec: ruleset_api_v1.form_specs.FormSpec[_NumberT],
    prefill: ruleset_api_v1.form_specs.Prefill[tuple[_NumberT, _NumberT]],
    level_direction: ruleset_api_v1.form_specs.LevelDirection,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.Tuple:
    if level_direction is ruleset_api_v1.form_specs.LevelDirection.LOWER:
        warn_title = ruleset_api_v1.Title("Warning below")
        crit_title = ruleset_api_v1.Title("Critical below")
    elif level_direction is ruleset_api_v1.form_specs.LevelDirection.UPPER:
        warn_title = ruleset_api_v1.Title("Warning at")
        crit_title = ruleset_api_v1.Title("Critical at")
    else:
        assert_never(level_direction)

    prefill_type = _get_prefill_type(prefill)

    return legacy_valuespecs.Tuple(
        elements=[
            _get_legacy_level_spec(
                form_spec, warn_title, prefill.value[0], prefill_type, localizer
            ),
            _get_legacy_level_spec(
                form_spec, crit_title, prefill.value[1], prefill_type, localizer
            ),
        ],
    )


class _PredictiveLevelDefinition(enum.StrEnum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    STDEV = "stdev"


def _get_level_computation_dropdown(
    form_spec_template: ruleset_api_v1.form_specs.FormSpec[_NumberT],
    to_convert: ruleset_api_v1.form_specs.PredictiveLevels[_NumberT],
    level_direction: ruleset_api_v1.form_specs.LevelDirection,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.CascadingDropdown:
    if level_direction is ruleset_api_v1.form_specs.LevelDirection.UPPER:
        warn_title = ruleset_api_v1.Title("Warning above")
        crit_title = ruleset_api_v1.Title("Critical above")
    elif level_direction is ruleset_api_v1.form_specs.LevelDirection.LOWER:
        warn_title = ruleset_api_v1.Title("Warning below")
        crit_title = ruleset_api_v1.Title("Critical below")
    else:
        assert_never(level_direction)

    abs_diff_prefill_type = _get_prefill_type(to_convert.prefill_abs_diff)
    # InputHint not supported by legacy VS -> use DEF_VALUE for now.
    rel_prefill: (
        tuple[float, float] | tuple[legacy_valuespecs.Sentinel, legacy_valuespecs.Sentinel]
    ) = (
        to_convert.prefill_rel_diff.value
        if isinstance(to_convert.prefill_rel_diff, ruleset_api_v1.form_specs.DefaultValue)
        else (legacy_valuespecs.DEF_VALUE, legacy_valuespecs.DEF_VALUE)
    )
    stddev_prefill: (
        tuple[float, float] | tuple[legacy_valuespecs.Sentinel, legacy_valuespecs.Sentinel]
    ) = (
        to_convert.prefill_stdev_diff.value
        if isinstance(to_convert.prefill_stdev_diff, ruleset_api_v1.form_specs.DefaultValue)
        else (legacy_valuespecs.DEF_VALUE, legacy_valuespecs.DEF_VALUE)
    )

    return legacy_valuespecs.CascadingDropdown(
        title=ruleset_api_v1.Title("Level definition in relation to the predicted value").localize(
            localizer
        ),
        choices=[
            (
                _PredictiveLevelDefinition.ABSOLUTE.value,
                ruleset_api_v1.Title("Absolute difference").localize(localizer),
                legacy_valuespecs.Tuple(
                    help=ruleset_api_v1.Help(
                        "The thresholds are calculated by increasing or decreasing the predicted "
                        "value by a fixed absolute value"
                    ).localize(localizer),
                    elements=[
                        _get_legacy_level_spec(
                            form_spec_template,
                            warn_title,
                            to_convert.prefill_abs_diff.value[0],
                            abs_diff_prefill_type,
                            localizer,
                        ),
                        _get_legacy_level_spec(
                            form_spec_template,
                            crit_title,
                            to_convert.prefill_abs_diff.value[1],
                            abs_diff_prefill_type,
                            localizer,
                        ),
                    ],
                ),
            ),
            (
                _PredictiveLevelDefinition.RELATIVE.value,
                ruleset_api_v1.Title("Relative difference").localize(localizer),
                legacy_valuespecs.Tuple(
                    help=ruleset_api_v1.Help(
                        "The thresholds are calculated by increasing or decreasing the predicted "
                        "value by a percentage"
                    ).localize(localizer),
                    elements=[
                        legacy_valuespecs.Percentage(
                            title=warn_title.localize(localizer),
                            default_value=rel_prefill[0],
                        ),
                        legacy_valuespecs.Percentage(
                            title=crit_title.localize(localizer),
                            default_value=rel_prefill[1],
                        ),
                    ],
                ),
            ),
            (
                _PredictiveLevelDefinition.STDEV.value,
                ruleset_api_v1.Title("Standard deviation difference").localize(localizer),
                legacy_valuespecs.Tuple(
                    help=ruleset_api_v1.Help(
                        "The thresholds are calculated by increasing or decreasing the predicted "
                        "value by a multiple of the standard deviation"
                    ).localize(localizer),
                    elements=[
                        legacy_valuespecs.Float(
                            title=warn_title.localize(localizer),
                            unit=ruleset_api_v1.Label("times the standard deviation").localize(
                                localizer
                            ),
                            default_value=stddev_prefill[0],
                        ),
                        legacy_valuespecs.Float(
                            title=crit_title.localize(localizer),
                            unit=ruleset_api_v1.Label("times the standard deviation").localize(
                                localizer
                            ),
                            default_value=stddev_prefill[1],
                        ),
                    ],
                ),
            ),
        ],
    )


def _get_predictive_levels_choice_element(
    form_spec_template: ruleset_api_v1.form_specs.FormSpec[_NumberT],
    to_convert: ruleset_api_v1.form_specs.PredictiveLevels[_NumberT],
    level_direction: ruleset_api_v1.form_specs.LevelDirection,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.Transform:
    if level_direction is ruleset_api_v1.form_specs.LevelDirection.UPPER:
        fixed_warn_title = ruleset_api_v1.Title("Warning level is at least")
        fixed_crit_title = ruleset_api_v1.Title("Critical level is at least")
        fixed_help_text = ruleset_api_v1.Help(
            "Regardless of how the dynamic levels are computed according to the prediction: they "
            "will never be set below the following limits. This avoids false alarms during times "
            "where the predicted levels would be very low."
        )

    elif level_direction is ruleset_api_v1.form_specs.LevelDirection.LOWER:
        fixed_warn_title = ruleset_api_v1.Title("Warning level is at most")
        fixed_crit_title = ruleset_api_v1.Title("Critical level is at most")
        fixed_help_text = ruleset_api_v1.Help(
            "Regardless of how the dynamic levels are computed according to the prediction: they "
            "will never be set above the following limits. This avoids false alarms during times "
            "where the predicted levels would be very high."
        )
    else:
        assert_never(level_direction)

    predictive_elements: Sequence[tuple[str, legacy_valuespecs.ValueSpec]] = [
        (
            "period",
            legacy_valuespecs.DropdownChoice(
                choices=[
                    ("wday", ruleset_api_v1.Title("Day of the week").localize(localizer)),
                    ("day", ruleset_api_v1.Title("Day of the month").localize(localizer)),
                    ("hour", ruleset_api_v1.Title("Hour of the day").localize(localizer)),
                    (
                        "minute",
                        ruleset_api_v1.Title("Minute of the hour").localize(localizer),
                    ),
                ],
                title=ruleset_api_v1.Title("Base prediction on").localize(localizer),
                help=ruleset_api_v1.Help(
                    "Define the periodicity in which the repetition of the measured data is "
                    "expected (monthly, weekly, daily or hourly)"
                ).localize(localizer),
            ),
        ),
        (
            "horizon",
            legacy_valuespecs.Integer(
                title=ruleset_api_v1.Title("Length of historic data to consider").localize(
                    localizer
                ),
                help=ruleset_api_v1.Help(
                    "How many days in the past Checkmk should evaluate the measurement data"
                ).localize(localizer),
                unit=ruleset_api_v1.Label("days").localize(localizer),
                minvalue=1,
                default_value=90,
            ),
        ),
        (
            "levels",
            _get_level_computation_dropdown(
                form_spec_template, to_convert, level_direction, localizer
            ),
        ),
        (
            "bound",
            legacy_valuespecs.Optional(
                title=ruleset_api_v1.Title("Fixed limits").localize(localizer),
                label=ruleset_api_v1.Label("Set fixed limits").localize(localizer),
                valuespec=legacy_valuespecs.Tuple(
                    help=fixed_help_text.localize(localizer),
                    elements=[
                        _get_legacy_level_spec(
                            form_spec_template,
                            fixed_warn_title,
                            0,
                            ruleset_api_v1.form_specs.InputHint,
                            localizer,
                        ),
                        _get_legacy_level_spec(
                            form_spec_template,
                            fixed_crit_title,
                            0,
                            ruleset_api_v1.form_specs.InputHint,
                            localizer,
                        ),
                    ],
                ),
            ),
        ),
    ]

    return legacy_valuespecs.Transform(
        valuespec=legacy_valuespecs.Dictionary(
            elements=predictive_elements,
            required_keys=["period", "horizon", "levels", "bound"],
        ),
        to_valuespec=lambda p: {k: p[k] for k in p if not k.startswith("__")},
        from_valuespec=lambda p: {
            **p,
            # The backend uses this information to compute the correct prediction.
            # The Transform ensures that an updated value in the ruleset plugin
            # is reflected in the stored data after update.
            "__reference_metric__": to_convert.reference_metric,
            "__direction__": (
                "upper"
                if level_direction is ruleset_api_v1.form_specs.LevelDirection.UPPER
                else "lower"
            ),
        },
    )


class _LevelDynamicChoice(enum.StrEnum):
    NO_LEVELS = "no_levels"
    FIXED = "fixed"
    PREDICTIVE = "predictive"


LevelsConfigLegacyModel = (
    ruleset_api_v1.form_specs.SimpleLevelsConfigModel | tuple[Literal["predictive"], object]
)

LevelsConfigModel = (
    ruleset_api_v1.form_specs.SimpleLevelsConfigModel
    | tuple[Literal["cmk_postprocessed"], Literal["predictive_levels"], object]
)


def _transform_levels_forth(value: object) -> LevelsConfigLegacyModel:
    match value:
        case "no_levels", None:
            return "no_levels", None
        case "fixed", tuple(fixed_levels):
            return "fixed", fixed_levels
        case "predictive", dict(predictive_levels):  # format released in 2.3.0b3
            return "predictive", predictive_levels
        case "cmk_postprocessed", "predictive_levels", predictive_levels:
            return "predictive", predictive_levels

    raise ValueError(value)


def _transform_levels_back(
    value: LevelsConfigLegacyModel,
) -> LevelsConfigModel:
    match value:
        case "no_levels", None:
            return "no_levels", None
        case "fixed", tuple(fixed_levels):
            return "fixed", fixed_levels
        case "predictive", predictive_levels:
            return "cmk_postprocessed", "predictive_levels", predictive_levels

    raise ValueError(value)


def _convert_to_legacy_levels(
    to_convert: (
        ruleset_api_v1.form_specs.Levels[_NumberT]
        | ruleset_api_v1.form_specs.SimpleLevels[_NumberT]
    ),
    localizer: Callable[[str], str],
) -> legacy_valuespecs.Transform:
    choices: list[tuple[str, str, legacy_valuespecs.ValueSpec]] = [
        (
            _LevelDynamicChoice.NO_LEVELS.value,
            ruleset_api_v1.Title("No levels").localize(localizer),
            legacy_valuespecs.FixedValue(
                value=None,
                title=ruleset_api_v1.Title("No levels").localize(localizer),
                totext=ruleset_api_v1.Label("Do not impose levels, always be OK").localize(
                    localizer
                ),
            ),
        ),
        (
            _LevelDynamicChoice.FIXED.value,
            ruleset_api_v1.Title("Fixed levels").localize(localizer),
            _get_fixed_levels_choice_element(
                to_convert.form_spec_template,
                to_convert.prefill_fixed_levels,
                to_convert.level_direction,
                localizer,
            ),
        ),
    ]
    if isinstance(to_convert, ruleset_api_v1.form_specs.Levels):
        choices.append(
            (
                _LevelDynamicChoice.PREDICTIVE.value,
                ruleset_api_v1.Title("Predictive levels (only on CMC)").localize(localizer),
                _get_predictive_levels_choice_element(
                    to_convert.form_spec_template,
                    to_convert.predictive,
                    to_convert.level_direction,
                    localizer,
                ),
            )
        )

    match to_convert.form_spec_template:
        case (
            ruleset_api_v1.form_specs.Float()
            | ruleset_api_v1.form_specs.TimeSpan()
            | ruleset_api_v1.form_specs.Percentage()
        ):
            # mypy accepts int's in place of float's (https://github.com/python/mypy/issues/11385).
            # However, int is not a subclass of float, issubclass(int, float) is false. In a
            # CascadingDropdown it is not acceptable to pass an int instead of a float (CMK-16402
            # shows the warning). We transform the value here, such that users which rely on mypy
            # validation are not disappointed.
            prefill_value = (
                float(to_convert.prefill_fixed_levels.value[0]),
                float(to_convert.prefill_fixed_levels.value[1]),
            )
        case ruleset_api_v1.form_specs.Integer() | ruleset_api_v1.form_specs.DataSize():
            prefill_value = to_convert.prefill_fixed_levels.value

    validate = None
    if to_convert.custom_validate is not None:
        validate = _convert_to_legacy_validation(to_convert.custom_validate, localizer)
    return legacy_valuespecs.Transform(
        legacy_valuespecs.CascadingDropdown(
            title=_localize_optional(to_convert.title, localizer),
            help=_localize_optional(to_convert.help_text, localizer),
            choices=choices,
            default_value=_make_levels_default_value(to_convert, prefill_value),
            # Mypy does not see, to see Literal["..."] as a str
            validate=validate,  # type: ignore[arg-type]
        ),
        back=_transform_levels_back,
        forth=_transform_levels_forth,
    )


def _make_levels_default_value(
    to_convert: (
        ruleset_api_v1.form_specs.Levels[_NumberT]
        | ruleset_api_v1.form_specs.SimpleLevels[_NumberT]
    ),
    prefill_fixed: tuple[_NumberT, _NumberT],
) -> tuple[str, None | tuple[_NumberT, _NumberT] | dict[str, Any]]:
    if to_convert.prefill_levels_type.value is ruleset_api_v1.form_specs.LevelsType.NONE:
        return _LevelDynamicChoice.NO_LEVELS.value, None

    if to_convert.prefill_levels_type.value is ruleset_api_v1.form_specs.LevelsType.FIXED:
        return _LevelDynamicChoice.FIXED.value, prefill_fixed

    if isinstance(to_convert, ruleset_api_v1.form_specs.Levels):
        return (
            _LevelDynamicChoice.PREDICTIVE.value,
            {
                "period": "wday",
                "horizon": 90,
                "levels": (
                    _PredictiveLevelDefinition.ABSOLUTE.value,
                    to_convert.predictive.prefill_abs_diff.value,
                ),
                "bound": None,
            },
        )

    raise NotImplementedError()  # should never happen.


def _transform_proxy_forth(value: object) -> tuple[str, str | None]:
    match value:
        case "cmk_postprocessed", "environment_proxy", str():
            return "environment", "environment"
        case "cmk_postprocessed", "no_proxy", str():
            return "no_proxy", None
        case "cmk_postprocessed", "stored_proxy", str(stored_proxy_id):
            return "global", stored_proxy_id
        case "cmk_postprocessed", "explicit_proxy", str(url):
            return "url", url

    raise ValueError(value)


def _transform_proxy_back(
    value: tuple[str, str],
) -> tuple[
    Literal["cmk_postprocessed"],
    Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
    str,
]:
    match value:
        case "environment", "environment":
            return "cmk_postprocessed", "environment_proxy", ""
        case "no_proxy", None:
            return "cmk_postprocessed", "no_proxy", ""
        case "global", str(stored_proxy_id):
            return "cmk_postprocessed", "stored_proxy", stored_proxy_id
        case "url", str(url):
            return "cmk_postprocessed", "explicit_proxy", url

    raise ValueError(value)


def _convert_to_legacy_http_proxy(
    to_convert: ruleset_api_v1.form_specs.Proxy, localizer: Callable[[str], str]
) -> legacy_valuespecs.Transform:
    allowed_schemas = {s.value for s in to_convert.allowed_schemas}

    def _global_proxy_choices() -> legacy_valuespecs.DropdownChoiceEntries:
        settings = legacy_config_domains.ConfigDomainCore().load()
        return [
            (p["ident"], p["title"])
            for p in settings.get("http_proxies", {}).values()
            if urllib.parse.urlparse(p["proxy_url"]).scheme in allowed_schemas
        ]

    return Transform(
        legacy_valuespecs.CascadingDropdown(
            title=ruleset_api_v1.Title("HTTP proxy").localize(localizer),
            default_value=("environment", "environment"),
            choices=[
                (
                    "environment",
                    ruleset_api_v1.Title("Use from environment").localize(localizer),
                    legacy_valuespecs.FixedValue(
                        value="environment",
                        help=ruleset_api_v1.Help(
                            "Use the proxy settings from the environment variables. The variables <tt>NO_PROXY</tt>, "
                            "<tt>HTTP_PROXY</tt> and <tt>HTTPS_PROXY</tt> are taken into account during execution. "
                            "Have a look at the python requests module documentation for further information. Note "
                            "that these variables must be defined as a site-user in ~/etc/environment and that "
                            "this might affect other notification methods which also use the requests module."
                        ).localize(localizer),
                        totext=ruleset_api_v1.Label(
                            "Use proxy settings from the process environment. This is the default."
                        ).localize(localizer),
                    ),
                ),
                (
                    "no_proxy",
                    ruleset_api_v1.Title("Connect without proxy").localize(localizer),
                    legacy_valuespecs.FixedValue(
                        value=None,
                        totext=ruleset_api_v1.Label(
                            "Connect directly to the destination instead of using a proxy."
                        ).localize(localizer),
                    ),
                ),
                (
                    "global",
                    ruleset_api_v1.Title("Use globally configured proxy").localize(localizer),
                    legacy_valuespecs.DropdownChoice(
                        choices=_global_proxy_choices,
                        sorted=True,
                    ),
                ),
                (
                    "url",
                    ruleset_api_v1.Title("Use explicit proxy settings").localize(localizer),
                    legacy_valuespecs.Url(
                        title=ruleset_api_v1.Title("Proxy URL").localize(localizer),
                        default_scheme="http",
                        allowed_schemes=allowed_schemas,
                    ),
                ),
            ],
            sorted=False,
        ),
        forth=_transform_proxy_forth,
        back=_transform_proxy_back,
    )


def _convert_to_legacy_checkbox(
    to_convert: ruleset_api_v1.form_specs.BooleanChoice, localizer: Callable[[str], str]
) -> legacy_valuespecs.Checkbox:
    return legacy_valuespecs.Checkbox(
        label=_localize_optional(to_convert.label, localizer),
        title=_localize_optional(to_convert.title, localizer),
        help=_localize_optional(to_convert.help_text, localizer),
        default_value=to_convert.prefill.value,
    )


def _convert_to_legacy_file_upload(
    to_convert: ruleset_api_v1.form_specs.FileUpload, localizer: Callable[[str], str]
) -> legacy_valuespecs.FileUpload:
    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }
    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.FileUpload(
        allow_empty=True,  # this makes it a "required" field
        allowed_extensions=to_convert.extensions,
        mime_types=to_convert.mime_types,
        allow_empty_content=True,
        **converted_kwargs,
    )


def _convert_to_legacy_metric_name(
    to_convert: ruleset_api_v1.form_specs.Metric, localizer: Callable[[str], str]
) -> legacy_graphing_valuespecs.MetricName:
    converted_kwargs = {}
    if (help_text := _localize_optional(to_convert.help_text, localizer)) is None:
        help_text = ruleset_api_v1.Help("Select from a list of metrics known to Checkmk").localize(
            localizer
        )
    converted_kwargs["help"] = help_text
    if (title := _localize_optional(to_convert.title, localizer)) is not None:
        converted_kwargs["title"] = title
    return legacy_graphing_valuespecs.MetricName(**converted_kwargs)


def _convert_to_legacy_monitored_host_name(
    to_convert: ruleset_api_v1.form_specs.MonitoredHost | MonitoredHostExtended,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.MonitoredHostname:
    converted_kwargs: dict[str, Any] = {
        "autocompleter": ContextAutocompleterConfig(
            ident=legacy_valuespecs.MonitoredHostname.ident,
            strict=True,
            show_independent_of_context=True,
        )
    }
    if (help_text := _localize_optional(to_convert.help_text, localizer)) is None:
        help_text = ruleset_api_v1.Help(
            "Select from a list of host names known to Checkmk"
        ).localize(localizer)
    converted_kwargs["help"] = help_text
    if (title := _localize_optional(to_convert.title, localizer)) is None:
        title = ruleset_api_v1.Title("Host name").localize(localizer)
    converted_kwargs["title"] = title
    if isinstance(to_convert, MonitoredHostExtended):
        converted_kwargs["default_value"] = to_convert.prefill.value

    return legacy_valuespecs.MonitoredHostname(**converted_kwargs)


def _convert_to_legacy_monitored_service_description(
    to_convert: ruleset_api_v1.form_specs.MonitoredService,
    localizer: Callable[[str], str],
) -> legacy_valuespecs.MonitoredServiceDescription:
    converted_kwargs: dict[str, Any] = {
        "autocompleter": ContextAutocompleterConfig(
            ident=legacy_valuespecs.MonitoredServiceDescription.ident,
            strict=True,
            show_independent_of_context=True,
        )
    }
    if (help_text := _localize_optional(to_convert.help_text, localizer)) is None:
        help_text = ruleset_api_v1.Help(
            "Select from a list of service names known to Checkmk"
        ).localize(localizer)
    converted_kwargs["help"] = help_text
    if (title := _localize_optional(to_convert.title, localizer)) is None:
        title = ruleset_api_v1.Title("Service name").localize(localizer)
    converted_kwargs["title"] = title

    return legacy_valuespecs.MonitoredServiceDescription(**converted_kwargs)


def _transform_password_forth(value: object) -> tuple[str, str]:
    match value:
        case "cmk_postprocessed", "explicit_password", (str(), str(password)):
            return "password", password
        case "cmk_postprocessed", "stored_password", (str(password_store_id), str()):
            return "store", password_store_id

    raise ValueError(value)


def _transform_password_back(
    value: tuple[str, str],
) -> tuple[
    Literal["cmk_postprocessed"], Literal["explicit_password", "stored_password"], tuple[str, str]
]:
    match value:
        case "password", str(password):
            return "cmk_postprocessed", "explicit_password", (ad_hoc_password_id(), password)
        case "store", str(password_store_id):
            return "cmk_postprocessed", "stored_password", (password_store_id, "")

    raise ValueError(value)


def _convert_to_legacy_individual_or_stored_password(
    to_convert: ruleset_api_v1.form_specs.Password, localizer: Callable[[str], str]
) -> legacy_valuespecs.Transform:
    return Transform(
        IndividualOrStoredPassword(
            title=_localize_optional(to_convert.title, localizer),
            help=_localize_optional(to_convert.help_text, localizer),
            allow_empty=False,
        ),
        forth=_transform_password_forth,
        back=_transform_password_back,
    )


def _convert_to_legacy_list_choice_match_type(
    to_convert: ruleset_api_v1.form_specs.MultipleChoice, localizer: Callable[[str], str]
) -> legacy_valuespecs.ValueSpec:
    def _ensure_sequence_str(value: object) -> Sequence | object:
        if not isinstance(value, Sequence):
            return value
        return list(value)

    return Transform(
        _convert_to_legacy_list_choice(to_convert, localizer),
        forth=_ensure_sequence_str,
    )


def _convert_to_legacy_list_choice(
    to_convert: ruleset_api_v1.form_specs.MultipleChoice, localizer: Callable[[str], str]
) -> legacy_valuespecs.ListChoice | legacy_valuespecs.DualListChoice:
    # arbitrarily chosen maximal size of created ListChoice
    # if number of choices if bigger, MultipleChoice is converted to DualListChoice
    MAX_LIST_CHOICE_SIZE: int = 10
    MAX_DUALLIST_CHOICE_SIZE: int = 25

    converted_kwargs: dict[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "default_value": to_convert.prefill.value,
        **_get_allow_empty_conf(to_convert, localizer),
    }

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    choices = [(e.name, e.title.localize(localizer)) for e in to_convert.elements]

    if len(choices) <= MAX_LIST_CHOICE_SIZE:
        return legacy_valuespecs.ListChoice(
            choices=choices,
            toggle_all=to_convert.show_toggle_all,
            **converted_kwargs,
        )

    return legacy_valuespecs.DualListChoice(
        choices=choices,
        toggle_all=to_convert.show_toggle_all,
        rows=min(len(choices), MAX_DUALLIST_CHOICE_SIZE),
        **converted_kwargs,
    )


def _convert_to_legacy_text_area(
    to_convert: ruleset_api_v1.form_specs.MultilineText, localizer: Callable[[str], str]
) -> legacy_valuespecs.TextAreaUnicode:
    converted_kwargs: dict[str, Any] = {**_get_allow_empty_conf(to_convert, localizer)}

    help_text = _localize_optional(to_convert.help_text, localizer)
    if to_convert.macro_support:
        macros_help_text = (
            "This field supports the use of macros. "
            "The corresponding plug-in replaces the macros with the actual values."
        )
        localized_text = ruleset_api_v1.Help(macros_help_text).localize(localizer)
        converted_kwargs["help"] = f"{help_text} {localized_text}" if help_text else localized_text
    else:
        converted_kwargs["help"] = help_text

    match to_convert.prefill:
        case ruleset_api_v1.form_specs.DefaultValue():
            converted_kwargs["default_value"] = to_convert.prefill.value
        case ruleset_api_v1.form_specs.InputHint():
            pass  # not implemented for legacy VS

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.TextAreaUnicode(
        monospaced=to_convert.monospaced,
        label=_localize_optional(to_convert.label, localizer),
        title=_localize_optional(to_convert.title, localizer),
        **converted_kwargs,
    )


def _transform_timeperiod_forth(value: object) -> str | None:
    match value:
        case "cmk_postprocessed", "stored_time_period", str(time_period):
            return time_period
        # time_period is None when adding a new rule
        case "cmk_postprocessed", "stored_time_period", None:
            return None

    raise ValueError(value)


def _transform_timeperiod_back(
    value: str,
) -> tuple[Literal["cmk_postprocessed"], Literal["stored_time_period"], str]:
    return "cmk_postprocessed", "stored_time_period", value


def _convert_to_legacy_timeperiod_selection(
    to_convert: ruleset_api_v1.form_specs.TimePeriod, localizer: Callable[[str], str]
) -> legacy_valuespecs.Transform:
    return legacy_valuespecs.Transform(
        legacy_timeperiods.TimeperiodSelection(
            title=_localize_optional(to_convert.title, localizer),
            help=_localize_optional(to_convert.help_text, localizer),
        ),
        back=_transform_timeperiod_back,
        forth=_transform_timeperiod_forth,
    )


def _convert_to_legacy_tuple(
    to_convert: Tuple, localizer: Callable[[str], str]
) -> legacy_valuespecs.Tuple:
    orientation = to_convert.layout
    # The legacy Tuple does not support the "horizontal_titles_top" orientation.
    if orientation == "horizontal_titles_top":
        orientation = "horizontal"
    return legacy_valuespecs.Tuple(
        title=_localize_optional(to_convert.title, localizer),
        help=_localize_optional(to_convert.help_text, localizer),
        elements=[convert_to_legacy_valuespec(e, localizer) for e in to_convert.elements],
        orientation=orientation,
        show_titles=to_convert.show_titles,
    )


def _convert_to_legacy_password(
    to_convert: SimplePassword, localizer: Callable[[str], str]
) -> legacy_valuespecs.Password:
    return legacy_valuespecs.Password(
        title=_localize_optional(to_convert.title, localizer),
        help=_localize_optional(to_convert.help_text, localizer),
        validate=_convert_to_legacy_validation(to_convert.custom_validate, localizer)
        if to_convert.custom_validate
        else None,
    )


def _convert_to_legacy_user_selection(
    to_convert: UserSelection, localizer: Callable[[str], str]
) -> legacy_valuespecs.Transform[UserId | None]:
    legacy_filter = to_convert.filter.to_legacy()

    return LegacyUserSelection(
        title=_localize_optional(to_convert.title, localizer),
        help=_localize_optional(to_convert.help_text, localizer),
        only_contacts=legacy_filter.only_contacts,
        only_automation=legacy_filter.only_automation,
    )


def _convert_to_legacy_validation_with_none(
    v1_validate_funcs: Iterable[Callable[[_ValidateFuncType], object]],
    localizer: Callable[[str], str],
) -> Callable[[_ValidateFuncType | None, str], None]:
    def wrapper(value: _ValidateFuncType | None, var_prefix: str) -> None:
        if value is None:
            return
        try:
            _ = [v1_validate_func(value) for v1_validate_func in v1_validate_funcs]
        except ruleset_api_v1.form_specs.validators.ValidationError as e:
            raise MKUserError(var_prefix, e.message.localize(localizer))

    return wrapper


def _convert_to_legacy_autocompleter(
    to_convert: StringAutocompleter, localizer: Callable[[str], str]
) -> AjaxDropdownChoice:
    return AjaxDropdownChoice(
        title=_localize_optional(to_convert.title, localizer),
        help=_localize_optional(to_convert.help_text, localizer),
        validate=_convert_to_legacy_validation_with_none(to_convert.custom_validate, localizer)
        if to_convert.custom_validate
        else None,
        autocompleter=AutocompleterConfig(ident=to_convert.autocompleter.data.ident)
        if to_convert.autocompleter
        else None,
    )
