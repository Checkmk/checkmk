#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.ccc.i18n import _
from cmk.ccc.site import SiteId

from cmk.utils import paths

from cmk.gui.logged_in import user
from cmk.gui.watolib.activate_changes import get_all_replicated_sites
from cmk.gui.watolib.broker_certificates import (
    clean_remote_sites_certs,
)
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.config_domains import ConfigDomainGUI

from cmk import messaging
from cmk.post_rename_site.registry import rename_action_registry, RenameAction


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
    add_change(
        action_name="edit-sites",
        text=_("Renamed site %s") % old_site_id,
        user_id=user.id,
        domains=[ConfigDomainGUI()],
        sites=list(get_all_replicated_sites()),
        need_restart=True,
        use_git=False,
    )


rename_action_registry.register(
    RenameAction(
        name="messaging",
        title=_("Broker certificates and configuration"),
        sort_index=10,
        handler=update_broker_config,
    )
)
