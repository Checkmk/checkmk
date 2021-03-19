#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import tarfile
import shutil
from io import IOBase
from typing import Dict, List
from pathlib import Path

from six import ensure_str
import pytest  # type: ignore[import]
import responses  # type: ignore[import]

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.gui.config as config
import cmk.gui.wato.mkeventd
import cmk.gui.watolib.utils as utils
import cmk.gui.watolib.activate_changes as activate_changes
import cmk.gui.watolib.config_sync as config_sync

from testlib.utils import is_enterprise_repo

pytestmark = pytest.mark.usefixtures("load_plugins")


@pytest.fixture(name="mocked_responses")
def fixture_mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(autouse=True)
def fixture_fake_site_states(monkeypatch):
    # During these tests we treat all sites a being online
    monkeypatch.setattr(
        activate_changes.ActivateChanges, "_get_site_status", lambda a, b, c: ({
            "state": "online",
            "livestatus_version": "1.2.3",
            "program_version": "1.2.3",
            "program_start": 0,
            "num_hosts": 123,
            "num_services": 123,
            "core": "cmc",
        }, "online"))


@pytest.fixture(autouse=True)
def fixture_disable_ec_rule_stats_loading(monkeypatch):
    # During CME config computation the EC rule packs are loaded which currently also load the
    # rule usage information from the running EC. Since we do not have a EC running this fails
    # and causes timeouts. Disable this for these tests.
    monkeypatch.setattr(cmk.gui.wato.mkeventd, "_get_rule_stats_from_ec", lambda: {})


def _create_sync_snapshot(activation_manager, snapshot_data_collector_class, monkeypatch, tmp_path,
                          is_pre_17_site):
    _create_test_sync_config(monkeypatch)
    return _generate_sync_snapshot(activation_manager,
                                   snapshot_data_collector_class,
                                   tmp_path,
                                   is_pre_17_site=is_pre_17_site)


def _create_test_sync_config(monkeypatch):
    """Create some config files to be synchronized"""
    conf_dir = Path(cmk.utils.paths.check_mk_config_dir, "wato")
    conf_dir.mkdir(parents=True, exist_ok=True)
    with conf_dir.joinpath("hosts.mk").open("w", encoding="utf-8") as f:
        f.write(u"all_hosts = []\n")

    gui_conf_dir = Path(cmk.utils.paths.default_config_dir) / "multisite.d" / "wato"
    gui_conf_dir.mkdir(parents=True, exist_ok=True)
    with gui_conf_dir.joinpath("global.mk").open("w", encoding="utf-8") as f:
        f.write(u"# 123\n")

    if cmk_version.is_managed_edition():
        monkeypatch.setattr(config,
                            "customers", {
                                "provider": {
                                    "name": "Provider",
                                },
                            },
                            raising=False)


def _get_activation_manager(monkeypatch):
    # TODO: Make this better testable: Extract site snapshot setting calculation
    monkeypatch.setattr(
        config, "sites", {
            "unit": {
                'alias': u'Der Master',
                'disable_wato': True,
                'disabled': False,
                'insecure': False,
                'multisiteurl': '',
                'persist': False,
                'replicate_ec': False,
                'replication': '',
                'timeout': 10,
                'user_login': True,
                'proxy': None,
            },
            "unit_remote_1": {
                'customer': 'provider',
                'url_prefix': '/unit_remote_1/',
                'status_host': None,
                'user_sync': None,
                'socket': ('tcp', {
                    'tls': ('encrypted', {
                        'verify': True
                    }),
                    'address': ('127.0.0.1', 6790)
                }),
                'replication': 'slave',
                'user_login': True,
                'insecure': False,
                'disable_wato': True,
                'disabled': False,
                'alias': u'unit_remote_1',
                'secret': 'watosecret',
                'replicate_mkps': False,
                'proxy': {
                    'params': None
                },
                'timeout': 2,
                'persist': False,
                'replicate_ec': True,
                'multisiteurl': 'http://localhost/unit_remote_1/check_mk/',
            },
        })

    activation_manager = activate_changes.ActivateChangesManager()
    activation_manager._sites = ["unit_remote_1"]
    activation_manager._changes_by_site = {"unit_remote_1": []}
    activation_manager._activation_id = "123"
    return activation_manager


