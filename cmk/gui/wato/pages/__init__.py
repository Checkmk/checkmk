#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.version import Edition, edition

from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.watolib.automation_commands import AutomationCommandRegistry
from cmk.gui.watolib.mode import ModeRegistry

from . import (
    activate_changes,
    analyze_configuration,
    audit_log,
    automation,
    bulk_discovery,
    bulk_edit,
    bulk_import,
    check_catalog,
    custom_attributes,
    diagnostics,
    download_agents,
    fetch_agent_output,
    folders,
    global_settings,
    groups,
    gui_timings,
    host_diagnose,
    host_rename,
    hosts,
    ldap,
    not_implemented,
    notifications,
    object_parameters,
    parentscan,
    password_store,
    pattern_editor,
    predefined_conditions,
    random_hosts,
    read_only,
    roles,
    rulesets,
    search,
    services,
    sites,
    tags,
    timeperiods,
    user_migrate,
    user_profile,
    users,
)
from ._password_store_valuespecs import (
    IndividualOrStoredPassword as IndividualOrStoredPassword,
)
from ._password_store_valuespecs import (
    MigrateNotUpdatedToIndividualOrStoredPassword as MigrateNotUpdatedToIndividualOrStoredPassword,
)
from ._password_store_valuespecs import (
    MigrateToIndividualOrStoredPassword as MigrateToIndividualOrStoredPassword,
)


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    automation_command_registry: AutomationCommandRegistry,
    job_registry: BackgroundJobRegistry,
) -> None:
    activate_changes.register(page_registry, mode_registry, automation_command_registry)
    analyze_configuration.register(mode_registry)
    audit_log.register(mode_registry)
    automation.register(page_registry)
    bulk_discovery.register(mode_registry)
    bulk_edit.register(mode_registry)
    bulk_import.register(mode_registry)
    check_catalog.register(mode_registry)
    custom_attributes.register(mode_registry)
    diagnostics.register(page_registry, mode_registry, automation_command_registry, job_registry)
    download_agents.register(mode_registry)
    fetch_agent_output.register(page_registry, automation_command_registry, job_registry)
    folders.register(page_registry, mode_registry)
    global_settings.register(mode_registry)
    groups.register(mode_registry)
    gui_timings.register(page_registry)
    host_diagnose.register(page_registry, mode_registry)
    host_rename.register(mode_registry)
    hosts.register(mode_registry)
    not_implemented.register(mode_registry)
    notifications.register(mode_registry, automation_command_registry)
    object_parameters.register(mode_registry)
    parentscan.register(mode_registry)
    password_store.register(mode_registry)
    pattern_editor.register(mode_registry)
    predefined_conditions.register(mode_registry)
    random_hosts.register(mode_registry)
    read_only.register(mode_registry)
    rulesets.register(mode_registry)
    search.register(mode_registry)
    services.register(page_registry, mode_registry, automation_command_registry)
    sites.register(page_registry, mode_registry)
    tags.register(mode_registry)
    timeperiods.register(mode_registry)
    user_migrate.register(mode_registry)
    user_profile.register(page_registry)
    users.register(mode_registry)

    if edition() is not Edition.CSE:  # disabled in CSE
        ldap.register(mode_registry)
        roles.register(mode_registry)
