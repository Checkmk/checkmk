#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Maps config domain and its distributed-replication contract.

``test_config_variables.py`` pins the variable→domain mapping; this pins the
domain itself. The load-bearing property is ``needs_sync = True``: the file sync
that ships the domain's ``ReplicationPath`` directory to remote sites is gated on
*some* change-domain requesting a sync, so a Maps-only settings change would
otherwise never reach a remote daemon — it would read stale config indefinitely.
The ReplicationPath itself is derived from ``config_dir()``, so that path must
resolve under ``omd_root`` for the registration to be valid.
"""

import cmk.utils.paths
from cmk.maps.gui._config_domain import (
    _object_defaults_factory_value,
    CONFIG_VAR_CONNECTIONS,
    CONFIG_VAR_LOG_LEVEL,
    CONFIG_VAR_MAP_DEFAULTS,
    CONFIG_VAR_OBJECT_DEFAULTS,
    CONFIG_VAR_STATE_REFRESH_INTERVAL,
    ConfigDomainMaps,
)


def test_daemon_domain_requests_sync_so_remote_daemons_get_config() -> None:
    # Regression guard: without needs_sync a Maps-only Activate Changes never
    # ships maps.d/wato to remotes and their daemon reads stale config.
    domain = ConfigDomainMaps()
    assert domain.needs_sync is True
    # The daemon re-reads its config dir per request, so there is no reload to
    # trigger on activation.
    assert domain.needs_activation is False


def test_settings_are_not_listed_in_the_central_global_settings() -> None:
    # Maps owns its settings pages (the two curated modes), like dcd.
    assert ConfigDomainMaps.in_global_settings is False


def test_domain_ident() -> None:
    assert ConfigDomainMaps.ident() == "maps"


def test_config_dir_is_replicable() -> None:
    domain = ConfigDomainMaps()
    config_dir = domain.config_dir()
    assert config_dir == cmk.utils.paths.default_config_dir / "maps.d/wato"
    # The ReplicationPath uses config_dir().relative_to(omd_root); it must not raise.
    assert config_dir.is_relative_to(cmk.utils.paths.omd_root)


def test_activate_and_create_artifacts_are_noops() -> None:
    domain = ConfigDomainMaps()
    assert domain.activate() == []
    assert domain.create_artifacts() == []


def test_default_globals_carry_daemon_and_authoring_defaults(request_context: None) -> None:  # noqa: ARG001
    # All Maps settings live in the one feature domain (like dcd); the daemon reads
    # only the runtime knobs and ignores the GUI-only authoring defaults in the file.
    defaults = ConfigDomainMaps().default_globals()
    # No connection out of the box — the daemon synthesises a local-site one when
    # the list is empty, so maps work unconfigured.
    assert defaults[CONFIG_VAR_CONNECTIONS] == []
    assert defaults[CONFIG_VAR_LOG_LEVEL] == "INFO"
    assert defaults[CONFIG_VAR_STATE_REFRESH_INTERVAL] == 5
    # The GUI-only authoring defaults share the domain.
    assert CONFIG_VAR_MAP_DEFAULTS in defaults
    assert CONFIG_VAR_OBJECT_DEFAULTS in defaults
    # The map default names the seeded local connection (cmk_<site>) directly.
    # default_globals() is also reached from non-request activation paths, so it
    # must stay a pure factory default — it must NOT read the connection list
    # from disk to synthesise this.
    assert defaults[CONFIG_VAR_MAP_DEFAULTS]["default_backend_id"].startswith("cmk_")


def test_object_defaults_form_spec_is_rendered_once(request_context: None) -> None:  # noqa: ARG001
    """``default_globals()`` must not rebuild the object-defaults FormSpec per call.

    ``_settings.effective_settings()`` calls ``default_globals()`` directly, so it
    is not covered by the request-level memoization in front of
    ``get_all_default_globals`` — every schema render and cfg import would pay for
    the spec build and the legacy conversion.
    """
    _object_defaults_factory_value.cache_clear()

    ConfigDomainMaps().default_globals()
    ConfigDomainMaps().default_globals()

    assert _object_defaults_factory_value.cache_info().hits == 1


def test_object_defaults_cannot_be_mutated_through_the_cache(
    request_context: None,  # noqa: ARG001
) -> None:
    # The cached factory value is shared; callers get a copy so a mutated settings
    # dict cannot poison every later reader in the process.
    first = ConfigDomainMaps().default_globals()[CONFIG_VAR_OBJECT_DEFAULTS]
    assert isinstance(first, dict)
    first["mutated_by_caller"] = True

    second = ConfigDomainMaps().default_globals()[CONFIG_VAR_OBJECT_DEFAULTS]
    assert isinstance(second, dict)
    assert "mutated_by_caller" not in second