def _generate_sync_snapshot(activation_manager, snapshot_data_collector_class, tmp_path,
                            is_pre_17_site):
    site_snapshot_settings = activation_manager._get_site_snapshot_settings(
        activation_manager._sites)
    snapshot_settings = site_snapshot_settings["unit_remote_1"]

    assert not Path(snapshot_settings.snapshot_path).exists()
    assert not Path(snapshot_settings.work_dir).exists()

    # Now create the snapshot
    work_dir = tmp_path / "activation"
    snapshot_manager = activate_changes.SnapshotManager.factory(str(work_dir),
                                                                site_snapshot_settings)
    assert snapshot_manager._data_collector.__class__.__name__ == snapshot_data_collector_class

    snapshot_manager.generate_snapshots()

    assert Path(snapshot_settings.snapshot_path).exists() == is_pre_17_site
    assert Path(snapshot_settings.work_dir).exists()

    return snapshot_settings


def _get_expected_paths(user_id, is_pre_17_site):
    expected_paths = [
        'etc',
        'var',
        'etc/check_mk',
        'etc/check_mk/conf.d',
        'etc/check_mk/mkeventd.d',
        'etc/check_mk/multisite.d',
        'etc/check_mk/conf.d/wato',
        'etc/check_mk/conf.d/wato/hosts.mk',
        'etc/check_mk/conf.d/wato/contacts.mk',
        'etc/check_mk/mkeventd.d/wato',
        'etc/check_mk/multisite.d/wato',
        'etc/check_mk/multisite.d/wato/global.mk',
        'var/check_mk',
        'var/check_mk/web',
        "etc/htpasswd",
        "etc/auth.serials",
        "etc/check_mk/multisite.d/wato/users.mk",
        ensure_str('var/check_mk/web/%s' % user_id),
        ensure_str('var/check_mk/web/%s/cached_profile.mk' % user_id),
        ensure_str('var/check_mk/web/%s/enforce_pw_change.mk' % user_id),
        ensure_str('var/check_mk/web/%s/last_pw_change.mk' % user_id),
        ensure_str('var/check_mk/web/%s/num_failed_logins.mk' % user_id),
        ensure_str('var/check_mk/web/%s/serial.mk' % user_id),
    ]

    # The new sync directories create all needed files on the central site now
    if not is_pre_17_site:
        expected_paths += [
            'etc/check_mk/apache.d',
            'etc/check_mk/apache.d/wato',
            'etc/check_mk/apache.d/wato/sitespecific.mk',
            'etc/check_mk/conf.d/distributed_wato.mk',
            'etc/check_mk/conf.d/wato/sitespecific.mk',
            'etc/check_mk/mkeventd.d/wato/sitespecific.mk',
            'etc/check_mk/multisite.d/wato/ca-certificates_sitespecific.mk',
            'etc/check_mk/multisite.d/wato/sitespecific.mk',
            'etc/check_mk/rrdcached.d',
            'etc/check_mk/rrdcached.d/wato',
            'etc/check_mk/rrdcached.d/wato/sitespecific.mk',
            'etc/omd',
            'etc/omd/sitespecific.mk',
        ]

        if is_enterprise_repo():
            expected_paths += [
                'etc/check_mk/dcd.d/wato/sitespecific.mk',
                'etc/check_mk/mknotifyd.d/wato/sitespecific.mk',
            ]

        if not cmk_version.is_raw_edition():
            expected_paths += ['etc/check_mk/dcd.d/wato/distributed.mk']

    # TODO: The second condition should not be needed. Seems to be a subtle difference between the
    # CME and CRE/CEE snapshot logic
    if not cmk_version.is_managed_edition():
        expected_paths += [
            'etc/check_mk/mkeventd.d/mkp',
            'etc/check_mk/mkeventd.d/mkp/rule_packs',
        ]

    # The paths are registered once the enterprise plugins are available, independent of the
    # cmk_version.edition_short() value.
    # TODO: The second condition should not be needed. Seems to be a subtle difference between the
    # CME and CRE/CEE snapshot logic
    if is_enterprise_repo() and (not is_pre_17_site or not cmk_version.is_managed_edition()):
        expected_paths += [
            'etc/check_mk/dcd.d',
            'etc/check_mk/dcd.d/wato',
            'etc/check_mk/mknotifyd.d',
            'etc/check_mk/mknotifyd.d/wato',
        ]

    # TODO: Shouldn't we clean up these subtle differences?
    if cmk_version.is_managed_edition():
        expected_paths += [
            "etc/check_mk/conf.d/customer.mk",
            "etc/check_mk/conf.d/wato/groups.mk",
            "etc/check_mk/mkeventd.d/wato/rules.mk",
            "etc/check_mk/multisite.d/customer.mk",
            "etc/check_mk/multisite.d/wato/bi.mk",
            "etc/check_mk/multisite.d/wato/customers.mk",
            "etc/check_mk/multisite.d/wato/groups.mk",
            "etc/check_mk/multisite.d/wato/user_connections.mk",
        ]

        expected_paths.remove("etc/check_mk/conf.d/wato/hosts.mk")

    # TODO: The second condition should not be needed. Seems to be a subtle difference between the
    # CME and CRE/CEE snapshot logic
    if not cmk_version.is_raw_edition() and not cmk_version.is_managed_edition():
        expected_paths += [
            'etc/check_mk/liveproxyd.d',
            'etc/check_mk/liveproxyd.d/wato',
        ]

    return expected_paths


