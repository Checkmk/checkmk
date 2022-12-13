#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.plugins.wato.utils.base_modes import ModeRegistry
from cmk.gui.plugins.watolib.utils import (
    ConfigDomainRegistry,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
    SampleConfigGeneratorRegistry,
)
from cmk.gui.views.data_source import DataSourceRegistry
from cmk.gui.views.icon import IconRegistry
from cmk.gui.views.painter.v0.base import PainterRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry
from cmk.gui.watolib.rulespecs import RulespecGroupRegistry, RulespecRegistry

from . import views, wato
from .config_domain import ConfigDomainEventConsole
from .defines import action_whats, phase_names, syslog_facilities, syslog_priorities
from .helpers import action_choices, service_levels
from .icon import MkeventdIcon
from .livestatus import execute_command
from .permission_section import PermissionSectionEventConsole
from .rule_matching import event_rule_matches


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    data_source_registry: DataSourceRegistry,
    painter_registry: PainterRegistry,
    icon_registry: IconRegistry,
    config_domain_registry: ConfigDomainRegistry,
    sample_config_generator_registry: SampleConfigGeneratorRegistry,
    mode_registry: ModeRegistry,
    main_module_registry: MainModuleRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    config_variable_registry: ConfigVariableRegistry,
    rulespec_group_registry: RulespecGroupRegistry,
    rulespec_registry: RulespecRegistry,
) -> None:
    views.register(data_source_registry, painter_registry)
    icon_registry.register(MkeventdIcon)
    wato.register(
        permission_registry,
        sample_config_generator_registry,
        mode_registry,
        main_module_registry,
        config_variable_group_registry,
        config_variable_registry,
        rulespec_group_registry,
        rulespec_registry,
    )
    permission_section_registry.register(PermissionSectionEventConsole)
    config_domain_registry.register(ConfigDomainEventConsole)


__all__ = [
    "register",
    "event_rule_matches",
    "syslog_priorities",
    "syslog_facilities",
    "phase_names",
    "action_whats",
    "service_levels",
    "action_choices",
    "execute_command",
    "ConfigDomainEventConsole",
]
