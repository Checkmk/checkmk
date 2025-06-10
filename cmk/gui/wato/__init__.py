#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""WATO aka Setup - The UI used to configure Checkmk

This package implements the backend rendered UI part of the setup, while `cmk.gui.watolib` holds the
backend business and persistence logic, which is also shared with the REST API.
"""

# A huge number of imports are here to be compatible with old GUI plugins. Once we dropped support
# for them, we can remove this here and the imports
# ruff: noqa: F401

from cmk.ccc.exceptions import MKGeneralException

import cmk.utils.paths

import cmk.gui.valuespec
import cmk.gui.view_utils
import cmk.gui.watolib.attributes
import cmk.gui.watolib.changes
import cmk.gui.watolib.config_domain_name
import cmk.gui.watolib.config_domains
import cmk.gui.watolib.config_hostname
import cmk.gui.watolib.host_attributes
import cmk.gui.watolib.hosts_and_folders
import cmk.gui.watolib.network_scan
import cmk.gui.watolib.read_only
import cmk.gui.watolib.rulespecs
import cmk.gui.watolib.sites
import cmk.gui.watolib.timeperiods
import cmk.gui.watolib.translation
import cmk.gui.watolib.user_scripts
import cmk.gui.watolib.utils
from cmk.gui import background_job, forms, gui_background_job, sites, userdb, utils, watolib, weblib
from cmk.gui.hooks import register_hook as register_hook
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.pages import Page, page_registry
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.table import table_element
from cmk.gui.type_defs import PermissionName
from cmk.gui.utils.html import HTML
from cmk.gui.valuespec import Age as Age
from cmk.gui.valuespec import Alternative as Alternative
from cmk.gui.valuespec import Dictionary as Dictionary
from cmk.gui.valuespec import Filesize as Filesize
from cmk.gui.valuespec import FixedValue as FixedValue
from cmk.gui.valuespec import ListOfStrings as ListOfStrings
from cmk.gui.valuespec import MonitoredHostname as MonitoredHostname
from cmk.gui.valuespec import MonitoringState as MonitoringState
from cmk.gui.valuespec import Password as Password
from cmk.gui.valuespec import Percentage as Percentage
from cmk.gui.valuespec import RegExpUnicode as RegExpUnicode
from cmk.gui.valuespec import TextAscii as TextAscii
from cmk.gui.valuespec import TextUnicode as TextUnicode
from cmk.gui.valuespec import Transform as Transform
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.wato._main_module_topics import MainModuleTopicAgents as MainModuleTopicAgents
from cmk.gui.wato._main_module_topics import MainModuleTopicEvents as MainModuleTopicEvents
from cmk.gui.wato._main_module_topics import MainModuleTopicExporter as MainModuleTopicExporter
from cmk.gui.wato._main_module_topics import MainModuleTopicGeneral as MainModuleTopicGeneral
from cmk.gui.wato._main_module_topics import MainModuleTopicHosts as MainModuleTopicHosts
from cmk.gui.wato._main_module_topics import (
    MainModuleTopicMaintenance as MainModuleTopicMaintenance,
)
from cmk.gui.wato._main_module_topics import MainModuleTopicServices as MainModuleTopicServices
from cmk.gui.wato._main_module_topics import MainModuleTopicUsers as MainModuleTopicUsers
from cmk.gui.wato.page_handler import page_handler
from cmk.gui.watolib.activate_changes import update_config_generation
from cmk.gui.watolib.hosts_and_folders import ajax_popup_host_action_menu
from cmk.gui.watolib.main_menu import MenuItem, register_modules, WatoModule
from cmk.gui.watolib.mode import mode_registry, mode_url, redirect, WatoMode
from cmk.gui.watolib.notification_parameter import (
    notification_parameter_registry as notification_parameter_registry,
)
from cmk.gui.watolib.notification_parameter import NotificationParameter as NotificationParameter
from cmk.gui.watolib.notification_parameter import (
    NotificationParameterRegistry as NotificationParameterRegistry,
)
from cmk.gui.watolib.notification_parameter import register_notification_parameters
from cmk.gui.watolib.sites import LivestatusViaTCP
from cmk.gui.watolib.translation import HostnameTranslation

from ._check_mk_configuration import monitoring_macro_help as monitoring_macro_help
from ._check_mk_configuration import PluginCommandLine as PluginCommandLine
from ._check_mk_configuration import UserIconOrAction as UserIconOrAction
from ._check_plugin_selection import CheckPluginSelection as CheckPluginSelection
from ._group_selection import ContactGroupSelection as ContactGroupSelection
from ._group_selection import HostGroupSelection as HostGroupSelection
from ._group_selection import ServiceGroupSelection as ServiceGroupSelection
from ._http_proxy import HTTPProxyReference as HTTPProxyReference
from ._levels import Levels as Levels
from ._levels import PredictiveLevels as PredictiveLevels
from ._permissions import PERMISSION_SECTION_WATO as PERMISSION_SECTION_WATO
from ._rulespec_groups import RulespecGroupActiveChecks as RulespecGroupActiveChecks
from ._rulespec_groups import (
    RulespecGroupCheckParametersApplications as RulespecGroupCheckParametersApplications,
)
from ._rulespec_groups import (
    RulespecGroupCheckParametersDiscovery as RulespecGroupCheckParametersDiscovery,
)
from ._rulespec_groups import (
    RulespecGroupCheckParametersEnvironment as RulespecGroupCheckParametersEnvironment,
)
from ._rulespec_groups import (
    RulespecGroupCheckParametersHardware as RulespecGroupCheckParametersHardware,
)
from ._rulespec_groups import (
    RulespecGroupCheckParametersNetworking as RulespecGroupCheckParametersNetworking,
)
from ._rulespec_groups import (
    RulespecGroupCheckParametersOperatingSystem as RulespecGroupCheckParametersOperatingSystem,
)
from ._rulespec_groups import (
    RulespecGroupCheckParametersPrinters as RulespecGroupCheckParametersPrinters,
)
from ._rulespec_groups import (
    RulespecGroupCheckParametersStorage as RulespecGroupCheckParametersStorage,
)
from ._rulespec_groups import (
    RulespecGroupCheckParametersVirtualization as RulespecGroupCheckParametersVirtualization,
)
from ._rulespec_groups import RulespecGroupDatasourcePrograms as RulespecGroupDatasourcePrograms
from ._rulespec_groups import (
    RulespecGroupDatasourceProgramsApps as RulespecGroupDatasourceProgramsApps,
)
from ._rulespec_groups import (
    RulespecGroupDatasourceProgramsCloud as RulespecGroupDatasourceProgramsCloud,
)
from ._rulespec_groups import (
    RulespecGroupDatasourceProgramsCustom as RulespecGroupDatasourceProgramsCustom,
)
from ._rulespec_groups import (
    RulespecGroupDatasourceProgramsHardware as RulespecGroupDatasourceProgramsHardware,
)
from ._rulespec_groups import RulespecGroupDatasourceProgramsOS as RulespecGroupDatasourceProgramsOS
from ._rulespec_groups import (
    RulespecGroupDatasourceProgramsTesting as RulespecGroupDatasourceProgramsTesting,
)
from ._rulespec_groups import (
    RulespecGroupDiscoveryCheckParameters as RulespecGroupDiscoveryCheckParameters,
)
from ._rulespec_groups import (
    RulespecGroupIntegrateOtherServices as RulespecGroupIntegrateOtherServices,
)
from ._rulespec_groups import RulespecGroupVMCloudContainer as RulespecGroupVMCloudContainer
from .pages import IndividualOrStoredPassword as IndividualOrStoredPassword
from .pages import (
    MigrateNotUpdatedToIndividualOrStoredPassword as MigrateNotUpdatedToIndividualOrStoredPassword,
)
from .pages import MigrateToIndividualOrStoredPassword as MigrateToIndividualOrStoredPassword
from .pages._match_conditions import FullPathFolderChoice as FullPathFolderChoice
from .pages._match_conditions import (
    multifolder_host_rule_match_conditions as multifolder_host_rule_match_conditions,
)
from .pages._password_store_valuespecs import PasswordFromStore as PasswordFromStore
from .pages._rule_conditions import DictHostTagCondition as DictHostTagCondition
from .pages._simple_modes import SimpleEditMode as SimpleEditMode
from .pages._simple_modes import SimpleListMode as SimpleListMode
from .pages._simple_modes import SimpleModeType as SimpleModeType
from .pages._tile_menu import TileMenuRenderer as TileMenuRenderer
from .pages.user_profile.main_menu import default_user_menu_topics as default_user_menu_topics

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


def load_plugins() -> None:
    """Plug-in initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    # Initialize watolib things which are needed before loading the Setup plugins.
    # This also loads the watolib plugins.
    watolib.load_watolib_plugins()

    utils.load_web_plugins("wato", globals())