@pytest.mark.usefixtures("register_builtin_html")
def test_generate_snapshot(edition_short, monkeypatch, tmp_path, with_user_login):
    snapshot_data_collector_class = ("CMESnapshotDataCollector"
                                     if edition_short == "cme" else "CRESnapshotDataCollector")

    activation_manager = _get_activation_manager(monkeypatch)
    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)

    monkeypatch.setattr(utils, "is_pre_17_remote_site", lambda s: False)

    snapshot_settings = _create_sync_snapshot(activation_manager,
                                              snapshot_data_collector_class,
                                              monkeypatch,
                                              tmp_path,
                                              is_pre_17_site=False)

    expected_paths = _get_expected_paths(user_id=with_user_login, is_pre_17_site=False)

    work_dir = Path(snapshot_settings.work_dir)
    paths = [str(p.relative_to(work_dir)) for p in work_dir.glob("**/*")]
    assert sorted(paths) == sorted(expected_paths)


@pytest.mark.usefixtures("register_builtin_html")
def test_generate_pre_17_site_snapshot(edition_short, monkeypatch, tmp_path, with_user_login):
    snapshot_data_collector_class = ("CMESnapshotDataCollector"
                                     if edition_short == "cme" else "CRESnapshotDataCollector")

    is_pre_17_site = True
    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)
    monkeypatch.setattr(utils, "is_pre_17_remote_site", lambda s: is_pre_17_site)

    activation_manager = _get_activation_manager(monkeypatch)
    snapshot_settings = _create_sync_snapshot(activation_manager, snapshot_data_collector_class,
                                              monkeypatch, tmp_path, is_pre_17_site)

    # And now check the resulting snapshot contents
    unpack_dir = tmp_path / "snapshot_unpack"
    if unpack_dir.exists():
        shutil.rmtree(str(unpack_dir))

    with tarfile.open(snapshot_settings.snapshot_path, "r") as t:
        t.extractall(str(unpack_dir))

    expected_subtars = [
        "auth.secret.tar",
        "auth.serials.tar",
        "check_mk.tar",
        "diskspace.tar",
        "htpasswd.tar",
        "mkeventd_mkp.tar",
        "mkeventd.tar",
        "multisite.tar",
        "sitespecific.tar",
        "usersettings.tar",
    ]

    if is_enterprise_repo():
        expected_subtars += [
            "dcd.tar",
            "mknotify.tar",
        ]

    if not cmk_version.is_raw_edition():
        expected_subtars.append("liveproxyd.tar")

    if cmk_version.is_managed_edition():
        expected_subtars += [
            "customer_check_mk.tar",
            "customer_gui_design.tar",
            "customer_multisite.tar",
            "gui_logo.tar",
            "gui_logo_dark.tar",
            "gui_logo_facelift.tar",
        ]

    assert sorted(f.name for f in unpack_dir.iterdir()) == sorted(expected_subtars)

    expected_files: Dict[str, List[str]] = {
        'mkeventd_mkp.tar': [],
        'multisite.tar': ["global.mk", "users.mk"],
        'usersettings.tar': [with_user_login],
        'mkeventd.tar': [],
        'check_mk.tar': ["hosts.mk", "contacts.mk"],
        'htpasswd.tar': ["htpasswd"],
        'liveproxyd.tar': [],
        'sitespecific.tar': ['sitespecific.mk'],
        'auth.secret.tar': [],
        'dcd.tar': [],
        'auth.serials.tar': ["auth.serials"],
        'mknotify.tar': [],
        'diskspace.tar': [],
    }

    if cmk_version.is_managed_edition():
        expected_files.update({
            "customer_check_mk.tar": ["customer.mk"],
            "customer_gui_design.tar": [],
            "customer_multisite.tar": ["customer.mk"],
            "gui_logo.tar": [],
            "gui_logo_dark.tar": [],
            "gui_logo_facelift.tar": [],
            # TODO: Shouldn't we clean up these subtle differences?
            "mkeventd.tar": ["rules.mk"],
            'check_mk.tar': ["groups.mk", "contacts.mk"],
            'multisite.tar': [
                "bi.mk",
                "customers.mk",
                "global.mk",
                "groups.mk",
                "user_connections.mk",
                "users.mk",
            ],
        })

    if not cmk_version.is_raw_edition():
        expected_files['liveproxyd.tar'] = []

    # And now check the subtar contents
    for subtar in unpack_dir.iterdir():
        subtar_unpack_dir = unpack_dir / subtar.stem
        subtar_unpack_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(str(subtar), "r") as s:
            s.extractall(str(subtar_unpack_dir))

        files = sorted(str(f.relative_to(subtar_unpack_dir)) for f in subtar_unpack_dir.iterdir())

        assert sorted(expected_files[subtar.name]) == files, \
            "Subtar %s has wrong files" % subtar.name


