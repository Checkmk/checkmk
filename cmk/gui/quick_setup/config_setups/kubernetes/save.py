#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.hostaddress import HostName
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.quick_setup.v0_unstable.predefined import complete
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.configuration_bundle_store import ConfigBundle
from cmk.gui.watolib.configuration_bundles import create_config_bundle, CreateBundleEntities
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.pending_changes import PendingChanges
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP

from .configuration import pull_configuration, with_dcd_host_deletion
from .constants import QUICK_SETUP_ID
from .settings import PullSettings, Settings


def save_configuration(
    settings: Settings,
    *,
    tree: FolderTree,
    acting_user: LoggedInUser,
    user_permissions: UserPermissions,
    pending_changes: PendingChanges,
    pprint_value: bool,
    debug: bool,
) -> None:
    """Save the source host and its related configuration using the bundle lifecycle."""
    acting_user.need_permission("wato.hosts")
    common = settings.common
    folder = tree.folder(common.host_path)
    folder.prepare_create_hosts(acting_user=acting_user)
    host_name = HostName(common.monitoring.host_name)
    host = complete.create_special_agent_host_from_form_data(host_name, common.site_id, folder)
    if isinstance(settings, PullSettings):
        acting_user.need_permission("wato.rulesets")
        acting_user.need_permission("wato.passwords")
        acting_user.need_permission("wato.edit_all_passwords")
        if not settings.base_url:
            raise ValueError("Enter the pull mode base URL before saving")
        entities = pull_configuration(
            bundle_id=common.bundle_id,
            host_name=host_name,
            host_path=folder.path(),
            site_id=common.site_id,
            base_url=settings.base_url,
            shared_secret=settings.shared_secret,
        )
    else:
        host["attributes"]["tag_agent"] = "cmk-agent"
        host["attributes"]["cmk_agent_connection"] = "push-agent"
        entities = CreateBundleEntities()
    entities.hosts = [host]
    entities.dcd_connections = with_dcd_host_deletion(
        complete.DCDHook.create_dcd_connections(common.bundle_id, common.site_id, host_name, folder)
    )
    create_config_bundle(
        tree,
        common.bundle_id,
        ConfigBundle(
            title=common.bundle_id,
            comment="",
            owned_by=acting_user.id,
            group=QUICK_SETUP_ID,
            program_id=PROGRAM_ID_QUICK_SETUP,
        ),
        entities,
        acting_user=acting_user,
        user_permissions=user_permissions,
        pprint_value=pprint_value,
        debug=debug,
        pending_changes=pending_changes,
    )
