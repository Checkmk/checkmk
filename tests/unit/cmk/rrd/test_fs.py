#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.rrd import RRDPaths

_OPT_ROOT = Path("/opt/omd/sites/heute")
_HOST = HostName("myhost")

# The longest suffix we append (".info") plus the "XXXXXX" rrdtool appends for its temp file
_RESERVED = len(".info") + len("XXXXXX")


def _rrd_paths(max_filename_length: int = 255) -> RRDPaths:
    return RRDPaths(
        omd_root=Path("/omd/sites/heute"),
        opt_root=_OPT_ROOT,
        max_filename_length=max_filename_length,
    )


def test_rrds_of_a_site_are_accessed_below_opt(tmp_path: Path) -> None:
    rrd_paths = RRDPaths.from_omd_root(tmp_path)

    assert (rrd_paths.rrd_single_dir, rrd_paths.rrd_multiple_dir) == (
        Path("/opt") / tmp_path.relative_to("/") / "var/check_mk/rrd",
        Path("/opt") / tmp_path.relative_to("/") / "var/pnp4nagios/perfdata",
    )


def test_cmc_rrd_is_named_after_the_sanitized_service() -> None:
    storage = _rrd_paths().cmc_storage(_HOST, "Filesystem /var:x\\y z")

    assert storage.path(".rrd") == _OPT_ROOT / "var/check_mk/rrd/myhost/Filesystem__var_x_y_z.rrd"


def test_pnp_rrd_is_named_after_the_sanitized_service_and_metric() -> None:
    storage = _rrd_paths().pnp_storage(_HOST, "Filesystem /var", metric="fs used")

    assert (
        storage.path(".rrd")
        == _OPT_ROOT / "var/pnp4nagios/perfdata/myhost/Filesystem__var_fs_used.rrd"
    )


def test_dots_in_service_names_are_kept() -> None:
    storage = _rrd_paths().cmc_storage(_HOST, "Interface 1.2")

    assert storage.path(".info") == _OPT_ROOT / "var/check_mk/rrd/myhost/Interface_1.2.info"


@pytest.mark.parametrize("suffix", [".rrd", ".info"])
def test_longest_allowed_name_gets_a_path(suffix: str) -> None:
    storage = _rrd_paths(max_filename_length=30 + _RESERVED).cmc_storage(_HOST, "x" * 30)

    assert storage.path(suffix) is not None


@pytest.mark.parametrize(
    "service",
    [
        pytest.param("x" * 31, id="one character too long"),
        pytest.param("ä" * 16, id="too many bytes"),
    ],
)
def test_too_long_name_gets_no_path(service: str) -> None:
    storage = _rrd_paths(max_filename_length=30 + _RESERVED).cmc_storage(_HOST, service)

    assert storage.path(".rrd") is None
