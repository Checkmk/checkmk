#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared helpers for exercising the ``user_sync`` -> ``authentication_connections`` /
``user_attribute_sync_connections`` migration on a *running* site.

Used by the composition migration tests (round-trip, the
preserve-already-configured guard, and the migrated-config-propagation test):
seed each legacy ``user_sync`` form onto a site's on-disk ``sites.mk``, run the
real ``cmk-update-config`` (which executes the registered
``migrate_user_sync_to_auth_connections`` update action), and read the migrated
fields back — from disk, and (after activation) from a remote.

The seeding itself has to run inside the site (site user, site Python, site config),
so it lives in ``helper_seed_legacy_user_sync.py`` next to this module and is invoked
through ``Site.python_helper``. Keeping it a real module rather than an inlined source
string puts it under the formatter, linter and type checker like any other test code.
"""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final, Literal, override, TypedDict

from tests.testlib.site import Site

logger = logging.getLogger(__name__)

# A legacy ``user_sync`` value in any of the forms the migration understands.
# ``"disabled"`` is this module's stand-in for a legacy ``user_sync = None`` (the
# "Disable automatic user synchronization" choice): the seeding keywords already use
# ``None`` to mean "not provided", so the disabled case needs a name of its own.
# ``"disabled"`` is not itself a legacy value, so it cannot collide with one.
LegacyUserSync = Literal["all", "master", "disabled"] | tuple[Literal["list"], list[str]]

# Legacy ``user_sync = None``. Pass as any of the seeding keywords to seed the
# disabled form; the in-site helper maps it back to ``None`` before writing.
DISABLED: Final[LegacyUserSync] = "disabled"


class _Missing:
    """Sentinel for "this key is absent on disk" (distinct from a ``None`` value)."""

    @override
    def __repr__(self) -> str:
        return "<absent>"


MISSING: Final = _Missing()


class PreconfiguredEntry(TypedDict):
    """A seeded site entry that already carries the post-migration fields (plus a
    stale ``user_sync``) — to assert the migration preserves rather than overwrites."""

    user_sync: LegacyUserSync
    authentication_connections: list[tuple[str, object]]
    user_attribute_sync_connections: Literal["all"] | list[str]


def seed_legacy_user_sync(
    site: Site,
    *,
    own: LegacyUserSync | None = None,
    remotes: dict[str, LegacyUserSync] | None = None,
    existing: dict[str, LegacyUserSync] | None = None,
    presets: dict[str, PreconfiguredEntry] | None = None,
    base_port: int = 6810,
) -> None:
    """Write legacy ``user_sync`` values into ``site``'s on-disk ``sites.mk``.

    ``own`` sets the value on the site's own (central) entry. ``remotes`` maps a
    fresh site id to its legacy value; each is materialised as a config-only
    "slave" connection cloned from the own entry (so it is a valid
    ``SiteConfiguration`` the migration can load), keyed central-vs-remote by id.
    ``existing`` sets the value on entries that already exist (e.g. a real connected
    remote), in place and without cloning, so a live connection is preserved.
    ``presets`` materialises entries that *already* carry the new fields alongside
    a stale ``user_sync`` — used to assert the migration preserves them.

    Pass :data:`DISABLED` for the legacy ``user_sync = None`` form; a bare ``None``
    means "leave this keyword alone", so it cannot express that value.
    """
    payload: dict[str, object] = {"own_site_id": site.id}
    if own is not None:
        payload["own"] = own
    payload["existing"] = dict(existing or {})
    port = base_port
    remote_entries: list[dict[str, object]] = []
    for site_id, value in sorted((remotes or {}).items()):
        remote_entries.append({"site_id": site_id, "user_sync": value, "port": port})
        port += 1
    payload["remotes"] = remote_entries
    preset_entries: list[dict[str, object]] = []
    for site_id, spec in sorted((presets or {}).items()):
        preset_entries.append({"site_id": site_id, "port": port, **spec})
        port += 1
    payload["presets"] = preset_entries
    site.python_helper("helper_seed_legacy_user_sync.py").check_output(input_=json.dumps(payload))


def run_update_config(site: Site) -> None:
    """Run the real ``cmk-update-config`` on a running site (non-interactive).

    ``--conflict=force`` answers all prompts and continues past pre-flight
    findings; ``--site-may-run`` allows running while the site is up.
    """
    result = site.run(
        ["cmk-update-config", "--conflict=force", "--site-may-run"],
        check=False,
    )
    assert result.returncode == 0, (
        f"cmk-update-config failed (rc={result.returncode})\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def read_site_sync_fields(site: Site) -> dict[str, dict[str, object]]:
    """Parse ``sites.mk`` and return, per site id, the migration-relevant state:

    ``authentication_connections`` / ``user_attribute_sync_connections`` (or
    :data:`MISSING` when the key is absent) and ``has_user_sync`` (the legacy key
    should be gone after migration).
    """
    content = site.read_file("etc/check_mk/multisite.d/sites.mk")
    ns: dict[str, object] = {"sites": {}}
    exec(content, ns)
    sites = ns.get("sites")
    if not isinstance(sites, dict):
        return {}
    fields: dict[str, dict[str, object]] = {}
    for site_id, cfg in sites.items():
        if not isinstance(cfg, dict):
            continue
        fields[site_id] = {
            "authentication_connections": cfg.get("authentication_connections", MISSING),
            "user_attribute_sync_connections": cfg.get("user_attribute_sync_connections", MISSING),
            "has_user_sync": "user_sync" in cfg,
        }
    return fields


def read_inherited_authentication_connections(remote_site: Site) -> object:
    """Return the ``authentication_connections`` the central pushed into ``remote_site``
    at activation (CMK-33812), or :data:`MISSING` if absent.

    The central writes each remote's per-site value into the remote's site-specific
    config; on the remote it surfaces either as a top-level key in
    ``sitespecific.mk`` or under that remote's own entry in ``sites.mk``.
    """
    sitespecific = "etc/check_mk/multisite.d/wato/sitespecific.mk"
    try:
        ns: dict[str, object] = {}
        exec(remote_site.read_file(sitespecific), ns)
        if "authentication_connections" in ns:
            return ns["authentication_connections"]
    except Exception:
        pass
    # Fall back to the remote's own entry in its sites.mk.
    return (
        read_site_sync_fields(remote_site)
        .get(remote_site.id, {})
        .get("authentication_connections", MISSING)
    )


@contextmanager
def preserve_sites_mk(site: Site) -> Iterator[None]:
    """Snapshot ``site``'s ``sites.mk`` and restore it (re-activating) on exit.

    Lets a destructive ``cmk-update-config`` run reuse a shared *session* site
    instead of a dedicated throw-away one: the pre-test site list is restored and
    re-activated afterwards, so neither the central nor its remotes keep the
    migrated state. Use around a migration test that runs on the session sites.
    """
    rel = "etc/check_mk/multisite.d/sites.mk"
    backup = site.read_file(rel)
    try:
        yield
    finally:
        site.write_file(rel, backup)
        try:
            # Push the restored site list back out so remotes drop the migrated value too.
            site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
        except Exception:
            logger.exception("Failed to re-activate after restoring sites.mk on %s", site.id)
