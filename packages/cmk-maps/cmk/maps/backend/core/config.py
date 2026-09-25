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

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _normalize_log_level(value: str) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    upper = value.strip().upper()
    if upper in _LOG_LEVELS:
        return upper  # type: ignore[return-value]
    return "INFO"


_OMD_ROOT = os.environ.get("OMD_ROOT", "")
_OMD_SITE = os.environ.get("OMD_SITE", "")
_VAR_DIR = str(Path(_OMD_ROOT) / "var" / "maps")


class Settings(BaseModel):
    app_name: str = "Checkmk Maps"

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default_factory=lambda: _normalize_log_level(os.environ.get("MAPS_LOG_LEVEL", "INFO"))
    )

    # OMD site context (always present in-tree).
    checkmk_omd_root: str = _OMD_ROOT
    checkmk_site: str = _OMD_SITE

    # Map JSON files live in var/maps/maps/; uploaded images in var/maps/images/.
    maps_dir: str = str(Path(_VAR_DIR) / "maps")

    state_refresh_interval: int = Field(
        default_factory=lambda: _env_int("MAPS_STATE_REFRESH_INTERVAL", 5), ge=1
    )
    # Cold-start Livestatus calls on busy 500+ host sites can exceed a 10 s
    # budget; 30 s keeps fan/orbit/row usable while still guarding against
    # truly stuck sockets.
    connection_query_timeout: int = Field(
        default_factory=lambda: _env_int("MAPS_CONNECTION_QUERY_TIMEOUT", 30), ge=1
    )
    connection_pool_size: int = Field(
        default_factory=lambda: _env_int("MAPS_CONNECTION_POOL_SIZE", 20), ge=1
    )

    flow_map_max_services_per_host: int = Field(
        default_factory=lambda: _env_int("MAPS_FLOW_MAX_SERVICES_PER_HOST", 50), ge=0
    )
    flow_map_topology_cache_ttl: float = Field(
        default_factory=lambda: _env_float("MAPS_FLOW_TOPOLOGY_CACHE_TTL", 20.0)
    )
    # Mirror cmk.gui.nodevis: only fetch service detail for the top-K hosts
    # ranked by problem count.
    flow_map_top_affected_hosts: int = Field(
        default_factory=lambda: _env_int("MAPS_FLOW_TOP_AFFECTED_HOSTS", 25), ge=0
    )
    flow_map_bulk_service_chunk_size: int = Field(
        default_factory=lambda: _env_int("MAPS_FLOW_BULK_SERVICE_CHUNK_SIZE", 5), ge=1
    )
    # Cap parallel chunks per Livestatus connection: each chunk opens its own
    # socket; firing 100+ in parallel exhausts the unix-socket listen backlog.
    flow_map_bulk_max_concurrent_chunks: int = Field(
        default_factory=lambda: _env_int("MAPS_FLOW_BULK_MAX_CONCURRENT_CHUNKS", 8), ge=1, le=64
    )
    connection_warmup_interval: int = Field(
        default_factory=lambda: _env_int("MAPS_CONNECTION_WARMUP_INTERVAL", 60), ge=1
    )
    # Hard cap on the services a folder-tree search returns. Without it a
    # multi-million-service site would freeze the UI.
    folder_search_max_services: int = Field(
        default_factory=lambda: _env_int("MAPS_FOLDER_SEARCH_MAX_SERVICES", 5000), ge=1
    )


settings = Settings()
