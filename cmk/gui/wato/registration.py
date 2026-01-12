#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable

from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.main_menu import MegaMenuRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.painter.v0 import PainterRegistry
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.quick_setup.v0_unstable._registry import QuickSetupRegistry
from cmk.gui.sidebar import SnapinRegistry
from cmk.gui.type_defs import TopicMenuTopic
from cmk.gui.views.icon import IconRegistry
from cmk.gui.views.sorter import SorterRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.wato.page_handler import page_handler
from cmk.gui.watolib.analyze_configuration import ACTestRegistry
from cmk.gui.watolib.automation_commands import AutomationCommandRegistry
from cmk.gui.watolib.config_domain_name import (
    ConfigDomainRegistry,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
)
from cmk.gui.watolib.config_sync import ReplicationPathRegistry
from cmk.gui.watolib.groups import ContactGroupUsageFinderRegistry
from cmk.gui.watolib.host_rename import rename_host_in_rule_value_registry
from cmk.gui.watolib.hosts_and_folders import ajax_popup_host_action_menu
from cmk.gui.watolib.main_menu import MainModuleRegistry, MainModuleTopicRegistry
from cmk.gui.watolib.mode import ModeRegistry
from cmk.gui.watolib.notification_parameter import NotificationParameterRegistry
from cmk.gui.watolib.rulespecs import RulespecGroupRegistry
from cmk.gui.watolib.search import MatchItemGeneratorRegistry

from . import (
    _ac_tests,
    _check_mk_configuration,
    _main_module_topics,
    _main_modules,
    _notification_settings,
    _omd_configuration,
    _permissions,
    _pre_21_plugin_api,
    _rulespec_groups,
    _snapins,
    _tracing,
    filters,
    piggyback_hub,
)
from . import pages as wato_pages
from ._notification_parameter import registration as _notification_parameter_registration
from ._virtual_host_tree import VirtualHostTree
from .icons import DownloadAgentOutputIcon, DownloadSnmpWalkIcon, WatoIcon
from .pages._rule_conditions import PageAjaxDictHostTagConditionGetChoice
from .views import (
    PainterHostFilename,
    PainterWatoFolderAbs,
    PainterWatoFolderPlain,
    PainterWatoFolderRel,
    SorterWatoFolderAbs,
    SorterWatoFolderPlain,
    SorterWatoFolderRel,
)


def register(
    page_registry: PageRegistry,
    painter_registry: PainterRegistry,
    sorter_registry: SorterRegistry,
    icon_registry: IconRegistry,
    automation_command_registry: AutomationCommandRegistry,
    job_registry: BackgroundJobRegistry,
    filter_registry: FilterRegistry,
    mode_registry: ModeRegistry,
    quick_setup_registry: QuickSetupRegistry,
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    main_module_topic_registry: MainModuleTopicRegistry,
    main_module_registry: MainModuleRegistry,
    rulespec_group_registry: RulespecGroupRegistry,
    config_domain_registry: ConfigDomainRegistry,
    config_variable_registry: ConfigVariableRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    snapin_registry: SnapinRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
    mega_menu_registry: MegaMenuRegistry,
    ac_test_registry: ACTestRegistry,
    contact_group_usage_finder_registry: ContactGroupUsageFinderRegistry,
    notification_parameter_registry: NotificationParameterRegistry,
    replication_path_registry: ReplicationPathRegistry,
    user_menu_topics: Callable[[], list[TopicMenuTopic]],
) -> None:
    painter_registry.register(PainterHostFilename)
    painter_registry.register(PainterWatoFolderAbs)
    painter_registry.register(PainterWatoFolderRel)
    painter_registry.register(PainterWatoFolderPlain)
    sorter_registry.register(SorterWatoFolderAbs)
    sorter_registry.register(SorterWatoFolderRel)
    sorter_registry.register(SorterWatoFolderPlain)

    icon_registry.register(DownloadAgentOutputIcon)
    icon_registry.register(DownloadSnmpWalkIcon)
    icon_registry.register(WatoIcon)

    page_registry.register_page_handler("wato", page_handler)
    page_registry.register_page_handler("ajax_popup_host_action_menu", ajax_popup_host_action_menu)
    page_registry.register_page("ajax_dict_host_tag_condition_get_choice")(
        PageAjaxDictHostTagConditionGetChoice
    )

    filters.register(filter_registry)
    wato_pages.register(
        page_registry,
        mode_registry,
        quick_setup_registry,
        automation_command_registry,
        job_registry,
        match_item_generator_registry,
        mega_menu_registry,
        user_menu_topics,
    )
    _permissions.register(permission_section_registry, permission_registry)
    _main_module_topics.register(main_module_topic_registry)
    _main_modules.register(main_module_registry)
    _rulespec_groups.register(rulespec_group_registry)
    _pre_21_plugin_api.register()
    _check_mk_configuration.register(
        config_variable_registry,
        config_variable_group_registry,
        contact_group_usage_finder_registry,
        rename_host_in_rule_value_registry,
    )
    _ac_tests.register(ac_test_registry)
    _omd_configuration.register(
        config_domain_registry,
        config_variable_registry,
        replication_path_registry,
    )
    _tracing.register(config_variable_registry)
    _snapins.register(snapin_registry, match_item_generator_registry, mega_menu_registry)
    _notification_settings.register(config_variable_registry)
    _notification_parameter_registration.register(notification_parameter_registry)
    snapin_registry.register(VirtualHostTree)
    piggyback_hub.register(config_variable_registry)
