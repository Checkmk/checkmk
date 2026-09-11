#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""WATO aka Setup - The UI used to configure Checkmk

This package implements the backend rendered UI part of the setup, while `cmk.gui.watolib` holds the
backend business and persistence logic, which is also shared with the REST API.
"""

from cmk.gui.legacy_plugins import load_web_plugins

from ._check_mk_configuration import (
    ConfigVariableTrustedCertificateAuthorities as ConfigVariableTrustedCertificateAuthorities,
)
from ._check_mk_configuration import monitoring_macro_help as monitoring_macro_help
from ._check_mk_configuration import PluginCommandLine as PluginCommandLine
from ._group_selection import ContactGroupSelection as ContactGroupSelection
from ._group_selection import sorted_contact_group_choices as sorted_contact_group_choices
from ._levels import Levels as Levels
from ._levels import PredictiveLevels as PredictiveLevels
from ._main_module_topics import MainModuleTopicAgents as MainModuleTopicAgents
from ._main_module_topics import MainModuleTopicEvents as MainModuleTopicEvents
from ._main_module_topics import MainModuleTopicExporter as MainModuleTopicExporter
from ._main_module_topics import MainModuleTopicGeneral as MainModuleTopicGeneral
from ._main_module_topics import MainModuleTopicHosts as MainModuleTopicHosts
from ._main_module_topics import (
    MainModuleTopicMaintenance as MainModuleTopicMaintenance,
)
from ._main_module_topics import MainModuleTopicUsers as MainModuleTopicUsers
from ._permissions import PERMISSION_SECTION_WATO as PERMISSION_SECTION_WATO
from .pages._match_conditions import (
    fs_multifolder_host_rule_match_conditions as fs_multifolder_host_rule_match_conditions,
)
from .pages._match_conditions import (
    multifolder_host_rule_match_conditions as multifolder_host_rule_match_conditions,
)
from .pages._password_store_valuespecs import (
    IndividualOrStoredPassword as IndividualOrStoredPassword,
)
from .pages._password_store_valuespecs import (
    MigrateNotUpdatedToIndividualOrStoredPassword as MigrateNotUpdatedToIndividualOrStoredPassword,
)
from .pages._password_store_valuespecs import (
    MigrateToIndividualOrStoredPassword as MigrateToIndividualOrStoredPassword,
)
from .pages._rule_conditions import DictHostTagCondition as DictHostTagCondition
from .pages._simple_modes import SimpleEditMode as SimpleEditMode
from .pages._simple_modes import SimpleListMode as SimpleListMode
from .pages._simple_modes import SimpleModeType as SimpleModeType
from .pages._tile_menu import TileMenuRenderer as TileMenuRenderer
from .pages.user_profile.main_menu import default_user_menu_topics as default_user_menu_topics

_ = lambda message: message


def register() -> None:
    load_web_plugins("wato", globals())
