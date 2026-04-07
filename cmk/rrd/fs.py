#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from dataclasses import dataclass, field
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.utils.misc import pnp_cleanup


@dataclass(frozen=True)
class Storage:
    _path: Path
    max_filename_length: int = field(kw_only=True)

    def path(self, suffix: str) -> Path | None:
        path = self.get_expected_path(suffix)
        if len(os.fsencode(path)) >= self.max_filename_length:
            return None
        return path

    def get_expected_path(self, suffix: str) -> Path:
        return attach_suffix(self._path, suffix)


def attach_suffix(p: Path, suffix: str) -> Path:
    return p.with_name(p.name + suffix)


@dataclass(frozen=True)
class RRDPaths:
    rrd_multiple_dir: Path
    rrd_single_dir: Path
    max_filename_length: int

    @classmethod
    def from_omd_root(cls, omd_root: Path) -> "RRDPaths":
        opt_root = "/opt" / omd_root.relative_to(omd_root.root)
        return cls(
            rrd_multiple_dir=opt_root / "var/pnp4nagios/perfdata",
            rrd_single_dir=opt_root / "var/check_mk/rrd",
            max_filename_length=os.pathconf(omd_root, "PC_NAME_MAX"),
        )

    def _storage(self, path: Path) -> Storage:
        return Storage(path, max_filename_length=self.max_filename_length)

    def pnp_host_dir(self, hostname: HostName) -> Path:
        # We need /opt here because of bug in rrdcached
        return self.rrd_multiple_dir / pnp_cleanup(hostname)

    def cmc_host_dir(self, hostname: HostName) -> Path:
        # We need /opt here because of bug in rrdcached
        return self.rrd_single_dir / pnp_cleanup(hostname)

    def cmc_storage(self, hostname: HostName, service_name: str) -> Storage:
        return self._storage(self.cmc_host_dir(hostname) / pnp_cleanup(service_name))

    def pnp_storage(self, hostname: HostName, service_name: str, *, metric: str) -> Storage:
        return self.pnp_custom_storage(
            self.pnp_host_dir(hostname), pnp_cleanup(service_name), metric=metric
        )

    def pnp_xml_storage(self, hostname: HostName, servicedesc: str) -> Storage:
        host_dir = self.pnp_host_dir(hostname)
        return self._storage(host_dir / pnp_cleanup(servicedesc))

    def pnp_custom_storage(self, host_dir: Path, prefix: str, *, metric: str) -> Storage:
        return self._storage(host_dir / (prefix + "_" + pnp_cleanup(metric)))
