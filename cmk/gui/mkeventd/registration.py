#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.data_source import DataSourceRegistry
from cmk.gui.painter.v0.base import PainterRegistry
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.plugins.wato.utils.base_modes import ModeRegistry
from cmk.gui.valuespec import AutocompleterRegistry
from cmk.gui.views.icon import IconRegistry
from cmk.gui.watolib.config_domain_name import (
    ConfigDomainRegistry,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
    SampleConfigGeneratorRegistry,
)
from cmk.gui.watolib.main_menu import MainModuleRegistry
from cmk.gui.watolib.rulespecs import RulespecGroupRegistry, RulespecRegistry

from . import views, wato
from .autocompleters import service_levels_autocompleter, syslog_facilities_autocompleter
from .config_domain import ConfigDomainEventConsole
from .icon import MkeventdIcon
from .permission_section import PermissionSectionEventConsole

__all__ = ["register"]


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
    autocompleter_registry: AutocompleterRegistry,
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
    autocompleter_registry.register_expression("syslog_facilities")(syslog_facilities_autocompleter)
    autocompleter_registry.register_expression("service_levels")(service_levels_autocompleter)
