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

from cmk.plugin_loader import load_plugins

#.
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   '----------------------------------------------------------------------'

# TODO: Would be better to replace this star import with an explicit list of
# names needed for the plugins. Then we would have something like an official
# plugin API. At least a list of names that are intended to be used by plugins.
from cmk.gui.plugins.wato.utils import (
    ACResultCRIT,
    ACResultOK,
    ACResultWARN,
    ACTest,
    ACTestCategories,
    ac_test_registry,
    add_change,
    add_replication_paths,
    changelog_button,
    CheckTypeSelection,
    ConfigDomain,
    ConfigDomainCore,
    ConfigDomainEventConsole,
    ConfigDomainGUI,
    ConfigDomainOMD,
    configvar_order,
    ContactGroupsAttribute,
    declare_host_attribute,
    EventsMode,
    folder_preserving_link,
    get_search_expression,
    global_buttons,
    GroupSelection,
    home_button,
    HostnameTranslation,
    IndividualOrStoredPassword,
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
    NagiosTextAttribute,
    PluginCommandLine,
    PredictiveLevels,
    register_check_parameters,
    register_configvar,
    register_configvar_group,
    register_modules,
    register_notification_parameters,
    register_rule,
    register_rulegroup,
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
    ValueSpecAttribute,
    vs_bulk_discovery,
    WatoBackgroundJob,
    wato_confirm,
    wato_fileheader,
    WatoMode,
    WatoModule,
    wato_root_dir,
    wato_styles,
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
