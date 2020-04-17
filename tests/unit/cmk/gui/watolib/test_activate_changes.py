#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.utils.paths
import cmk.utils.version as cmk_version
import cmk.gui.watolib.activate_changes as activate_changes
from cmk.gui.watolib.config_sync import ReplicationPath
import testlib


@pytest.fixture(autouse=True)
def restore_orig_replication_paths():
    _orig_paths = activate_changes._replication_paths[:]
    yield
    activate_changes._replication_paths = _orig_paths


@pytest.mark.parametrize("edition_short", ["cre", "cee", "cme"])
def test_get_replication_paths_defaults(edition_short, monkeypatch):
    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)

    expected = [
        ReplicationPath('dir', 'check_mk',
                        '%s/etc/check_mk/conf.d/wato/' % cmk.utils.paths.omd_root,
                        ['sitespecific.mk']),
        ReplicationPath('dir', 'multisite',
                        '%s/etc/check_mk/multisite.d/wato/' % cmk.utils.paths.omd_root,
                        ['sitespecific.mk']),
        ReplicationPath('file', 'htpasswd', '%s/etc/htpasswd' % cmk.utils.paths.omd_root, []),
        ReplicationPath('file', 'auth.secret', '%s/etc/auth.secret' % cmk.utils.paths.omd_root, []),
        ReplicationPath('file', 'auth.serials', '%s/etc/auth.serials' % cmk.utils.paths.omd_root,
                        []),
        ReplicationPath('dir', 'usersettings', '%s/var/check_mk/web' % cmk.utils.paths.omd_root,
                        ['*/report-thumbnails']),
        ReplicationPath('dir', 'mkps', '%s/var/check_mk/packages' % cmk.utils.paths.omd_root, []),
        ReplicationPath('dir', 'local', '%s/local' % cmk.utils.paths.omd_root, []),
    ]

    if not cmk_version.is_raw_edition():
        expected += [
            ReplicationPath('dir', 'liveproxyd',
                            '%s/etc/check_mk/liveproxyd.d/wato/' % cmk.utils.paths.omd_root,
                            ['sitespecific.mk']),
        ]

    if testlib.is_enterprise_repo():
        expected += [
            ReplicationPath('dir', 'dcd', '%s/etc/check_mk/dcd.d/wato/' % cmk.utils.paths.omd_root,
                            ['sitespecific.mk', 'distributed.mk']),
            ReplicationPath('dir', 'mknotify',
                            '%s/etc/check_mk/mknotifyd.d/wato/' % cmk.utils.paths.omd_root,
                            ['sitespecific.mk']),
        ]

    expected += [
        ReplicationPath('dir', 'mkeventd',
                        '%s/etc/check_mk/mkeventd.d/wato' % cmk.utils.paths.omd_root,
                        ['sitespecific.mk']),
        ReplicationPath('dir', 'mkeventd_mkp',
                        '%s/etc/check_mk/mkeventd.d/mkp/rule_packs' % cmk.utils.paths.omd_root, []),
        ReplicationPath('file', 'diskspace', '%s/etc/diskspace.conf' % cmk.utils.paths.omd_root,
                        []),
    ]

    assert sorted(activate_changes.get_replication_paths()) == sorted(expected)


def test_add_replication_paths_pre_17():
    # dir/file, ident, path, optional list of excludes
    activate_changes.add_replication_paths([
        ("dir", "abc", "/path/to/abc"),
        ("dir", "abc", "/path/to/abc", ["e1", "e2"]),
    ])

    assert activate_changes.get_replication_paths()[-2] == ReplicationPath(
        "dir", "abc", "/path/to/abc", [])
    assert activate_changes.get_replication_paths()[-1] == ReplicationPath(
        "dir", "abc", "/path/to/abc", ["e1", "e2"])


def test_add_replication_paths():
    activate_changes.add_replication_paths([
        ReplicationPath("dir", "abc", "/path/to/abc", ["e1", "e2"]),
    ])

    assert activate_changes.get_replication_paths()[-1] == ReplicationPath(
        "dir", "abc", "/path/to/abc", ["e1", "e2"])
