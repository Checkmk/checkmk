#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths

import cmk.gui.plugins.wato as api_module  # pylint: disable=cmk-module-layer-violation
import cmk.gui.plugins.wato.utils as wato_utils  # pylint: disable=cmk-module-layer-violation
import cmk.gui.valuespec
import cmk.gui.view_utils
import cmk.gui.watolib.attributes
import cmk.gui.watolib.changes
import cmk.gui.watolib.config_domain_name
import cmk.gui.watolib.config_domains
import cmk.gui.watolib.config_hostname
import cmk.gui.watolib.host_attributes
import cmk.gui.watolib.hosts_and_folders

# Make some functions of watolib available to Setup plug-ins without using the
# watolib module name. This is mainly done for compatibility reasons to keep
# the current plug-in API functions working
import cmk.gui.watolib.network_scan
import cmk.gui.watolib.read_only
import cmk.gui.watolib.rulespecs
import cmk.gui.watolib.sites
import cmk.gui.watolib.timeperiods
import cmk.gui.watolib.translation
import cmk.gui.watolib.user_scripts
import cmk.gui.watolib.utils
from cmk.gui.hooks import register_hook
from cmk.gui.plugins.wato import datasource_programs  # pylint: disable=cmk-module-layer-violation
from cmk.gui.plugins.wato.utils import (  # pylint: disable=cmk-module-layer-violation
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
    RulespecGroupCheckParametersHardware,
    RulespecGroupCheckParametersNetworking,
    RulespecGroupCheckParametersOperatingSystem,
    RulespecGroupCheckParametersPrinters,
    RulespecGroupCheckParametersStorage,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.wato._main_module_topics import (
    MainModuleTopicAgents,
    MainModuleTopicEvents,
    MainModuleTopicExporter,
    MainModuleTopicGeneral,
    MainModuleTopicHosts,
    MainModuleTopicMaintenance,
    MainModuleTopicServices,
    MainModuleTopicUsers,
)
from cmk.gui.watolib.main_menu import register_modules, WatoModule
from cmk.gui.watolib.mode import mode_registry, mode_url, redirect, WatoMode
from cmk.gui.watolib.notification_parameter import (
    notification_parameter_registry,
    NotificationParameter,
    register_notification_parameters,
)

from ._check_mk_configuration import monitoring_macro_help, PluginCommandLine, UserIconOrAction
from ._group_selection import ContactGroupSelection, HostGroupSelection, ServiceGroupSelection
from ._http_proxy import HTTPProxyInput, HTTPProxyReference
from ._permissions import PERMISSION_SECTION_WATO
from ._rulespec_groups import (
    RulespecGroupActiveChecks,
    RulespecGroupDatasourcePrograms,
    RulespecGroupDatasourceProgramsApps,
    RulespecGroupDatasourceProgramsCloud,
    RulespecGroupDatasourceProgramsCustom,
    RulespecGroupDatasourceProgramsHardware,
    RulespecGroupDatasourceProgramsOS,
    RulespecGroupDatasourceProgramsTesting,
    RulespecGroupIntegrateOtherServices,
    RulespecGroupVMCloudContainer,
)
from .pages._password_store_valuespecs import (
    IndividualOrStoredPassword,
    MigrateToIndividualOrStoredPassword,
    PasswordFromStore,
)

# Has to be kept for compatibility with pre 1.6 register_rule() and register_check_parameters()
# calls in the Setup plug-in context
subgroup_networking = RulespecGroupCheckParametersNetworking().sub_group_name
subgroup_storage = RulespecGroupCheckParametersStorage().sub_group_name
subgroup_os = RulespecGroupCheckParametersOperatingSystem().sub_group_name
subgroup_printing = RulespecGroupCheckParametersPrinters().sub_group_name
subgroup_environment = RulespecGroupCheckParametersEnvironment().sub_group_name
subgroup_applications = RulespecGroupCheckParametersApplications().sub_group_name
subgroup_virt = RulespecGroupCheckParametersVirtualization().sub_group_name
subgroup_hardware = RulespecGroupCheckParametersHardware().sub_group_name
subgroup_inventory = RulespecGroupCheckParametersDiscovery().sub_group_name


def register() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by built-in and also 3rd party plugins.

    Our built-in plug-in have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plug-ins for now.

    In the moment we define an official plug-in API, we can drop this and require all plug-ins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    for name, value in [
        ("PermissionSectionWATO", PERMISSION_SECTION_WATO),
        ("register_modules", register_modules),
        ("WatoModule", WatoModule),
        ("register_notification_parameters", register_notification_parameters),
        ("NotificationParameter", NotificationParameter),
        ("notification_parameter_registry", notification_parameter_registry),
        ("MainModuleTopicAgents", MainModuleTopicAgents),
        ("MainModuleTopicEvents", MainModuleTopicEvents),
        ("MainModuleTopicExporter", MainModuleTopicExporter),
        ("MainModuleTopicGeneral", MainModuleTopicGeneral),
        ("MainModuleTopicHosts", MainModuleTopicHosts),
        ("MainModuleTopicMaintenance", MainModuleTopicMaintenance),
        ("MainModuleTopicServices", MainModuleTopicServices),
        ("MainModuleTopicUsers", MainModuleTopicUsers),
        ("ContactGroupSelection", ContactGroupSelection),
        ("ServiceGroupSelection", ServiceGroupSelection),
        ("HostGroupSelection", HostGroupSelection),
        ("IndividualOrStoredPassword", IndividualOrStoredPassword),
        ("PasswordFromStore", PasswordFromStore),
        ("MigrateToIndividualOrStoredPassword", MigrateToIndividualOrStoredPassword),
        ("register_hook", register_hook),
        ("UserIconOrAction", UserIconOrAction),
        ("PluginCommandLine", PluginCommandLine),
        ("monitoring_macro_help", monitoring_macro_help),
        ("HTTPProxyInput", HTTPProxyInput),
        ("HTTPProxyReference", HTTPProxyReference),
    ]:
        api_module.__dict__[name] = wato_utils.__dict__[name] = value

    for name in (
        "ABCHostAttributeNagiosText",
        "ABCHostAttributeValueSpec",
        "ABCMainModule",
        "BinaryHostRulespec",
        "BinaryServiceRulespec",
        "CheckParameterRulespecWithItem",
        "CheckParameterRulespecWithoutItem",
        "HostRulespec",
        "is_wato_slave_site",
        "Levels",
        "main_module_registry",
        "MainModuleTopic",
        "make_confirm_link",
        "ManualCheckParameterRulespec",
        "MenuItem",
        "PredictiveLevels",
        "ReplicationPath",
        "RulespecGroup",
        "RulespecGroupCheckParametersApplications",
        "RulespecGroupCheckParametersDiscovery",
        "RulespecGroupCheckParametersEnvironment",
        "RulespecGroupCheckParametersHardware",
        "RulespecGroupCheckParametersNetworking",
        "RulespecGroupCheckParametersOperatingSystem",
        "RulespecGroupCheckParametersPrinters",
        "RulespecGroupCheckParametersStorage",
        "RulespecGroupCheckParametersVirtualization",
        "RulespecGroupEnforcedServicesApplications",
        "RulespecGroupEnforcedServicesEnvironment",
        "RulespecGroupEnforcedServicesHardware",
        "RulespecGroupEnforcedServicesNetworking",
        "RulespecGroupEnforcedServicesOperatingSystem",
        "RulespecGroupEnforcedServicesStorage",
        "RulespecGroupEnforcedServicesVirtualization",
        "RulespecSubGroup",
        "ServiceRulespec",
    ):
        api_module.__dict__[name] = cmk.gui.plugins.wato.utils.__dict__[name]
    for name, value in (
        ("mode_registry", mode_registry),
        ("mode_url", mode_url),
        ("redirect", redirect),
        ("WatoMode", WatoMode),
    ):
        api_module.__dict__[name] = value
    for name in (
        "IPMIParameters",
        "SNMPCredentials",
    ):
        api_module.__dict__[name] = cmk.gui.watolib.attributes.__dict__[name]
    for name in ("add_change",):
        api_module.__dict__[name] = cmk.gui.watolib.changes.__dict__[name]
    for name in (
        "ConfigDomainCACertificates",
        "ConfigDomainCore",
        "ConfigDomainGUI",
        "ConfigDomainOMD",
    ):
        api_module.__dict__[name] = cmk.gui.watolib.config_domains.__dict__[name]
    for name in ("ConfigHostname",):
        api_module.__dict__[name] = cmk.gui.watolib.config_hostname.__dict__[name]
    for name in (
        "host_attribute_registry",
        "host_attribute_topic_registry",
    ):
        api_module.__dict__[name] = cmk.gui.watolib.host_attributes.__dict__[name]
    for name in (
        "folder_preserving_link",
        "make_action_link",
    ):
        api_module.__dict__[name] = cmk.gui.watolib.hosts_and_folders.__dict__[name]
    for name in (
        "Rulespec",
        "rulespec_group_registry",
        "rulespec_registry",
    ):
        api_module.__dict__[name] = cmk.gui.watolib.rulespecs.__dict__[name]

    for name in ("LivestatusViaTCP",):
        api_module.__dict__[name] = cmk.gui.watolib.sites.__dict__[name]
    for name in ("TimeperiodSelection",):
        api_module.__dict__[name] = cmk.gui.watolib.timeperiods.__dict__[name]
    for name in (
        "HostnameTranslation",
        "ServiceDescriptionTranslation",
    ):
        api_module.__dict__[name] = cmk.gui.watolib.translation.__dict__[name]
    for name in (
        "user_script_choices",
        "user_script_title",
    ):
        api_module.__dict__[name] = cmk.gui.watolib.user_scripts.__dict__[name]
    for name in (
        "ABCConfigDomain",
        "config_domain_registry",
        "config_variable_group_registry",
        "config_variable_registry",
        "ConfigVariable",
        "ConfigVariableGroup",
        "register_configvar",
        "sample_config_generator_registry",
        "SampleConfigGenerator",
        "wato_fileheader",
    ):
        api_module.__dict__[name] = cmk.gui.watolib.config_domain_name.__dict__[name]
    for name in ("rule_option_elements",):
        api_module.__dict__[name] = cmk.gui.valuespec.__dict__[name]

    for name in (
        "multisite_dir",
        "site_neutral_path",
        "wato_root_dir",
    ):
        api_module.__dict__[name] = cmk.gui.watolib.utils.__dict__[name]

    for name, value in (
        ("RulespecGroupVMCloudContainer", RulespecGroupVMCloudContainer),
        ("RulespecGroupDatasourcePrograms", RulespecGroupDatasourcePrograms),
        ("RulespecGroupDatasourceProgramsOS", RulespecGroupDatasourceProgramsOS),
        ("RulespecGroupDatasourceProgramsApps", RulespecGroupDatasourceProgramsApps),
        ("RulespecGroupDatasourceProgramsCloud", RulespecGroupDatasourceProgramsCloud),
        ("RulespecGroupDatasourceProgramsCustom", RulespecGroupDatasourceProgramsCustom),
        ("RulespecGroupDatasourceProgramsHardware", RulespecGroupDatasourceProgramsHardware),
        ("RulespecGroupDatasourceProgramsTesting", RulespecGroupDatasourceProgramsTesting),
        ("RulespecGroupIntegrateOtherServices", RulespecGroupIntegrateOtherServices),
        ("RulespecGroupActiveChecks", RulespecGroupActiveChecks),
        ("MigrateToIndividualOrStoredPassword", MigrateToIndividualOrStoredPassword),
    ):
        datasource_programs.__dict__[name] = value
