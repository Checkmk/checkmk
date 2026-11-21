#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

from cmk.ccc import store
from cmk.product_usage.schema import DistributedMonitoring


def collect(*, default_config_dir: Path, cmk_config_dir: Path) -> DistributedMonitoring:
    return DistributedMonitoring(
        is_remote_setup_site=_has_distributed_wato_file(cmk_config_dir)
        and not _configures_remote_sites(default_config_dir)
    )


def _has_distributed_wato_file(cmk_config_dir: Path) -> bool:
    """Whether a central site pushed its configuration to this site, or this site to others

    The file is written with each configuration push, on the central site and on the remote
    sites. A central site empties its file when it no longer pushes to any remote site.
    """
    path = cmk_config_dir / "distributed_wato.mk"
    return path.exists() and path.stat().st_size != 0


def _configures_remote_sites(default_config_dir: Path) -> bool:
    """Whether this site pushes its configuration to a remote site, like a central site"""
    sites: Mapping[str, Mapping[str, object]] = store.load_from_mk_file(
        default_config_dir / "multisite.d/sites.mk", key="sites", default={}, lock=False
    )
    return any(site.get("replication") for site in sites.values())
