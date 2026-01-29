#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Register the built-in topics. These are the ones that may be referenced by different Setup
plugins. Additional individual plug-ins are allowed to create their own topics."""

from cmk.gui.i18n import _l
from cmk.gui.type_defs import DynamicIconName
from cmk.gui.watolib.main_menu import MainModuleTopic, MainModuleTopicRegistry


def register(main_module_topic_registry: MainModuleTopicRegistry) -> None:
    main_module_topic_registry.register(MainModuleTopicQuickSetup)
    main_module_topic_registry.register(MainModuleTopicHosts)
    main_module_topic_registry.register(MainModuleTopicServices)
    main_module_topic_registry.register(MainModuleTopicAgents)
    main_module_topic_registry.register(MainModuleTopicEvents)
    main_module_topic_registry.register(MainModuleTopicUsers)
    main_module_topic_registry.register(MainModuleTopicGeneral)
    main_module_topic_registry.register(MainModuleTopicMaintenance)
    main_module_topic_registry.register(MainModuleTopicExporter)


MainModuleTopicHosts = MainModuleTopic(
    name="hosts",
    title=_l("Hosts"),
    icon_name=DynamicIconName("topic_hosts"),
    sort_index=10,
)

MainModuleTopicServices = MainModuleTopic(
    name="services",
    title=_l("Services"),
    icon_name=DynamicIconName("topic_services"),
    sort_index=20,
)

MainModuleTopicAgents = MainModuleTopic(
    name="agents",
    title=_l("Agents"),
    icon_name=DynamicIconName("topic_agents"),
    sort_index=40,
)

MainModuleTopicQuickSetup = MainModuleTopic(
    name="quick_setups",
    title=_l("Quick Setup"),
    icon_name=DynamicIconName("topic_quick_setups"),
    sort_index=45,
)

MainModuleTopicEvents = MainModuleTopic(
    name="events",
    title=_l("Events"),
    icon_name=DynamicIconName("topic_events"),
    sort_index=50,
)

MainModuleTopicUsers = MainModuleTopic(
    name="users",
    title=_l("Users"),
    icon_name=DynamicIconName("topic_users"),
    sort_index=60,
)

MainModuleTopicGeneral = MainModuleTopic(
    name="general",
    title=_l("General"),
    icon_name=DynamicIconName("topic_general"),
    sort_index=70,
)

MainModuleTopicMaintenance = MainModuleTopic(
    name="maintenance",
    title=_l("Maintenance"),
    icon_name=DynamicIconName("topic_maintenance"),
    sort_index=80,
)

MainModuleTopicExporter = MainModuleTopic(
    name="exporter",
    title=_l("Connectors"),
    icon_name=DynamicIconName("topic_exporter"),
    sort_index=150,
)
