#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from livestatus import SiteConfiguration

from cmk.ccc.site import omd_site, SiteId

from cmk.gui.config import active_config
from cmk.gui.site_config import is_wato_slave_site, site_is_local

UserSyncConfig = Literal["all", "master"] | tuple[Literal["list"], list[str]] | None


def user_sync_config() -> UserSyncConfig:
    # use global option as default for reading legacy options and on remote site
    # for reading the value set by the Setup master site
    default_cfg = user_sync_default_config(
        site_config := active_config.sites[omd_site()], omd_site()
    )
    return site_config.get("user_sync", default_cfg)


# Legacy option config.userdb_automatic_sync defaulted to "master".
# Can be: None: (no sync), "all": all sites sync, "master": only master site sync
# Take that option into account for compatibility reasons.
# For remote sites in distributed setups, the default is to do no sync.
def user_sync_default_config(site_config: SiteConfiguration, site_id: SiteId) -> UserSyncConfig:
    global_user_sync = _transform_userdb_automatic_sync(active_config.userdb_automatic_sync)
    if global_user_sync == "master":
        if site_is_local(site_config) and not is_wato_slave_site():
            user_sync_default: UserSyncConfig = "all"
        else:
            user_sync_default = None
    else:
        user_sync_default = global_user_sync

    return user_sync_default


# Old vs:
# ListChoice(
#    title = _('Automatic User Synchronization'),
#    help  = _('By default the users are synchronized automatically in several situations. '
#              'The sync is started when opening the "Users" page in configuration and '
#              'during each page rendering. Each connector can then specify if it wants to perform '
#              'any actions. For example the LDAP connector will start the sync once the cached user '
#              'information are too old.'),
#    default_value = [ 'wato_users', 'page', 'wato_pre_activate_changes', 'wato_snapshot_pushed' ],
#    choices       = [
#        ('page',                      _('During regular page processing')),
#        ('wato_users',                _('When opening the users\' configuration page')),
#        ('wato_pre_activate_changes', _('Before activating the changed configuration')),
#        ('wato_snapshot_pushed',      _('On a remote site, when it receives a new configuration')),
#    ],
#    allow_empty   = True,
# ),
def _transform_userdb_automatic_sync(val):
    if val == []:
        # legacy compat - disabled
        return None

    if isinstance(val, list) and val:
        # legacy compat - all connections
        return "all"

    return val