@pytest.mark.usefixtures("register_builtin_html")
def test_apply_pre_17_sync_snapshot(edition_short, monkeypatch, tmp_path, with_user_login):
    snapshot_data_collector_class = ("CMESnapshotDataCollector"
                                     if edition_short == "cme" else "CRESnapshotDataCollector")

    is_pre_17_site = True
    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)
    monkeypatch.setattr(utils, "is_pre_17_remote_site", lambda s: is_pre_17_site)

    activation_manager = _get_activation_manager(monkeypatch)
    snapshot_settings = _create_sync_snapshot(activation_manager,
                                              snapshot_data_collector_class,
                                              monkeypatch,
                                              tmp_path,
                                              is_pre_17_site=is_pre_17_site)

    # Change unpack target directory from "unit test site" paths to a test specific path
    unpack_dir = tmp_path / "snapshot_unpack"
    if unpack_dir.exists():
        shutil.rmtree(str(unpack_dir))

    with open(snapshot_settings.snapshot_path, "rb") as f:
        activate_changes.apply_pre_17_sync_snapshot("unit_remote_1", f.read(), unpack_dir,
                                                    activate_changes.get_replication_paths())

    expected_paths = _get_expected_paths(user_id=with_user_login, is_pre_17_site=is_pre_17_site)

    if cmk_version.is_managed_edition():
        expected_paths += [
            "etc/check_mk/dcd.d",
            "etc/check_mk/dcd.d/wato",
            "etc/check_mk/liveproxyd.d",
            "etc/check_mk/liveproxyd.d/wato",
            "etc/check_mk/mknotifyd.d",
            "etc/check_mk/mknotifyd.d/wato",
            "etc/check_mk/mkeventd.d/mkp",
            "etc/check_mk/mkeventd.d/mkp/rule_packs",
        ]

    paths = [str(p.relative_to(unpack_dir)) for p in unpack_dir.glob("**/*")]
    assert sorted(paths) == sorted(expected_paths)


@pytest.mark.parametrize("master, slave, result", [
    pytest.param({"first": {
        "customer": "tribe"
    }}, {
        "first": {
            "customer": "tribe"
        },
        "second": {
            "customer": "tribe"
        }
    }, {"first": {
        "customer": "tribe"
    }},
                 id="Delete user from master"),
    pytest.param(
        {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "adminevery"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": []
            }
        }, {}, {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "adminevery"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": []
            }
        },
        id="New users"),
    pytest.param(
        {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "all admins"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": []
            }
        }, {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "adminevery"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": [{
                    "description": "Host on fire"
                }]
            }
        }, {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "all admins"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": [{
                    "description": "Host on fire"
                }]
            }
        },
        id="Update Global user notifications. Retain Customer user notifications"),
])
def test_update_contacts_dict(master, slave, result):
    assert config_sync._update_contacts_dict(master, slave) == result


