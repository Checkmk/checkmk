#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Migrate the deprecated ``user_sync`` site field to the new authentication fields.

Every LDAP connection mentioned in an explicit ``("list", [...])`` form of
``user_sync`` is copied into both ``authentication_connections`` and
``user_attribute_sync_connections``. The legacy bare strings ``"all"`` and
``"master"`` (on the central site) implied "every LDAP connection", so they are
expanded into an explicit ``[("ldap", id), ...]`` list of every configured LDAP
connection for ``authentication_connections`` and the ``"all"`` form for
``user_attribute_sync_connections``. This preserves the prior behaviour where
every LDAP connection could create users during the background sync — the new
system gates user creation on ``authentication_connections`` membership, so
leaving it unset would silently stop those sites from creating users on upgrade.

Pre-existing values of the new fields are preserved — the migration only
fills in fields that haven't been set yet, so a site that was already moved
manually keeps its current configuration.

The legacy ``user_sync`` key is removed from the on-disk site spec after the
new fields have been derived; ``user_sync`` is no longer part of the
``SiteConfiguration`` schema, so leaving it would just be dead data.
"""

from logging import Logger
from typing import Literal, override

from livestatus import AuthenticationConnectionEntry

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.userdb._connections import is_ldap, load_connection_config
from cmk.gui.watolib.sites import site_management_registry
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.log import VERBOSE

AuthConnectionsValue = list[AuthenticationConnectionEntry]
AttrSyncConnectionsValue = Literal["all"] | list[str]


class MigrateUserSyncToAuthConnections(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        site_mgmt = site_management_registry["site_management"]
        configured_sites = site_mgmt.load_sites()
        central_site_id = omd_site()

        # All configured LDAP connections, read from disk (independent of whether
        # `active_config.user_connections` is populated during update-config).
        # The legacy bare-string forms "all"/"master" implied "every LDAP
        # connection", so they expand into this explicit list for
        # `authentication_connections` (which has no "all" shorthand).
        ldap_connection_ids = [c["id"] for c in load_connection_config() if is_ldap(c)]

        migrated = False
        for site_id, site_spec in configured_sites.items():
            # `user_sync` was a required field on legacy `SiteConfiguration`; the
            # earlier cleanup action (sort_index=30) `setdefault`s it for older
            # sites that lacked it on disk, so it is usually present when we run.
            # We `pop` here so the on-disk spec ends up without the obsolete key
            # regardless of whether the new fields had already been set manually.
            user_sync = site_spec.pop("user_sync", None)  # type: ignore[typeddict-item]
            auth_value, attr_sync_value = _derive_new_values(
                user_sync,
                is_central_site=(site_id == central_site_id),
                ldap_connection_ids=ldap_connection_ids,
            )
            did_set = user_sync is not None
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
                    "Migrated user_sync=%r on site %r to authentication_connections=%r, "
                    "user_attribute_sync_connections=%r",
                    user_sync,
                    str(site_id),
                    site_spec.get("authentication_connections"),
                    site_spec.get("user_attribute_sync_connections"),
                )

        if migrated:
            site_mgmt.save_sites(
                configured_sites,
                activate=False,
                pprint_value=active_config.wato_pprint_config,
            )


def _derive_new_values(
    user_sync: object,
    *,
    is_central_site: bool,
    ldap_connection_ids: list[str],
) -> tuple[AuthConnectionsValue | None, AttrSyncConnectionsValue | None]:
    """Map a ``user_sync`` value to the new fields.

    Returning ``None`` for a field means "leave the key absent on disk" —
    callers must skip the assignment so that the runtime falls back to the
    propagated central-site value.

    ``authentication_connections`` has no ``"all"`` shorthand — it is an
    explicit list of connections. The legacy bare-string forms implied "every
    LDAP connection", so they are expanded into an explicit
    ``[("ldap", id), ...]`` list over ``ldap_connection_ids`` (all configured
    LDAP connections). This preserves the prior behaviour where every LDAP
    connection could create users during the background sync: the new system
    gates creation on ``authentication_connections`` membership, so leaving it
    unset would silently stop those sites from creating users on upgrade.

    ``user_attribute_sync_connections`` keeps deriving automatically — ``"all"``
    is a valid form there.

    - ``"all"`` → ``([("ldap", id) ...], "all")``: every configured LDAP
      connection both authenticates and attribute-syncs (prior behaviour).
    - ``"master"`` on the central → ``([("ldap", id) ...], "all")``: same as
      above; the central syncs and authenticates with every LDAP connection.
    - ``"master"`` on a remote → ``(None, None)``: the master syncs, the
      remote does not; both keys left unset (inherit from central).
    - ``("list", [conn_ids])`` → ``([("ldap", id) ...], [conn_ids])``: the
      legacy connection IDs are migrated faithfully as plain lists.
    - Anything else (``None`` / unrecognized) → ``(None, None)``.
    """
    all_ldap_entries: list[AuthenticationConnectionEntry] = [
        ("ldap", conn_id) for conn_id in ldap_connection_ids
    ]
    if user_sync == "all":
        return all_ldap_entries, "all"
    if user_sync == "master":
        return (all_ldap_entries, "all") if is_central_site else (None, None)
    if isinstance(user_sync, tuple) and user_sync[0] == "list":
        conn_ids: list[str] = list(user_sync[1])
        auth_entries: list[AuthenticationConnectionEntry] = [
            ("ldap", conn_id) for conn_id in conn_ids
        ]
        return auth_entries, conn_ids
    return None, None


update_action_registry.register(
    MigrateUserSyncToAuthConnections(
        name="migrate_user_sync_to_auth_connections",
        title="Migrate site user_sync to authentication_connections",
        # Run after `clean_up_site_attributes` (sort_index=30), which
        # `setdefault`s `user_sync = "all"` for legacy sites that lacked it.
        sort_index=35,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
