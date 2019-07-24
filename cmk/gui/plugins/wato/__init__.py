#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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

from cmk.gui.plugins.wato.utils import (
    PermissionSectionWATO,
    ACResultCRIT,
    ACResultOK,
    ACResultWARN,
    ACTest,
    ACTestCategories,
    ac_test_registry,
    add_change,
    add_replication_paths,
    global_buttons,
    changelog_button,
    home_button,
    host_status_button,
    CheckTypeSelection,
    config_domain_registry,
    ConfigDomain,
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
    EventsMode,
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
    WatoBackgroundJob,
    wato_confirm,
    wato_fileheader,
    register_hook,
    WatoMode,
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
