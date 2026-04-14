#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from cmk.ccc.hostaddress import HostName
from cmk.utils.misc import pnp_cleanup

# We need to add some space for the RRD backend temporary file
# rrd_create.c:
#   strcpy(tmpfilename, outfilename);
#   strcat(tmpfilename, "XXXXXX");
_RRD_GUARD: Final = 6

# All suffixes that may ever be appended to a Storage path.
# The stem length must not exceed max_filename_length - max(len(suffix)) - _RRD_GUARD
# so that every variant (.info or .rrd) + the RRD backend temp suffix fits within PC_NAME_MAX.
_KNOWN_SUFFIXES: Final = (".info", ".rrd")

RESERVED_FILENAME_LENGTH: Final = max(len(os.fsencode(s)) for s in _KNOWN_SUFFIXES) + _RRD_GUARD


@dataclass(frozen=True)
class Storage:
    _path: Path
    _max_filename_length: int = field(kw_only=True)

    def path(self, suffix: str) -> Path | None:
        # PC_NAME_MAX limits a single filename component (not the full path).
        # MAX_STEM_LENGTH is derived from known suffixes only — crash on unknown ones is allowed.
        max_stem = self._max_filename_length - RESERVED_FILENAME_LENGTH
        if len(os.fsencode(self._path.name)) > max_stem:
            return None
        return self.get_expected_path(suffix)

    def get_expected_path(self, suffix: str) -> Path:
        return attach_suffix(self._path, suffix)


def attach_suffix(p: Path, suffix: str) -> Path:
    return p.with_name(p.name + suffix)


@dataclass(frozen=True, kw_only=True)
class RRDPaths:
    rrd_multiple_dir: Path
    rrd_single_dir: Path
    _max_filename_length: int

    @classmethod
    def from_omd_root(cls, omd_root: Path) -> "RRDPaths":
        opt_root = "/opt" / omd_root.relative_to(omd_root.root)
        return cls(
            rrd_multiple_dir=opt_root / "var/pnp4nagios/perfdata",
            rrd_single_dir=opt_root / "var/check_mk/rrd",
            _max_filename_length=os.pathconf(omd_root, "PC_NAME_MAX"),
        )

    def _storage(self, path: Path) -> Storage:
        return Storage(path, _max_filename_length=self._max_filename_length)

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
