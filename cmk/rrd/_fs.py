#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.utils import paths
from cmk.utils.misc import pnp_cleanup


@dataclass(frozen=True)
class Storage:
    _path: Path

    def get_path(self) -> Path:
        return self._path


def rrd_pnp_host_dir(hostname: HostName) -> Path:
    # We need /opt here because of bug in rrdcached
    return paths.rrd_multiple_dir / pnp_cleanup(hostname)


def rrd_cmc_host_dir(hostname: HostName) -> Path:
    # We need /opt here because of bug in rrdcached
    return paths.rrd_single_dir / pnp_cleanup(hostname)


def rrd_cmc_host_path(hostname: HostName, service_name: str) -> Storage:
    return Storage(rrd_cmc_host_dir(hostname) / pnp_cleanup(service_name))


def rrd_pnp_host_path(hostname: HostName, service_name: str, *, metric: str) -> Storage:
    return rrd_pnp_custom_path(rrd_pnp_host_dir(hostname), pnp_cleanup(service_name), metric=metric)


def rrd_pnp_xml_path(hostname: HostName, servicedesc: str) -> Storage:
    host_dir = rrd_pnp_host_dir(hostname)
    return Storage((host_dir / pnp_cleanup(servicedesc)).with_suffix(".xml"))


def rrd_pnp_custom_path(host_dir: Path, prefix: str, *, metric: str) -> Storage:
    return Storage(host_dir / (prefix + "_" + pnp_cleanup(metric)))
