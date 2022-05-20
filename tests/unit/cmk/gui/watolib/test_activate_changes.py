#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import tarfile
import io
import logging
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from werkzeug import datastructures as werkzeug_datastructures

from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.version as cmk_version
import cmk.gui.watolib.activate_changes as activate_changes
import cmk.gui.watolib.utils
from cmk.gui.http import Request
from cmk.gui.watolib.activate_changes import ConfigSyncFileInfo
from cmk.gui.watolib.config_sync import ReplicationPath

import testlib

pytestmark = pytest.mark.usefixtures("load_plugins")
logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def restore_orig_replication_paths():
    _orig_paths = activate_changes._replication_paths[:]
    yield
    activate_changes._replication_paths = _orig_paths


def _expected_replication_paths():
    expected = [
        ReplicationPath('dir', 'check_mk', 'etc/check_mk/conf.d/wato/', []),
        ReplicationPath('dir', 'multisite', 'etc/check_mk/multisite.d/wato/', []),
        ReplicationPath('file', 'htpasswd', 'etc/htpasswd', []),
        ReplicationPath('file', 'auth.secret', 'etc/auth.secret', []),
        ReplicationPath('file', 'auth.serials', 'etc/auth.serials', []),
        ReplicationPath('dir', 'usersettings', 'var/check_mk/web',
                        ['report-thumbnails', 'session_info.mk']),
        ReplicationPath('dir', 'mkps', 'var/check_mk/packages', []),
        ReplicationPath('dir', 'local', 'local', []),
    ]

    if not cmk_version.is_raw_edition():
        expected += [
            ReplicationPath('dir', 'liveproxyd', 'etc/check_mk/liveproxyd.d/wato/', []),
        ]

    if testlib.is_enterprise_repo():
        expected += [
            ReplicationPath('dir', 'dcd', 'etc/check_mk/dcd.d/wato/', []),
            ReplicationPath('dir', 'mknotify', 'etc/check_mk/mknotifyd.d/wato', []),
        ]

    expected += [
        ReplicationPath('dir', 'mkeventd', 'etc/check_mk/mkeventd.d/wato', []),
        ReplicationPath('dir', 'mkeventd_mkp', 'etc/check_mk/mkeventd.d/mkp/rule_packs', []),
        ReplicationPath('file', 'diskspace', 'etc/diskspace.conf', []),
    ]

    if cmk_version.is_managed_edition():
        expected += [
            ReplicationPath(ty='file',
                            ident='customer_check_mk',
                            site_path='etc/check_mk/conf.d/customer.mk',
                            excludes=[]),
            ReplicationPath(ty='file',
                            ident='customer_gui_design',
                            site_path='etc/check_mk/multisite.d/zzz_customer_gui_design.mk',
                            excludes=[]),
            ReplicationPath(ty='file',
                            ident='customer_multisite',
                            site_path='etc/check_mk/multisite.d/customer.mk',
                            excludes=[]),
            ReplicationPath(
                ty='file',
                ident='gui_logo',
                site_path='local/share/check_mk/web/htdocs/themes/classic/images/sidebar_top.png',
                excludes=[]),
            ReplicationPath(
                ty='file',
                ident='gui_logo_dark',
                site_path='local/share/check_mk/web/htdocs/themes/modern-dark/images/mk-logo.png',
                excludes=[]),
            ReplicationPath(
                ty='file',
                ident='gui_logo_facelift',
                site_path='local/share/check_mk/web/htdocs/themes/facelift/images/mk-logo.png',
                excludes=[]),
        ]

    return expected


def test_get_replication_paths_defaults(edition_short, monkeypatch):
    expected = _expected_replication_paths()
    assert sorted(activate_changes.get_replication_paths()) == sorted(expected)


@pytest.mark.parametrize("replicate_ec", [None, True, False])
@pytest.mark.parametrize("replicate_mkps", [None, True, False])
@pytest.mark.parametrize("is_pre_17_remote_site", [True, False])
def test_get_replication_components(edition_short, monkeypatch, replicate_ec, replicate_mkps,
                                    is_pre_17_remote_site):
    partial_site_config = {}
    if replicate_ec is not None:
        partial_site_config["replicate_ec"] = replicate_ec
    if replicate_mkps is not None:
        partial_site_config["replicate_mkps"] = replicate_mkps

    expected = _expected_replication_paths()

    if not replicate_ec:
        expected = [e for e in expected if e.ident not in ["mkeventd", "mkeventd_mkp"]]

    if not replicate_mkps:
        expected = [e for e in expected if e.ident not in ["local", "mkps"]]

    if is_pre_17_remote_site:
        for repl_path in expected:
            if repl_path.ident in {
                    "check_mk", "multisite", "liveproxyd", "mkeventd", "dcd", "mknotify"
            }:
                if "sitespecific.mk" not in repl_path.excludes:
                    repl_path.excludes.append("sitespecific.mk")

            if repl_path.ident == "dcd" and "distributed.mk" not in repl_path.excludes:
                repl_path.excludes.append("distributed.mk")

        expected += [
            ReplicationPath(
                ty="file",
                ident="sitespecific",
                site_path="site_globals/sitespecific.mk",
                excludes=[],
            ),
        ]

    if not is_pre_17_remote_site:
        expected += [
            ReplicationPath(
                ty='file',
                ident='distributed_wato',
                site_path='etc/check_mk/conf.d/distributed_wato.mk',
                excludes=['.*new*'],
            ),
        ]

    assert sorted(
        activate_changes._get_replication_components(partial_site_config,
                                                     is_pre_17_remote_site)) == sorted(expected)


