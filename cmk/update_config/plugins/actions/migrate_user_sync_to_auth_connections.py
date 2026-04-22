#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Migrate the deprecated ``user_sync`` site field to the new authentication fields.

Every LDAP connection mentioned in an explicit ``("list", [...])`` form of
``user_sync`` is copied into both ``authentication_connections`` and
``user_attribute_sync_connections``. The legacy bare strings ``"all"`` and
``"master"`` are migrated to ``user_attribute_sync_connections`` only;
``authentication_connections`` is left unset for those forms because the
new system requires explicit opt-in per connection.

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

        migrated = False
        for site_id, site_spec in configured_sites.items():
            # `user_sync` was a required field on legacy `SiteConfiguration`; the
            # earlier cleanup action (sort_index=30) `setdefault`s it for older
            # sites that lacked it on disk, so it is usually present when we run.
            # We `pop` here so the on-disk spec ends up without the obsolete key
            # regardless of whether the new fields had already been set manually.
            user_sync = site_spec.pop("user_sync", None)  # type: ignore[typeddict-item]
            auth_value, attr_sync_value = _derive_new_values(
                user_sync, is_central_site=(site_id == central_site_id)
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
) -> tuple[AuthConnectionsValue | None, AttrSyncConnectionsValue | None]:
    """Map a ``user_sync`` value to the new fields.

    Returning ``None`` for a field means "leave the key absent on disk" —
    callers must skip the assignment so that the runtime falls back to the
    propagated central-site value.

    ``authentication_connections`` no longer supports an ``"all"`` form:
    admins must list specific LDAP/SAML connections (or inherit from the
    central by leaving the key absent). We therefore *never* derive
    ``authentication_connections`` from the legacy bare-string forms of
    ``user_sync`` — those would have implied "every LDAP connection", but
    the new system requires explicit opt-in. Admins of existing distributed
    setups must visit the site configuration and pick connections
    explicitly.

    For ``user_attribute_sync_connections`` we still derive the value
    automatically — ``"all"`` is a valid form there.

    - ``"all"`` → ``(None, "all")``: attribute sync runs for every LDAP
      connection (prior behaviour); auth list is left unset for explicit
      admin action.
    - ``"master"`` on the central → ``(None, "all")``: same as above; the
      central syncs everything but auth must be configured explicitly.
    - ``"master"`` on a remote → ``(None, None)``: the master syncs, the
      remote does not; both keys left unset (inherit from central).
    - ``("list", [conn_ids])`` → ``([("ldap", id) ...], [conn_ids])``: the
      legacy connection IDs are migrated faithfully as plain lists.
    - Anything else (``None`` / unrecognized) → ``(None, None)``.
    """
    if user_sync == "all":
        return None, "all"
    if user_sync == "master":
        return None, ("all" if is_central_site else None)
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
