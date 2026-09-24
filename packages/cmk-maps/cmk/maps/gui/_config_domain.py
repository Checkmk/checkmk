#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Config domain for the Checkmk Maps backend daemon.

Maps settings are edited as native Checkmk global settings (Customize → Maps →
"Maps settings"), but — like every other Checkmk daemon configured via
WATO (liveproxyd, dcd, mkeventd) — they belong to the daemon's *own* config
domain, not to the GUI domain. WATO writes them to ``etc/check_mk/maps.d/wato/``
(``global.mk`` + per-site ``sitespecific.mk``); the daemon reads that directory
directly (it never touches the GUI's ``multisite.d``). A ReplicationPath ships
the directory to remote sites on Activate Changes.

The daemon re-reads its settings per request (uncached), so a global change is
picked up on the next request — there is no reload signal to send, hence
``needs_activation = False`` and a no-op ``activate()``.
"""

import copy
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal, override, TypedDict

import cmk.utils.paths
from cmk.ccc.site import omd_site
from cmk.gui.i18n import _
from cmk.gui.rule_specs.legacy_converter import convert_to_legacy_valuespec
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    SerializedSettings,
)
from cmk.maps.gui._permissions import PERMISSION_SECTION_MAPS
from cmk.maps.gui.form_specs.global_settings import object_defaults_spec
from cmk.maps.shared import config_vars as maps_config_vars
from cmk.maps.shared.map_payload import MapViewType, RenderMode
from cmk.rulesets.v1 import Title
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.web.utils.permission_verification import PermissionName

MAPS: Final[ConfigDomainName] = "maps"

# Runtime idents the DAEMON reads: the GUI↔daemon .mk-file contract lives in
# cmk.maps.shared.config_vars, imported by both sides so it can't drift.
CONFIG_VAR_CONNECTIONS = maps_config_vars.VAR_CONNECTIONS
CONFIG_VAR_LOG_LEVEL = maps_config_vars.VAR_LOG_LEVEL
CONFIG_VAR_STATE_REFRESH_INTERVAL = maps_config_vars.VAR_STATE_REFRESH_INTERVAL
# Authoring-defaults idents. GUI-only (the daemon never reads them), but kept in
# this same domain so the feature owns all its config in one place (like dcd) —
# the daemon just ignores these keys in maps.d.
CONFIG_VAR_MAP_DEFAULTS = "maps_map_defaults"
CONFIG_VAR_OBJECT_DEFAULTS = "maps_object_defaults"

# Titles shown in the "Maps: …" global-settings groups (the groups already say
# "Maps", so the individual settings are not prefixed).
CONNECTIONS_TITLE = Title("Connections")
MAP_DEFAULTS_TITLE = Title("Map defaults")
OBJECT_DEFAULTS_TITLE = Title("Object defaults")

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_STATE_REFRESH_INTERVAL = 5


class _SocketTarget(TypedDict):
    socket_path: str


class _LivestatusOptions(TypedDict):
    """The Livestatus arm of the connection form's ``type`` cascade."""

    target: tuple[Literal["socket"], _SocketTarget]
    timeout: int
    checkmk_url: str
    metric_history: tuple[Literal["livestatus"], None]


class _ConnectionEntry(TypedDict):
    """One ``maps_connections`` entry in the nested FormSpec shape WATO stores.

    The daemon flattens this back into a ``ConnectionConfig``
    (``cmk.maps.backend.services.connection_forms``).
    """

    id: str
    label: str
    type: tuple[Literal["livestatus"], _LivestatusOptions]


def _connections_default() -> list[_ConnectionEntry]:
    # Every site starts with a connection to its own Livestatus. Being the factory
    # default, it is computed on each site and never stored, so it does not count
    # as a modification and is not replicated to the remote sites; the daemon's
    # built-in local-site connection describes the same connection.
    site = omd_site()
    return [
        {
            "id": f"cmk_{site}",
            "label": f"Checkmk {site}",
            "type": (
                "livestatus",
                {
                    "target": (
                        "socket",
                        {"socket_path": str(cmk.utils.paths.omd_root / "tmp" / "run" / "live")},
                    ),
                    "timeout": 10,
                    "checkmk_url": f"/{site}/check_mk",
                    "metric_history": ("livestatus", None),
                },
            ),
        }
    ]


class _MapDefaults(TypedDict):
    """The authoring defaults a new map inherits."""

    default_backend_id: str
    default_map_type: tuple[MapViewType, Mapping[str, object] | None]
    default_render_mode: RenderMode


def _map_defaults_default() -> _MapDefaults:
    # Static factory default. Deliberately does NOT read the configured connection
    # list from disk / render a valuespec: default_globals() is also reached from
    # non-request activation paths (get_all_default_globals), where file I/O and
    # form rendering are surprising. The default connection id is deterministic
    # (cmk_<site>, see _connections_default / builtin_maps), so we name it directly and
    # let per-map / Global-settings overrides take precedence.
    return {
        "default_backend_id": f"cmk_{omd_site()}",
        "default_map_type": ("static", None),
        "default_render_mode": "default",
    }


@lru_cache(maxsize=1)
def _object_defaults_factory_value() -> Mapping[str, object]:
    # ``_settings.effective_settings()`` calls ``default_globals()`` directly,
    # bypassing the request-level memoization WATO puts in front of
    # ``get_all_default_globals``, so every schema render and cfg import would
    # rebuild the spec. Cacheable across requests because the spec takes no
    # context and every prefill is a plain, unlocalized literal.
    #
    # ``default_value()`` is untyped (the legacy valuespec conversion erases the
    # model type), hence the explicit annotation.
    default: Mapping[str, object] = convert_to_legacy_valuespec(
        object_defaults_spec(title=OBJECT_DEFAULTS_TITLE), _
    ).default_value()
    return default


def _object_defaults_default() -> Mapping[str, object]:
    # Unlike the map defaults there is no hand-written literal to keep in sync: the
    # object-defaults FormSpec's own defaults are the source of truth. Handed out
    # as a copy so a caller mutating the settings it got cannot reach into the
    # cached value.
    return copy.deepcopy(_object_defaults_factory_value())


class ConfigDomainMaps(ABCConfigDomain):
    # Distributed to remotes via an explicit ReplicationPath (see registration),
    # mirroring liveproxyd; the daemon picks up changes by re-reading per request.
    # needs_sync must be True: the file sync that ships ReplicationPath dirs is
    # gated on some change-domain requesting a sync, so a Maps-only change would
    # otherwise never reach remote sites (their daemon would read stale config).
    needs_sync = True
    needs_activation = False
    in_global_settings = False
    # Global defaults are an admin concern, on the Maps pages as well as per site.
    global_settings_permission: PermissionName = f"{PERMISSION_SECTION_MAPS.name}.configure"

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return MAPS

    @override
    def config_dir(self) -> Path:
        return cmk.utils.paths.default_config_dir / "maps.d/wato"

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # No reload signal: the Maps daemon re-reads its config dir per request.
        return []

    @override
    def default_globals(self) -> GlobalSettings:
        return {
            CONFIG_VAR_CONNECTIONS: _connections_default(),
            CONFIG_VAR_LOG_LEVEL: DEFAULT_LOG_LEVEL,
            CONFIG_VAR_STATE_REFRESH_INTERVAL: DEFAULT_STATE_REFRESH_INTERVAL,
            # GUI-only authoring seeds — kept in the daemon's own domain (the
            # daemon ignores them) so the feature owns all its config, like dcd.
            CONFIG_VAR_MAP_DEFAULTS: _map_defaults_default(),
            CONFIG_VAR_OBJECT_DEFAULTS: _object_defaults_default(),
        }