def test_add_replication_paths_pre_17(monkeypatch):
    monkeypatch.setattr(cmk.utils.paths, "omd_root", "/path")
    # dir/file, ident, path, optional list of excludes
    activate_changes.add_replication_paths([
        ("dir", "abc", "/path/to/abc"),
        ("dir", "abc", "/path/to/abc", ["e1", "e2"]),
    ])
    monkeypatch.undo()

    assert activate_changes.get_replication_paths()[-2] == ReplicationPath(
        "dir", "abc", "to/abc", [])
    assert activate_changes.get_replication_paths()[-1] == ReplicationPath(
        "dir", "abc", "to/abc", ["e1", "e2"])


def test_add_replication_paths():
    activate_changes.add_replication_paths([
        ReplicationPath("dir", "abc", "path/to/abc", ["e1", "e2"]),
    ])

    assert activate_changes.get_replication_paths()[-1] == ReplicationPath(
        "dir", "abc", "path/to/abc", ["e1", "e2"])


@pytest.mark.parametrize("expected, site_status", [
    (False, {}),
    (False, {
        "livestatus_version": "1.8.0"
    }),
    (False, {
        "livestatus_version": "1.8.0"
    }),
    (False, {
        "livestatus_version": "1.7.0p2"
    }),
    (False, {
        "livestatus_version": "1.7.0"
    }),
    (False, {
        "livestatus_version": "1.7.0i1"
    }),
    (False, {
        "livestatus_version": "1.7.0-2020.04.20"
    }),
    (True, {
        "livestatus_version": "1.6.0p2"
    }),
    (True, {
        "livestatus_version": "1.5.0p23"
    }),
])
def test_is_pre_17_remote_site(site_status, expected):
    assert cmk.gui.watolib.utils.is_pre_17_remote_site(site_status) == expected


def test_automation_get_config_sync_state():
    get_state = activate_changes.AutomationGetConfigSyncState()
    response = get_state.execute([ReplicationPath("dir", "abc", "etc", [])])
    assert response == (
        {
            'etc/check_mk/multisite.mk':
                (33200, 0, None, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
                ),
            'etc/check_mk/mkeventd.mk':
                (33200, 0, None, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
                ),
            'etc/htpasswd': (33200, 0, None,
                             'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
        },
        0,
    )


def test_get_config_sync_file_infos():
    base_dir = Path(cmk.utils.paths.omd_root) / "replication"
    _create_get_config_sync_file_infos_test_config(base_dir)

    replication_paths = [
        ReplicationPath("dir", "d1-empty", "etc/d1", []),
        ReplicationPath("dir", "d2-not-existing", "etc/d2", []),
        ReplicationPath("dir", "d3-single-file", "etc/d3", []),
        ReplicationPath("dir", "d4-multiple-files", "etc/d4", []),
        ReplicationPath("file", "f1-not-existing", "etc/f1", []),
        ReplicationPath("file", "f2", "bla/blub/f2", []),
        ReplicationPath("dir", "links", "links", []),
    ]
    sync_infos = activate_changes._get_config_sync_file_infos(replication_paths, base_dir)

    assert sync_infos == {
        'bla/blub/f2': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=7,
            link_target=None,
            file_hash='ae973806ace987a1889dc02cfa6b320912b68b6eb3929e425762795955990f35'),
        'etc/d3/xyz': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=5,
            link_target=None,
            file_hash='780518619e3c5dfc931121362c7f14fa8d06457995c762bd818072ed42e6e69e'),
        'etc/d4/layer1/layer2/x3.xyz': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=6,
            link_target=None,
            file_hash='c213b1ced86472704fdc0f77e15cc41f67341c4370def7a0ae9d90bedf37c8ca'),
        'etc/d4/layer1/layer2/x4.xyz': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=6,
            link_target=None,
            file_hash='c213b1ced86472704fdc0f77e15cc41f67341c4370def7a0ae9d90bedf37c8ca'),
        'etc/d4/x1': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=6,
            link_target=None,
            file_hash='1c77fe07e738fd6cbf0075195a773043a7507d53d6deeb1161549244c02ea0ff'),
        'etc/d4/x2': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=6,
            link_target=None,
            file_hash='c213b1ced86472704fdc0f77e15cc41f67341c4370def7a0ae9d90bedf37c8ca'),
        'etc/f1': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=7,
            link_target=None,
            file_hash='4dd985602450dfdeb261cedf8562cb62c5173d1d8bb5f3ca26cd3519add67cf7'),
        'links/broken-symlink': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=3,
            link_target='eeg',
            file_hash=None,
        ),
        'links/working-symlink-to-file': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=13,
            link_target='../etc/d3/xyz',
            file_hash=None,
        ),
        'links/working-symlink-to-dir': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=9,
            link_target='../etc/d3',
            file_hash=None,
        ),
    }


