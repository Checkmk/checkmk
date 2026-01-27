#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from cmk.ccc.hostaddress import HostName
from cmk.utils import paths
from cmk.utils.misc import pnp_cleanup

MAX_FILENAME_LENGTH: Final = os.pathconf("/", "PC_NAME_MAX")


@dataclass(frozen=True)
class Storage:
    _path: Path

    def get_path(self, suffix: str) -> Path | None:
        path = self.get_expected_path(suffix)
        # 5 is a bit more theoretical safety
        if len(str(path.name)) >= MAX_FILENAME_LENGTH - 5:
            return None
        return path

    def get_expected_path(self, suffix: str) -> Path:
        return self._path.with_suffix(suffix)


def get_pnp_host_dir(hostname: HostName) -> Path:
    # We need /opt here because of bug in rrdcached
    return paths.rrd_multiple_dir / pnp_cleanup(hostname)


def get_cmc_host_dir(hostname: HostName) -> Path:
    # We need /opt here because of bug in rrdcached
    return paths.rrd_single_dir / pnp_cleanup(hostname)


def get_cmc_storage(hostname: HostName, service_name: str) -> Storage:
    return Storage(get_cmc_host_dir(hostname) / pnp_cleanup(service_name))


def get_pnp_storage(hostname: HostName, service_name: str, *, metric: str) -> Storage:
    return get_pnp_custom_storage(
        get_pnp_host_dir(hostname), pnp_cleanup(service_name), metric=metric
    )


def get_pnp_xml_storage(hostname: HostName, servicedesc: str) -> Storage:
    host_dir = get_pnp_host_dir(hostname)
    return Storage(host_dir / pnp_cleanup(servicedesc))


def get_pnp_custom_storage(host_dir: Path, prefix: str, *, metric: str) -> Storage:
    return Storage(host_dir / (prefix + "_" + pnp_cleanup(metric)))
