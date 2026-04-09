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

MAX_FILENAME_LENGTH: Final = os.pathconf(paths.omd_root, "PC_NAME_MAX")

# All suffixes that may ever be appended to a Storage path.
# The stem length must not exceed MAX_FILENAME_LENGTH - max(len(suffix)) so that
# every variant (.info or .rrd) fits within PC_NAME_MAX.
_KNOWN_SUFFIXES: Final = (".info", ".rrd")
MAX_STEM_LENGTH: Final = MAX_FILENAME_LENGTH - max(len(os.fsencode(s)) for s in _KNOWN_SUFFIXES)


@dataclass(frozen=True)
class Storage:
    _path: Path

    def path(self, suffix: str) -> Path | None:
        # PC_NAME_MAX limits a single filename component (not the full path).
        # MAX_STEM_LENGTH is derived from known suffixes only — crash on unknown ones is allowed.
        if len(os.fsencode(self._path.name)) > MAX_STEM_LENGTH:
            return None
        return self.get_expected_path(suffix)

    def get_expected_path(self, suffix: str) -> Path:
        return attach_suffix(self._path, suffix)


def attach_suffix(p: Path, suffix: str) -> Path:
    return p.with_name(p.name + suffix)


def pnp_host_dir(hostname: HostName) -> Path:
    # We need /opt here because of bug in rrdcached
    return paths.rrd_multiple_dir / pnp_cleanup(hostname)


def cmc_host_dir(hostname: HostName) -> Path:
    # We need /opt here because of bug in rrdcached
    return paths.rrd_single_dir / pnp_cleanup(hostname)


def cmc_storage(hostname: HostName, service_name: str) -> Storage:
    return Storage(cmc_host_dir(hostname) / pnp_cleanup(service_name))


def pnp_storage(hostname: HostName, service_name: str, *, metric: str) -> Storage:
    return pnp_custom_storage(pnp_host_dir(hostname), pnp_cleanup(service_name), metric=metric)


def pnp_xml_storage(hostname: HostName, servicedesc: str) -> Storage:
    host_dir = pnp_host_dir(hostname)
    return Storage(host_dir / pnp_cleanup(servicedesc))


def pnp_custom_storage(host_dir: Path, prefix: str, *, metric: str) -> Storage:
    return Storage(host_dir / (prefix + "_" + pnp_cleanup(metric)))