def _create_get_config_sync_file_infos_test_config(base_dir):
    base_dir.joinpath("etc/d1").mkdir(parents=True, exist_ok=True)

    base_dir.joinpath("etc/d3").mkdir(parents=True, exist_ok=True)
    with base_dir.joinpath("etc/d3").joinpath("xyz").open("w", encoding="utf-8") as f:
        f.write(u"Däng")

    base_dir.joinpath("etc/d4").mkdir(parents=True, exist_ok=True)
    with base_dir.joinpath("etc/d4").joinpath("x1").open("w", encoding="utf-8") as f:
        f.write(u"Däng1")
    with base_dir.joinpath("etc/d4").joinpath("x2").open("w", encoding="utf-8") as f:
        f.write(u"Däng2")
    base_dir.joinpath("etc/d4/layer1/layer2").mkdir(parents=True, exist_ok=True)
    with base_dir.joinpath("etc/d4/layer1/layer2").joinpath("x3.xyz").open("w",
                                                                           encoding="utf-8") as f:
        f.write(u"Däng2")

    with base_dir.joinpath("etc/d4/layer1/layer2").joinpath("x4.xyz").open("w",
                                                                           encoding="utf-8") as f:
        f.write(u"Däng2")

    with base_dir.joinpath("etc/f1").open("w", encoding="utf-8") as f:
        f.write(u"Ef-eins")

    base_dir.joinpath("bla/blub").mkdir(parents=True, exist_ok=True)
    with base_dir.joinpath("bla/blub/f2").open("w", encoding="utf-8") as f:
        f.write(u"Ef-zwei")

    base_dir.joinpath("links").mkdir(parents=True, exist_ok=True)
    base_dir.joinpath("links/broken-symlink").symlink_to("eeg")
    base_dir.joinpath("links/working-symlink-to-dir").symlink_to("../etc/d3")
    base_dir.joinpath("links/working-symlink-to-file").symlink_to("../etc/d3/xyz")


def test_get_file_names_to_sync():
    remote, central = _get_test_file_infos()
    to_sync_new, to_sync_changed, to_delete = activate_changes.get_file_names_to_sync(
        logger, central, remote, None)

    assert sorted(to_sync_new + to_sync_changed) == sorted([
        "both-differ-mode",
        "both-differ-size",
        "both-differ-hash",
        "central-only",
        "central-file-remote-link",
        "central-link-remote-file",
        "link-changed",
        "central-link-remote-dir-with-file",
    ])

    assert sorted(to_delete) == sorted([
        "remote-only",
        "central-link-remote-dir-with-file/file",
    ])


def _get_test_file_infos():
    remote = {
        'remote-only': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=2,
            link_target=None,
            file_hash='9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa'),
        'both': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=37,
            link_target=None,
            file_hash='3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08'),
        'both-differ-mode': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash='xbaece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08'),
        'both-differ-size': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash='xbaece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08'),
        'both-differ-hash': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash='xxxece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08'),
        'link-equal': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target='abc',
            file_hash=None,
        ),
        'link-changed': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target='abc',
            file_hash=None,
        ),
        'central-file-remote-link': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash='xxxece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08',
        ),
        'central-link-remote-file': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target='abc',
            file_hash=None,
        ),
        'central-link-remote-dir-with-file/file': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash='xxxece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08',
        ),
    }
    central = {
        'central-only': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=2,
            link_target=None,
            file_hash='9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa'),
        'both': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=37,
            link_target=None,
            file_hash='3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08'),
        'both-differ-mode': ConfigSyncFileInfo(
            st_mode=33202,
            st_size=36,
            link_target=None,
            file_hash='xbaece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08'),
        'both-differ-size': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=38,
            link_target=None,
            file_hash='xbaece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08'),
        'both-differ-hash': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash='3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08'),
        'link-equal': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target='abc',
            file_hash=None,
        ),
        'link-changed': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target='/ddd/abc',
            file_hash=None,
        ),
        'central-file-remote-link': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target='abc',
            file_hash=None,
        ),
        'central-link-remote-file': ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash='3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08',
        ),
        'central-link-remote-dir-with-file': ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target='auuuuu',
            file_hash=None,
        ),
    }

    return remote, central


