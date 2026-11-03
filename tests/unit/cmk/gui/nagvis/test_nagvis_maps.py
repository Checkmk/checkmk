#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.gui.nagvis._nagvis_maps import _is_nagvis_enabled, _is_nagvis_url


@pytest.mark.parametrize(
    "url, expected",
    [
        # Relative "Edit" footnote link
        ("../nagvis/", True),
        ("../nagvis/index.php?mod=Map&act=view&show=Germany", True),
        # Site-absolute map links as returned by the NagVis getMaps API (CMK-36587)
        ("/prod/nagvis/index.php?mod=Map&act=view&show=Germany", True),
        # Non-NagVis URLs must be rejected
        ("/prod/check_mk/index.py", False),
        ("https://example.com/", False),
        ("../check_mk/", False),
    ],
)
def test_is_nagvis_url(url: str, expected: bool) -> None:
    assert _is_nagvis_url(url, "/prod/") is expected


def _apache_conf_d(omd_root: Path) -> Path:
    conf_d = omd_root / "etc/apache/conf.d"
    conf_d.mkdir(parents=True)
    return conf_d


def test_is_nagvis_enabled_with_linked_apache_conf(tmp_path: Path) -> None:
    (tmp_path / "etc/nagvis").mkdir(parents=True)
    (tmp_path / "etc/nagvis/apache.conf").write_text("")
    (_apache_conf_d(tmp_path) / "nagvis.conf").symlink_to("../../nagvis/apache.conf")
    assert _is_nagvis_enabled(tmp_path)


def test_is_nagvis_disabled_without_apache_conf(tmp_path: Path) -> None:
    _apache_conf_d(tmp_path)
    assert not _is_nagvis_enabled(tmp_path)


def test_is_nagvis_disabled_with_dangling_apache_conf(tmp_path: Path) -> None:
    (_apache_conf_d(tmp_path) / "nagvis.conf").symlink_to("../../nagvis/apache.conf")
    assert not _is_nagvis_enabled(tmp_path)
