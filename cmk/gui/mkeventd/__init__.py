#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.painters.v0.base import PainterRegistry
from cmk.gui.permissions import PermissionSectionRegistry
from cmk.gui.plugins.watolib.utils import ConfigDomainRegistry, SampleConfigGeneratorRegistry
from cmk.gui.views.data_source import DataSourceRegistry

from . import views, wato
from .config_domain import ConfigDomainEventConsole
from .defines import action_whats, phase_names, syslog_facilities, syslog_priorities
from .helpers import action_choices, service_levels
from .livestatus import execute_command
from .permission_section import PermissionSectionEventConsole
from .rule_matching import event_rule_matches


def register(
    permission_section_registry: PermissionSectionRegistry,
    data_source_registry: DataSourceRegistry,
    painter_registry: PainterRegistry,
    config_domain_registry: ConfigDomainRegistry,
    sample_config_generator_registry: SampleConfigGeneratorRegistry,
) -> None:
    views.register(data_source_registry, painter_registry)
    wato.register(sample_config_generator_registry)
    permission_section_registry.register(PermissionSectionEventConsole)
    config_domain_registry.register(ConfigDomainEventConsole)


__all__ = [
    "register",
    "event_rule_matches",
    "syslog_priorities",
    "syslog_facilities",
    "phase_names",
    "action_whats",
    "PermissionSectionEventConsole",
    "service_levels",
    "action_choices",
    "execute_command",
    "ConfigDomainEventConsole",
]