def test_get_sync_archive(tmp_path):
    sync_archive = _get_test_sync_archive(tmp_path)
    with tarfile.TarFile(mode="r", fileobj=io.BytesIO(sync_archive)) as f:
        assert sorted(f.getnames()) == sorted([
            "etc/abc",
            "file-to-dir/aaa",
            "dir-to-file",
            "ding",
            "broken-symlink",
            "working-symlink",
        ])


def _get_test_sync_archive(tmp_path):
    tmp_path.joinpath("etc").mkdir(parents=True, exist_ok=True)
    with tmp_path.joinpath("etc/abc").open("w", encoding="utf-8") as f:
        f.write(u"gä")

    tmp_path.joinpath("file-to-dir").mkdir(parents=True, exist_ok=True)
    with tmp_path.joinpath("file-to-dir/aaa").open("w", encoding="utf-8") as f:
        f.write(u"gä")

    with tmp_path.joinpath("dir-to-file").open("w", encoding="utf-8") as f:
        f.write(u"di")

    with tmp_path.joinpath("ding").open("w", encoding="utf-8") as f:
        f.write(u"dong")

    tmp_path.joinpath("broken-symlink").symlink_to("eeg")
    tmp_path.joinpath("working-symlink").symlink_to("ding")

    return activate_changes._get_sync_archive([
        "etc/abc",
        "file-to-dir/aaa",
        "ding",
        "dir-to-file",
        "broken-symlink",
        "working-symlink",
    ], tmp_path)


class TestAutomationReceiveConfigSync:
    def test_automation_receive_config_sync(
        self,
        monkeypatch: MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        remote_path = tmp_path.joinpath("remote")
        monkeypatch.setattr(cmk.utils.paths, "omd_root", remote_path)

        # Disable for the moment, because the unit test fake environment is not ready for this yet
        monkeypatch.setattr(cmk.gui.watolib.activate_changes, "_execute_post_config_sync_actions",
                            lambda site_id: None)

        remote_path.mkdir(parents=True, exist_ok=True)

        dir_to_symlink_file = remote_path.joinpath("working-symlink/file")
        dir_to_symlink_file.parent.mkdir(parents=True, exist_ok=True)
        with dir_to_symlink_file.open("w", encoding="utf-8") as f:
            f.write(u"ig")

        dir_to_file = remote_path.joinpath("dir-to-file/file")
        dir_to_file.parent.mkdir(parents=True, exist_ok=True)
        with dir_to_file.open("w", encoding="utf-8") as f:
            f.write(u"fi")

        file_to_dir = remote_path.joinpath("file-to-dir")
        with file_to_dir.open("w", encoding="utf-8") as f:
            f.write(u"za")

        to_delete_path = remote_path.joinpath("to_delete")
        with to_delete_path.open("w", encoding="utf-8") as f:
            f.write(u"äää")

        assert to_delete_path.exists()
        assert not remote_path.joinpath("etc/abc").exists()
        assert not remote_path.joinpath("ding").exists()

        automation = activate_changes.AutomationReceiveConfigSync()
        automation.execute(
            activate_changes.ReceiveConfigSyncRequest(
                site_id="remote",
                sync_archive=_get_test_sync_archive(tmp_path.joinpath("central")),
                to_delete=[
                    "to_delete",
                    "working-symlink/file",
                    "file-to-dir",
                ],
                config_generation=0,
            ))

    def test_get_request(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        request = Request({})
        request.set_var("site_id", "NO_SITE")
        request.set_var("to_delete", "['x/y/z.txt', 'abc.ending']")
        request.set_var("config_generation", "123")
        request.files = werkzeug_datastructures.ImmutableMultiDict({
            "sync_archive": werkzeug_datastructures.FileStorage(
                stream=io.BytesIO(b"some data"),
                filename="sync_archive",
                name="sync_archive",
            )
        })
        monkeypatch.setattr(
            activate_changes,
            "_request",
            request,
        )
        assert (activate_changes.AutomationReceiveConfigSync().get_request() ==
                activate_changes.ReceiveConfigSyncRequest(
                    site_id=SiteId("NO_SITE"),
                    sync_archive=b"some data",
                    to_delete=["x/y/z.txt", "abc.ending"],
                    config_generation=123,
                ))


def test_get_current_config_generation():
    assert activate_changes._get_current_config_generation() == 0
    activate_changes.update_config_generation()
    assert activate_changes._get_current_config_generation() == 1
    activate_changes.update_config_generation()
    activate_changes.update_config_generation()
    assert activate_changes._get_current_config_generation() == 3
