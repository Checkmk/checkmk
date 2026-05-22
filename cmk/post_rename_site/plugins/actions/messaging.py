#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk import messaging
from cmk.ccc.i18n import _
from cmk.ccc.site import omd_site, SiteId
from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.user_sites import activation_sites
from cmk.gui.watolib.activate_changes import get_all_replicated_sites
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.broker_certificates import (
    clean_remote_sites_certs,
)
from cmk.gui.watolib.config_domain_name import GUI
from cmk.gui.watolib.pending_changes import (
    Change,
    ChangeScope,
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.post_rename_site.internal import (
    Name,
    RenameAction,
    SortIndex,
    Title,
)
from cmk.utils import paths


def update_broker_config(old_site_id: SiteId, new_site_id: SiteId, logger: Logger) -> None:
    """
    Cleanup broker certificates of the renamed site and of the replicated sites
    so that they can be re-created at the next changes activation.

    Also add a changes for the connected sites, so that the definitions file is
    created with the new names.
    """
    logger.debug("Deleting broker certificates of site %s", old_site_id)
    messaging.site_cert_file(paths.omd_root).unlink(missing_ok=True)
    logger.debug("Deleting broker certificates of replicated sites")
    clean_remote_sites_certs(kept_sites=[])

    logger.debug("Add changes for the connected sites")
    PendingChanges(
        activation_sites=activation_sites(active_config.sites),
        local_site=omd_site(),
        acting_user=user.id,
        store=PendingChangesStore(),
        hooks=(make_audit_log_change_hook(use_git=False), index_update_change_hook),
    ).add(
        Change(
            action_name="edit-sites",
            text=_("Renamed site %s") % old_site_id,
            force_restart=True,
            domains=[GUI],
        ),
        ChangeScope.sites(get_all_replicated_sites(activation_sites(active_config.sites))),
    )


rename_action_messaging = RenameAction(
    name=Name("messaging"),
    title=Title("Broker certificates and configuration"),
    sort_index=SortIndex(10),
    run=update_broker_config,
)
