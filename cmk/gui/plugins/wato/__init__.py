#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# flake8: noqa
# pylint: disable=unused-import

from cmk.utils.plugin_loader import load_plugins

from cmk.gui.plugins.wato.utils import (
    ABCConfigDomain,
    ABCEventsMode,
    ABCHostAttributeNagiosText,
    ABCHostAttributeValueSpec,
    ABCMainModule,
    ac_test_registry,
    ACResult,
    ACResultCRIT,
    ACResultOK,
    ACResultWARN,
    ACTest,
    ACTestCategories,
    add_change,
    add_replication_paths,
    BinaryHostRulespec,
    BinaryServiceRulespec,
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    config_domain_registry,
    config_variable_group_registry,
    config_variable_registry,
    ConfigDomainCACertificates,
    ConfigDomainCore,
    ConfigDomainEventConsole,
    ConfigDomainGUI,
    ConfigDomainOMD,
    ConfigHostname,
    ConfigVariable,
    ConfigVariableGroup,
    ContactGroupSelection,
    DictHostTagCondition,
    flash,
    folder_preserving_link,
    FullPathFolderChoice,
    get_check_information,
    get_hostnames_from_checkboxes,
    get_hosts_from_checkboxes,
    get_search_expression,
    host_attribute_registry,
    host_attribute_topic_registry,
    HostAttributeTopicAddress,
    HostAttributeTopicBasicSettings,
    HostAttributeTopicCustomAttributes,
    HostAttributeTopicDataSources,
    HostAttributeTopicHostTags,
    HostAttributeTopicManagementBoard,
    HostAttributeTopicMetaData,
    HostAttributeTopicNetworkScan,
    HostGroupSelection,
    HostnameTranslation,
    HostRulespec,
    HostTagCondition,
    HTTPProxyInput,
    HTTPProxyReference,
    IndividualOrStoredPassword,
    IPMIParameters,
    is_wato_slave_site,
    Levels,
    LivestatusViaTCP,
    main_module_registry,
    MainMenu,
    MainModuleTopic,
    MainModuleTopicAgents,
    MainModuleTopicBI,
    MainModuleTopicCustom,
    MainModuleTopicEvents,
    MainModuleTopicGeneral,
    MainModuleTopicHosts,
    MainModuleTopicMaintenance,
    MainModuleTopicServices,
    MainModuleTopicUsers,
    make_action_link,
    make_confirm_link,
    make_diff_text,
    ManualCheckParameterRulespec,
    MenuItem,
    mode_registry,
    mode_url,
    monitoring_macro_help,
    multifolder_host_rule_match_conditions,
    multisite_dir,
    notification_parameter_registry,
    NotificationParameter,
    PasswordFromStore,
    PermissionSectionWATO,
    PluginCommandLine,
    PredictiveLevels,
    redirect,
    register_check_parameters,
    register_configvar,
    register_hook,
    register_modules,
    register_notification_parameters,
    ReplicationPath,
    rule_option_elements,
    Rulespec,
    rulespec_group_registry,
    rulespec_registry,
    RulespecGroup,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
    RulespecGroupCheckParametersHardware,
    RulespecGroupCheckParametersNetworking,
    RulespecGroupCheckParametersOperatingSystem,
    RulespecGroupCheckParametersPrinters,
    RulespecGroupCheckParametersStorage,
    RulespecGroupCheckParametersVirtualization,
    RulespecGroupEnforcedServicesApplications,
    RulespecGroupEnforcedServicesEnvironment,
    RulespecGroupEnforcedServicesHardware,
    RulespecGroupEnforcedServicesNetworking,
    RulespecGroupEnforcedServicesOperatingSystem,
    RulespecGroupEnforcedServicesStorage,
    RulespecGroupEnforcedServicesVirtualization,
    RulespecSubGroup,
    sample_config_generator_registry,
    SampleConfigGenerator,
    search_form,
    ServiceDescriptionTranslation,
    ServiceGroupSelection,
    ServiceRulespec,
    SimpleEditMode,
    SimpleListMode,
    SimpleModeType,
    site_neutral_path,
    SiteBackupJobs,
    SNMPCredentials,
    sort_sites,
    TimeperiodSelection,
    transform_simple_to_multi_host_rule_match_conditions,
    user_script_choices,
    user_script_title,
    UserIconOrAction,
    valuespec_check_plugin_selection,
    wato_fileheader,
    wato_root_dir,
    WatoMode,
    WatoModule,
)
from cmk.gui.type_defs import ActionResult
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob

# .
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   '----------------------------------------------------------------------'


# .
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'

load_plugins(__file__, __package__)