# This test does not perform the full synchronization. It executes the central site parts and mocks
# the remote site HTTP calls
@pytest.mark.usefixtures("register_builtin_html")
def test_synchronize_site(mocked_responses, monkeypatch, edition_short, tmp_path, mocker):
    if edition_short == "cme":
        pytest.skip("Seems faked site environment is not 100% correct")

    mocked_responses.add(
        method=responses.POST,
        url=
        "http://localhost/unit_remote_1/check_mk/automation.py?command=get-config-sync-state&debug=&secret=watosecret",
        body=repr(({
            'etc/check_mk/conf.d/wato/hosts.mk':
                (33204, 15, None, '0fc4df48a03c3e972a86c9d573bc04f6e2a5d91aa368d7f4ce4ec5cd93ee5725'
                ),
            'etc/check_mk/multisite.d/wato/global.mk':
                (33204, 6, None, '0e10d5fc5aedd798b68706c0189aeccadccae1fa6cc72324524293769336571c'
                ),
            'etc/htpasswd':
                (33204, 0, None, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
        }, 0)),
    )

    mocked_responses.add(
        method=responses.POST,
        url=
        "http://localhost/unit_remote_1/check_mk/automation.py?command=receive-config-sync&debug=&secret=watosecret",
        body="True",
    )

    snapshot_data_collector_class = ("CMESnapshotDataCollector"
                                     if edition_short == "cme" else "CRESnapshotDataCollector")

    is_pre_17_site = False
    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)
    monkeypatch.setattr(utils, "is_pre_17_remote_site", lambda s: is_pre_17_site)

    activation_manager = _get_activation_manager(monkeypatch)
    snapshot_settings = _create_sync_snapshot(activation_manager,
                                              snapshot_data_collector_class,
                                              monkeypatch,
                                              tmp_path,
                                              is_pre_17_site=is_pre_17_site)

    site_activation = activate_changes.ActivateChangesSite("unit_remote_1",
                                                           snapshot_settings,
                                                           activation_manager._activation_id,
                                                           prevent_activate=True)

    site_activation._time_started = time.time()
    site_activation._synchronize_site()


# This test does not perform the full synchronization. It executes the central site parts and mocks
# the remote site HTTP calls
@pytest.mark.usefixtures("register_builtin_html")
def test_synchronize_pre_17_site(monkeypatch, edition_short, tmp_path, mocker):
    snapshot_data_collector_class = ("CMESnapshotDataCollector"
                                     if edition_short == "cme" else "CRESnapshotDataCollector")

    if edition_short == "cme":
        pytest.skip("Seems faked site environment is not 100% correct")

    is_pre_17_site = True
    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)
    monkeypatch.setattr(utils, "is_pre_17_remote_site", lambda s: is_pre_17_site)

    activation_manager = _get_activation_manager(monkeypatch)
    snapshot_settings = _create_sync_snapshot(activation_manager,
                                              snapshot_data_collector_class,
                                              monkeypatch,
                                              tmp_path,
                                              is_pre_17_site=is_pre_17_site)

    site_activation = activate_changes.ActivateChangesSite("unit_remote_1",
                                                           snapshot_settings,
                                                           activation_manager._activation_id,
                                                           prevent_activate=True)

    # Could be better to mock requests instead of our own code
    get_url_mock = mocker.patch("cmk.gui.watolib.automations.get_url", return_value="True")

    site_activation._time_started = time.time()
    site_activation._synchronize_site()

    get_url_mock.assert_called_once()
    args, kwargs = get_url_mock.call_args

    assert args == (
        'http://localhost/unit_remote_1/check_mk/automation.py?command=push-snapshot&debug=&secret=watosecret&siteid=unit_remote_1',
        False)
    assert list(kwargs.keys()) == ["files"]
    assert list(kwargs["files"].keys()) == ["snapshot"]
    # TODO: Add correct type once we are on Python 3 only
    assert isinstance(kwargs["files"]["snapshot"], IOBase)

    file_name = kwargs["files"]["snapshot"].name  # type: ignore[attr-defined]
    assert file_name == snapshot_settings.snapshot_path
