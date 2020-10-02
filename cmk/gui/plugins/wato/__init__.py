#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# flake8: noqa
# pylint: disable=unused-import

from cmk.utils.plugin_loader import load_plugins

#.
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   '----------------------------------------------------------------------'

from cmk.gui.watolib.wato_background_job import WatoBackgroundJob
from cmk.gui.plugins.wato.utils import (
    PermissionSectionWATO,
    ACResult,
    ACResultCRIT,
    ACResultOK,
    ACResultWARN,
    ACTest,
    ACTestCategories,
    ac_test_registry,
    add_change,
    add_replication_paths,
    ReplicationPath,
    CheckTypeSelection,
    config_domain_registry,
    ABCConfigDomain,
    ConfigDomainCore,
    ConfigDomainEventConsole,
    ConfigDomainGUI,
    ConfigDomainOMD,
    ConfigDomainCACertificates,
    HostAttributeTopicBasicSettings,
    HostAttributeTopicAddress,
    HostAttributeTopicDataSources,
    HostAttributeTopicHostTags,
    HostAttributeTopicNetworkScan,
    HostAttributeTopicManagementBoard,
    HostAttributeTopicCustomAttributes,
    HostAttributeTopicMetaData,
    host_attribute_topic_registry,
    ABCHostAttributeValueSpec,
    ABCHostAttributeNagiosText,
    host_attribute_registry,
    ABCEventsMode,
    folder_preserving_link,
    get_search_expression,
    ContactGroupSelection,
    ServiceGroupSelection,
    HostGroupSelection,
    HostnameTranslation,
    IndividualOrStoredPassword,
    passwordstore_choices,
    HTTPProxyReference,
    HTTPProxyInput,
    IPMIParameters,
    is_wato_slave_site,
    Levels,
    LivestatusViaTCP,
    MainMenu,
    make_action_link,
    may_edit_ruleset,
    MenuItem,
    mode_registry,
    monitoring_macro_help,
    multifolder_host_rule_match_conditions,
    multisite_dir,
    PluginCommandLine,
    PredictiveLevels,
    config_variable_group_registry,
    ConfigVariableGroup,
    config_variable_registry,
    ConfigVariable,
    register_configvar,
    register_check_parameters,
    main_module_registry,
    MainModuleTopic,
    MainModuleTopicHosts,
    MainModuleTopicServices,
    MainModuleTopicBI,
    MainModuleTopicAgents,
    MainModuleTopicEvents,
    MainModuleTopicUsers,
    MainModuleTopicGeneral,
    MainModuleTopicMaintenance,
    MainModuleTopicCustom,
    MainModule,
    WatoModule,
    register_modules,
    register_notification_parameters,
    notification_parameter_registry,
    NotificationParameter,
    rulespec_registry,
    Rulespec,
    HostRulespec,
    ServiceRulespec,
    BinaryHostRulespec,
    BinaryServiceRulespec,
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    ManualCheckParameterRulespec,
    RulespecGroupManualChecksNetworking,
    RulespecGroupManualChecksApplications,
    RulespecGroupManualChecksEnvironment,
    RulespecGroupManualChecksOperatingSystem,
    RulespecGroupManualChecksHardware,
    RulespecGroupManualChecksStorage,
    RulespecGroupManualChecksVirtualization,
    rulespec_group_registry,
    RulespecGroup,
    RulespecSubGroup,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
    RulespecGroupCheckParametersHardware,
    RulespecGroupCheckParametersNetworking,
    RulespecGroupCheckParametersOperatingSystem,
    RulespecGroupCheckParametersPrinters,
    RulespecGroupCheckParametersStorage,
    RulespecGroupCheckParametersVirtualization,
    FullPathFolderChoice,
    rule_option_elements,
    search_form,
    ServiceDescriptionTranslation,
    site_neutral_path,
    SNMPCredentials,
    sort_sites,
    TimeperiodSelection,
    transform_simple_to_multi_host_rule_match_conditions,
    UserIconOrAction,
    user_script_choices,
    user_script_title,
    wato_confirm,
    wato_fileheader,
    register_hook,
    WatoMode,
    ActionResult,
    SimpleModeType,
    SimpleListMode,
    SimpleEditMode,
    wato_root_dir,
    ConfigHostname,
    SiteBackupJobs,
    HostTagCondition,
    DictHostTagCondition,
    get_hostnames_from_checkboxes,
    get_hosts_from_checkboxes,
    get_check_information,
    SampleConfigGenerator,
    sample_config_generator_registry,
)

#.
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'

load_plugins(__file__, __package__)

import cmk.gui.plugins.wato.check_parameters
