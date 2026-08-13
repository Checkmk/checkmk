#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Migrate the removed ``user_sync`` site field to ``authentication_connections``
and ``user_attribute_sync_connections``.

``user_sync`` only governed the background sync; login worked against every
connection available on the site. The attribute sync field takes over the
sync half, the authentication field stays permissive so that logins — and the
users a login creates on the site, which only survive config pushes while
listed here — keep working:

    legacy ``user_sync``   authentication         attribute sync
    ``"all"``              ``("all", [types])``   ``"all"``
    ``"master"``           ``("all", [types])``   central ``"all"``, remote ``"disabled"``
    non-empty ``list``     same list              same list
    ``None`` / empty list  ``("all", [types])``   ``"disabled"``
    key missing            ``("all", [types])``   central ``"all"``, remote ``"disabled"``

``[types]`` is ``["ldap", "saml"]`` on the central site and ``["ldap"]`` on
remotes, where SAML never authenticated before the upgrade.

Only fields not yet set are filled in, so manually migrated sites keep their
configuration.
"""

from logging import Logger
from typing import Literal, override

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.userdb._connections import distributed_saml_supported
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.sites import site_management_registry
from cmk.livestatus_client import AuthenticationConnectionEntry, AuthenticationConnectionsValue
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.log import VERBOSE

AttrSyncConnectionsValue = Literal["all", "disabled"] | list[str]

# Distinguishes "key not on disk" from an explicit ``user_sync = None``
# (the legacy "Disable automatic user synchronization" choice).
_MISSING = object()


class MigrateUserSyncToAuthConnections(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        site_mgmt = site_management_registry["site_management"]
        configured_sites = site_mgmt.load_sites()
        central_site_id = omd_site()

        migrated = False
        for site_id, site_spec in configured_sites.items():
            # `user_sync` was a required field on legacy `SiteConfiguration`
            # and the legacy valuespec always wrote it, so it is usually
            # present when we run. We `pop` here so the on-disk spec ends up
            # without the obsolete key regardless of whether the new fields
            # had already been set manually. The `_MISSING` sentinel keeps a
            # hand-edited spec without the key distinguishable from an
            # explicit `user_sync = None` ("sync disabled").
            user_sync = site_spec.pop("user_sync", _MISSING)  # type: ignore[typeddict-item]
            auth_value, attr_sync_value = _derive_new_values(
                user_sync,
                is_central_site=(site_id == central_site_id),
                saml_supported=distributed_saml_supported(),
            )
            did_set = user_sync is not _MISSING
            if "authentication_connections" not in site_spec and auth_value is not None:
                site_spec["authentication_connections"] = auth_value
                did_set = True
            if "user_attribute_sync_connections" not in site_spec and attr_sync_value is not None:
                site_spec["user_attribute_sync_connections"] = attr_sync_value
                did_set = True

            if did_set:
                migrated = True
                logger.log(
                    VERBOSE,
                    "Migrated user_sync=%(user_sync)r on site %(site_id)r to "
                    "authentication_connections=%(authentication_connections)r, "
                    "user_attribute_sync_connections=%(user_attribute_sync_connections)r",
                    {
                        "user_sync": user_sync,
                        "site_id": str(site_id),
                        "authentication_connections": site_spec.get("authentication_connections"),
                        "user_attribute_sync_connections": site_spec.get(
                            "user_attribute_sync_connections"
                        ),
                    },
                )

        if migrated:
            site_mgmt.save_sites(
                make_folder_tree(active_config),
                configured_sites,
                activate=False,
                pprint_value=active_config.wato_pprint_config,
                liveproxyd_enabled=active_config.liveproxyd_enabled,
                use_git=active_config.wato_use_git,
                acting_user_id=None,
            )


def _derive_new_values(
    user_sync: object,
    *,
    is_central_site: bool,
    saml_supported: bool,
) -> tuple[AuthenticationConnectionsValue | None, AttrSyncConnectionsValue | None]:
    """Map a ``user_sync`` value to the new fields per the module docstring.

    ``None`` for a field means "leave the key absent on disk" — callers must
    skip the assignment.
    """
    all_value: AuthenticationConnectionsValue = (
        ("all", ["ldap", "saml"]) if is_central_site and saml_supported else ("all", ["ldap"])
    )
    if user_sync == "all":
        return all_value, "all"
    if user_sync == "master":
        # Legacy "sync only on the central site".
        return all_value, "all" if is_central_site else "disabled"
    if isinstance(user_sync, tuple) and user_sync[0] == "list":
        if not (conn_ids := list(user_sync[1])):
            # An empty explicit list is semantically "no sync", and the site
            # editor now rejects an empty list.
            return all_value, "disabled"
        auth_entries: list[AuthenticationConnectionEntry] = [
            ("ldap", conn_id) for conn_id in conn_ids
        ]
        return auth_entries, conn_ids
    if user_sync is None:
        # Legacy "Disable automatic user synchronization".
        return all_value, "disabled"
    # Missing key (or unrecognized value): write both sides explicitly since
    # an absent key now falls back to the "all" defaults. The attribute sync
    # follows the legacy `userdb_automatic_sync` default ("master"): only the
    # central site syncs.
    return all_value, "all" if is_central_site else "disabled"


update_action_registry.register(
    MigrateUserSyncToAuthConnections(
        name="migrate_user_sync_to_auth_connections",
        title="Migrate site user_sync to authentication_connections",
        sort_index=35,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
