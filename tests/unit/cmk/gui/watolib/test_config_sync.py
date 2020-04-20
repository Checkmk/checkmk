#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import tarfile
import six
from werkzeug.test import create_environ

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path

import pytest  # type: ignore[import]

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.gui.login as login
import cmk.gui.config as config
import cmk.gui.watolib.activate_changes as activate_changes
import cmk.gui.watolib.config_sync as config_sync
import cmk.gui.htmllib as htmllib
from cmk.gui.http import Request
from cmk.gui.globals import AppContext, RequestContext
from testlib.utils import DummyApplication, is_enterprise_repo, is_managed_repo


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


def _create_sync_snapshot(snapshot_manager_class, monkeypatch, tmp_path):
    # TODO: Make this better testable: Extract site snapshot setting calculation
    activation_manager = activate_changes.ActivateChangesManager()
    activation_manager._sites = ["unit", "unit_remote_1"]
    activation_manager._changes_by_site = {"unit": [], "unit_remote_1": []}
    activation_manager._activation_id = "123"
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

    site_snapshot_settings = activation_manager._site_snapshot_settings()

    # Now create the snapshot
    work_dir = tmp_path / "activation"
    snapshot_manager = activate_changes.SnapshotManagerFactory.factory(
        str(work_dir), site_snapshot_settings)
    assert snapshot_manager.__class__.__name__ == snapshot_manager_class

    snapshot_settings = site_snapshot_settings["unit_remote_1"]

    snapshot_manager.generate_snapshots()
    assert Path(snapshot_settings.snapshot_path).exists()
    assert not Path(snapshot_settings.work_dir).exists()

    return snapshot_settings


def editions():
    yield ("cre", "CRESnapshotManager")

    if is_enterprise_repo():
        yield ("cee", "CRESnapshotManager")

    if is_managed_repo():
        yield ("cme", "CMESnapshotManager")


@pytest.mark.parametrize("edition_short,snapshot_manager_class", editions())
def test_generate_snapshot(edition_short, snapshot_manager_class, monkeypatch, tmp_path, with_user):
    user_id = with_user[0]
    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)

    environ = dict(create_environ(), REQUEST_URI='')
    with AppContext(DummyApplication(environ, None)), \
         RequestContext(htmllib.html(Request(environ))):
        login.login(user_id)
        _create_test_sync_config(monkeypatch)
        snapshot_settings = _create_sync_snapshot(snapshot_manager_class, monkeypatch, tmp_path)

    # And now check the resulting snapshot contents
    unpack_dir = tmp_path / "snapshot_unpack"
    with tarfile.open(snapshot_settings.snapshot_path, "r") as t:
        t.extractall(str(unpack_dir))

    expected_subtars = [
        "auth.secret.tar",
        "auth.serials.tar",
        "check_mk.tar",
        "dcd.tar",
        "diskspace.tar",
        "htpasswd.tar",
        "mkeventd_mkp.tar",
        "mkeventd.tar",
        "mknotify.tar",
        "multisite.tar",
        "sitespecific.tar",
        "usersettings.tar",
    ]

    if not cmk_version.is_raw_edition():
        expected_subtars.append("liveproxyd.tar")

    assert sorted(f.name for f in unpack_dir.iterdir()) == sorted(expected_subtars)

    expected_files = {
        'mkeventd_mkp.tar': [],
        'multisite.tar': ["global.mk", "users.mk"],
        'usersettings.tar': [user_id],
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

    # TODO: Shouldn't we clean up these subtle differences?
    if cmk_version.is_managed_edition():
        expected_files.update({
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


@pytest.mark.parametrize("edition_short,snapshot_manager_class", editions())
def test_apply_sync_snapshot(edition_short, snapshot_manager_class, monkeypatch, tmp_path,
                             with_user):
    user_id = with_user[0]
    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)

    environ = dict(create_environ(), REQUEST_URI='')
    with AppContext(DummyApplication(environ, None)), \
         RequestContext(htmllib.html(Request(environ))):
        login.login(user_id)

        _create_test_sync_config(monkeypatch)
        snapshot_settings = _create_sync_snapshot(snapshot_manager_class, monkeypatch, tmp_path)

        # Change unpack target directory from "unit test site" paths to a test specific path
        unpack_dir = tmp_path / "snapshot_unpack"
        components = [
            activate_changes._replace_omd_root(str(unpack_dir), p)
            for p in activate_changes.get_replication_paths()
        ]

        with open(snapshot_settings.snapshot_path, "rb") as f:
            activate_changes.apply_sync_snapshot("unit_remote_1", f.read(), components)

    expected_paths = [
        'etc',
        'var',
        'etc/check_mk',
        'etc/check_mk/mknotifyd.d',
        'etc/check_mk/conf.d',
        # TODO: Why is dcd / mknotifyd in raw edition?
        'etc/check_mk/dcd.d',
        'etc/check_mk/mkeventd.d',
        'etc/check_mk/multisite.d',
        'etc/check_mk/mknotifyd.d/wato',
        'etc/check_mk/conf.d/wato',
        'etc/check_mk/conf.d/wato/hosts.mk',
        'etc/check_mk/conf.d/wato/contacts.mk',
        'etc/check_mk/dcd.d/wato',
        'etc/check_mk/mkeventd.d/mkp',
        'etc/check_mk/mkeventd.d/wato',
        'etc/check_mk/mkeventd.d/mkp/rule_packs',
        'etc/check_mk/multisite.d/wato',
        'etc/check_mk/multisite.d/wato/global.mk',
        'var/check_mk',
        'var/check_mk/web',
        "etc/htpasswd",
        "etc/auth.serials",
        "etc/check_mk/multisite.d/wato/users.mk",
        six.ensure_str('var/check_mk/web/%s' % user_id),
        six.ensure_str('var/check_mk/web/%s/cached_profile.mk' % user_id),
        six.ensure_str('var/check_mk/web/%s/enforce_pw_change.mk' % user_id),
        six.ensure_str('var/check_mk/web/%s/last_pw_change.mk' % user_id),
        six.ensure_str('var/check_mk/web/%s/num_failed_logins.mk' % user_id),
        six.ensure_str('var/check_mk/web/%s/serial.mk' % user_id),
    ]

    # TODO: Shouldn't we clean up these subtle differences?
    if cmk_version.is_managed_edition():
        expected_paths += [
            "etc/check_mk/conf.d/wato/groups.mk",
            "etc/check_mk/mkeventd.d/wato/rules.mk",
            "etc/check_mk/multisite.d/wato/bi.mk",
            "etc/check_mk/multisite.d/wato/customers.mk",
            "etc/check_mk/multisite.d/wato/groups.mk",
            "etc/check_mk/multisite.d/wato/user_connections.mk",
            #"etc/check_mk/conf.d/wato/sitespecific.mk",
            #"etc/check_mk/dcd.d/wato/distributed.mk",
            #"etc/check_mk/dcd.d/wato/sitespecific.mk",
            #"etc/check_mk/mkeventd.d/wato/sitespecific.mk",
            #"etc/check_mk/mknotifyd.d/wato/sitespecific.mk",
            #"etc/check_mk/multisite.d/wato/sitespecific.mk",
        ]

        expected_paths.remove("etc/check_mk/conf.d/wato/hosts.mk")

    if not cmk_version.is_raw_edition():
        expected_paths += [
            'etc/check_mk/liveproxyd.d',
            'etc/check_mk/liveproxyd.d/wato',
            #'etc/check_mk/multisite.d/wato/ca-certificates_sitespecific.mk',
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
