#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Daemon configuration, derived from the OMD site environment.

In-tree the Maps backend always runs inside an OMD site, so ``OMD_ROOT`` /
``OMD_SITE`` are authoritative and there is no ``.env`` file, secret key, JWT or
database to configure. Operational tunables stay overridable via environment
variables (set by the init script) for emergency tuning without a code change.
"""

import logging
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cmk.maps.shared.config_vars import MAX_STATE_REFRESH_INTERVAL
from cmk.maps.shared.map_payload import FLOW_SERVICES_PER_HOST_MAX, FLOW_TOP_AFFECTED_HOSTS_MAX

_log = logging.getLogger(__name__)

_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


def _env_int(key: str, default: int, lo: int, hi: int) -> int:
    """The value of ``key``, or ``default`` when it is unset, no int or out of range."""
    if (raw := os.environ.get(key)) is None:
        return default
    try:
        if lo <= (value := int(raw)) <= hi:
            return value
    except ValueError:
        pass
    _log.warning(
        "Ignoring %(key)s=%(raw)r: not an integer from %(lo)d to %(hi)d, using %(default)d",
        {"key": key, "raw": raw, "lo": lo, "hi": hi, "default": default},
    )
    return default


def _bounded(key: str, default: int, lo: int, hi: int) -> int:
    """A setting from ``lo`` to ``hi`` that the environment variable ``key`` overrides."""
    return Field(default_factory=lambda: _env_int(key, default, lo, hi), ge=lo, le=hi)


def _normalize_log_level(value: str) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    upper = value.strip().upper()
    if upper in _LOG_LEVELS:
        return upper  # type: ignore[return-value]
    return "INFO"


_OMD_ROOT = os.environ.get("OMD_ROOT", "")
_OMD_SITE = os.environ.get("OMD_SITE", "")


class Settings(BaseModel):
    model_config = ConfigDict(validate_default=True)

    app_name: str = "Checkmk Maps"

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default_factory=lambda: _normalize_log_level(os.environ.get("MAPS_LOG_LEVEL", "INFO"))
    )

    # OMD site context (always present in-tree).
    checkmk_omd_root: str = _OMD_ROOT
    checkmk_site: str = _OMD_SITE

    state_refresh_interval: int = _bounded(
        "MAPS_STATE_REFRESH_INTERVAL", 5, 1, MAX_STATE_REFRESH_INTERVAL
    )
    # Cold-start Livestatus calls on busy 500+ host sites can exceed a 10 s
    # budget; 30 s keeps fan/orbit/row usable while still guarding against
    # truly stuck sockets.
    connection_query_timeout: int = _bounded("MAPS_CONNECTION_QUERY_TIMEOUT", 30, 1, 300)
    connection_pool_size: int = _bounded("MAPS_CONNECTION_POOL_SIZE", 20, 1, 256)
    multisite_connections: int = _bounded("MAPS_MULTISITE_CONNECTIONS", 4, 1, 16)

    flow_map_max_services_per_host: int = _bounded(
        "MAPS_FLOW_MAX_SERVICES_PER_HOST", 50, 0, FLOW_SERVICES_PER_HOST_MAX
    )
    # Mirror cmk.gui.nodevis: only fetch service detail for the top-K hosts
    # ranked by problem count.
    flow_map_top_affected_hosts: int = _bounded(
        "MAPS_FLOW_TOP_AFFECTED_HOSTS", 25, 0, FLOW_TOP_AFFECTED_HOSTS_MAX
    )
    # The services of a single host come by the core's index; those of several
    # take a look at every service.
    flow_map_bulk_service_chunk_size: int = _bounded(
        "MAPS_FLOW_BULK_SERVICE_CHUNK_SIZE", 1, 1, 1000
    )
    # Cap parallel chunks per Livestatus connection: each chunk opens its own
    # socket; firing 100+ in parallel exhausts the unix-socket listen backlog.
    flow_map_bulk_max_concurrent_chunks: int = _bounded(
        "MAPS_FLOW_BULK_MAX_CONCURRENT_CHUNKS", 8, 1, 64
    )
    connection_warmup_interval: int = _bounded("MAPS_CONNECTION_WARMUP_INTERVAL", 60, 1, 3600)
    # Hard cap on the services a folder-tree search returns. Without it a
    # multi-million-service site would freeze the UI.
    folder_search_max_services: int = _bounded("MAPS_FOLDER_SEARCH_MAX_SERVICES", 5000, 1, 50_000)


settings = Settings()
