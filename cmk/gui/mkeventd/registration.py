#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.gui.data_source import DataSourceRegistry
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.painter.v0 import PainterRegistry
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.sidebar import SnapinRegistry
from cmk.gui.valuespec import AutocompleterRegistry
from cmk.gui.views.command import CommandRegistry
from cmk.gui.views.icon import IconRegistry
from cmk.gui.views.sorter import SorterRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.watolib.config_domain_name import (
    ConfigDomainRegistry,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
    SampleConfigGeneratorRegistry,
)
from cmk.gui.watolib.config_sync import ReplicationPathRegistry
from cmk.gui.watolib.groups import ContactGroupUsageFinderRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry
from cmk.gui.watolib.mode import ModeRegistry
from cmk.gui.watolib.notification_parameter import NotificationParameterRegistry
from cmk.gui.watolib.rulespecs import RulespecGroupRegistry, RulespecRegistry
from cmk.gui.watolib.search import match_item_generator_registry
from cmk.gui.watolib.timeperiods import TimeperiodUsageFinderRegistry

from . import _filters, views, wato
from ._find_usage import (
    find_timeperiod_usage_in_ec_rules,
    find_usages_of_contact_group_in_ec_rules,
    find_usages_of_contact_group_in_mkeventd_notify_contactgroup,
)
from ._openapi import register as openapi_register
from ._sidebar_snapin import SidebarSnapinEventConsole
from .autocompleters import service_levels_autocompleter, syslog_facilities_autocompleter
from .icon import MkeventdIcon

__all__ = ["register"]

from .permission_section import PERMISSION_SECTION_EVENT_CONSOLE


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    data_source_registry: DataSourceRegistry,
    painter_registry: PainterRegistry,
    command_registry: CommandRegistry,
    sorter_registry: SorterRegistry,
    icon_registry: IconRegistry,
    config_domain_registry: ConfigDomainRegistry,
    sample_config_generator_registry: SampleConfigGeneratorRegistry,
    mode_registry: ModeRegistry,
    main_module_registry: MainModuleRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    config_variable_registry: ConfigVariableRegistry,
    rulespec_group_registry: RulespecGroupRegistry,
    rulespec_registry: RulespecRegistry,
    autocompleter_registry: AutocompleterRegistry,
    filter_registry: FilterRegistry,
    notification_parameter_registry: NotificationParameterRegistry,
    snapin_registry: SnapinRegistry,
    contact_group_usage_finder_registry: ContactGroupUsageFinderRegistry,
    timeperiod_usage_finder_registry: TimeperiodUsageFinderRegistry,
    endpoint_registry: EndpointRegistry,
    replication_path_registry: ReplicationPathRegistry,
    save_active_config: Callable[[], None],
    *,
    ignore_duplicate_endpoints: bool = False,
) -> None:
    views.register(
        data_source_registry,
        painter_registry,
        command_registry,
        sorter_registry,
        permission_registry,
    )
    icon_registry.register(MkeventdIcon)
    wato.register(
        permission_registry,
        sample_config_generator_registry,
        mode_registry,
        main_module_registry,
        config_domain_registry,
        save_active_config,
        config_variable_group_registry,
        config_variable_registry,
        rulespec_group_registry,
        rulespec_registry,
        match_item_generator_registry,
        notification_parameter_registry,
        replication_path_registry,
    )
    permission_section_registry.register(PERMISSION_SECTION_EVENT_CONSOLE)
    autocompleter_registry.register_autocompleter(
        "syslog_facilities", syslog_facilities_autocompleter
    )
    autocompleter_registry.register_autocompleter("service_levels", service_levels_autocompleter)
    _filters.register(filter_registry)
    snapin_registry.register(SidebarSnapinEventConsole)
    contact_group_usage_finder_registry.register(find_usages_of_contact_group_in_ec_rules)
    contact_group_usage_finder_registry.register(
        find_usages_of_contact_group_in_mkeventd_notify_contactgroup
    )
    timeperiod_usage_finder_registry.register(find_timeperiod_usage_in_ec_rules)
    openapi_register(endpoint_registry, ignore_duplicates=ignore_duplicate_endpoints)
