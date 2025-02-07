#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterable
from pathlib import Path

import pytest
import responses
from pytest_mock import MockerFixture

from tests.testlib.utils import is_enterprise_repo, is_managed_repo

from livestatus import SiteId

import cmk.utils.packaging
import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.type_defs import UserId

import cmk.gui.watolib.activate_changes as activate_changes
import cmk.gui.watolib.config_sync as config_sync
from cmk.gui.config import active_config
from cmk.gui.nodevis_lib import topology_dir

from cmk.bi.type_defs import frozen_aggregations_dir


@pytest.fixture(name="mocked_responses")
def fixture_mocked_responses() -> Iterable[responses.RequestsMock]:
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(autouse=True)
def fixture_fake_site_states(monkeypatch: pytest.MonkeyPatch) -> None:
    # During these tests we treat all sites a being online
    monkeypatch.setattr(
        activate_changes.ActivateChanges,
        "_get_site_status",
        lambda a, b, c: (
            {
                "state": "online",
                "livestatus_version": "1.2.3",
                "program_version": "1.2.3",
                "program_start": 0,
                "num_hosts": 123,
                "num_services": 123,
                "core": "cmc",
            },
            "online",
        ),
    )


@pytest.fixture(autouse=True)
def fixture_disable_ec_rule_stats_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    # During CME config computation the EC rule packs are loaded which currently also load the
    # rule usage information from the running EC. Since we do not have a EC running this fails
    # and causes timeouts. Disable this for these tests.
    monkeypatch.setattr(cmk.gui.watolib.mkeventd, "_get_rule_stats_from_ec", lambda: {})


@pytest.fixture(autouse=True)
def fixture_disable_cmk_update_config(monkeypatch: pytest.MonkeyPatch) -> None:
    # During CME config computation the EC rule packs are loaded which currently also load the
    # rule usage information from the running EC. Since we do not have a EC running this fails
    # and causes timeouts. Disable this for these tests.
    monkeypatch.setattr(
        cmk.gui.watolib.activate_changes, "_execute_cmk_update_config", lambda: None
    )


def _create_sync_snapshot(
    activation_manager: activate_changes.ActivateChangesManager,
    snapshot_data_collector_class: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    remote_site: SiteId,
    edition: cmk_version.Edition,
) -> activate_changes.SnapshotSettings:
    _create_test_sync_config(monkeypatch)
    return _generate_sync_snapshot(
        activation_manager,
        snapshot_data_collector_class,
        tmp_path,
        remote_site=remote_site,
        edition=edition,
    )


def _create_test_sync_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create some config files to be synchronized"""
    conf_dir = Path(cmk.utils.paths.check_mk_config_dir, "wato")
    conf_dir.mkdir(parents=True, exist_ok=True)
    with conf_dir.joinpath("hosts.mk").open("w", encoding="utf-8") as f:
        f.write("all_hosts = []\n")

    (cmk.utils.paths.omd_root / "local").mkdir(parents=True, exist_ok=True)
    Path(cmk.utils.paths.var_dir, "packages").mkdir(parents=True, exist_ok=True)
    frozen_aggregations_dir.mkdir(parents=True, exist_ok=True)
    topology_dir.mkdir(parents=True, exist_ok=True)

    gui_conf_dir = Path(cmk.utils.paths.default_config_dir) / "multisite.d" / "wato"
    gui_conf_dir.mkdir(parents=True, exist_ok=True)
    with gui_conf_dir.joinpath("global.mk").open("w", encoding="utf-8") as f:
        f.write("# 123\n")

    stored_passwords_dir = Path(cmk.utils.paths.var_dir)
    with stored_passwords_dir.joinpath("stored_passwords").open("w", encoding="utf-8") as f:
        f.write("DUMMY_PWD_ENTRY \n")

    if cmk_version.is_managed_edition():
        monkeypatch.setattr(
            active_config,
            "customers",
            {
                "provider": {
                    "name": "Provider",
                },
            },
            raising=False,
        )
        dummy_password: dict[str, dict[str, None | str | list]] = {
            "password_1": {
                "title": "testpwd",
                "comment": "",
                "docu_url": "",
                "password": "",
                "owned_by": None,
                "shared_with": [],
                "customer": "provider",
            }
        }
        monkeypatch.setattr(
            cmk.gui.watolib.password_store.PasswordStore,
            "load_for_reading",
            lambda x: dummy_password,
        )


def _get_activation_manager(
    monkeypatch: pytest.MonkeyPatch, remote_site: SiteId = SiteId("unit_remote_1")
) -> activate_changes.ActivateChangesManager:
    # TODO: Make this better testable: Extract site snapshot setting calculation
    remote_sites = {
        "unit_remote_1": {
            "customer": "provider",
            "url_prefix": "/unit_remote_1/",
            "status_host": None,
            "user_sync": None,
            "socket": (
                "tcp",
                {"tls": ("encrypted", {"verify": True}), "address": ("127.0.0.1", 6790)},
            ),
            "replication": "slave",
            "user_login": True,
            "insecure": False,
            "disable_wato": True,
            "disabled": False,
            "alias": "unit_remote_1",
            "secret": "watosecret",
            "replicate_mkps": False,
            "proxy": {"params": None},
            "timeout": 2,
            "persist": False,
            "replicate_ec": True,
            "multisiteurl": "http://localhost/unit_remote_1/check_mk/",
        },
        "unit_remote_2": {
            "customer": "provider",
            "url_prefix": "/unit_remote_1/",
            "status_host": None,
            "user_sync": None,
            "socket": (
                "tcp",
                {"tls": ("encrypted", {"verify": True}), "address": ("127.0.0.1", 6790)},
            ),
            "replication": "slave",
            "user_login": True,
            "insecure": False,
            "disable_wato": True,
            "disabled": False,
            "alias": "unit_remote_1",
            "secret": "watosecret",
            "replicate_mkps": True,
            "proxy": {"params": None},
            "timeout": 2,
            "persist": False,
            "replicate_ec": True,
            "multisiteurl": "http://localhost/unit_remote_1/check_mk/",
        },
    }

    monkeypatch.setattr(
        active_config,
        "sites",
        {
            "unit": {
                "alias": "Der Master",
                "disable_wato": True,
                "disabled": False,
                "insecure": False,
                "multisiteurl": "",
                "persist": False,
                "replicate_ec": False,
                "replication": "",
                "timeout": 10,
                "user_login": True,
                "proxy": None,
            },
            remote_site: remote_sites[remote_site],
        },
    )

    activation_manager = activate_changes.ActivateChangesManager()
    activation_manager._sites = [remote_site]
    activation_manager._changes_by_site = {remote_site: []}
    activation_manager._activation_id = "123"
    return activation_manager


def _generate_sync_snapshot(
    activation_manager: activate_changes.ActivateChangesManager,
    snapshot_data_collector_class: str,
    tmp_path: Path,
    remote_site: SiteId,
    *,
    edition: cmk_version.Edition,
) -> activate_changes.SnapshotSettings:
    assert activation_manager._activation_id is not None
    site_snapshot_settings = activation_manager._get_site_snapshot_settings(
        activation_manager._activation_id, activation_manager._sites
    )
    snapshot_settings = site_snapshot_settings[remote_site]

    assert not Path(snapshot_settings.snapshot_path).exists()
    assert not Path(snapshot_settings.work_dir).exists()

    # Now create the snapshot
    work_dir = tmp_path / "activation"
    snapshot_manager = activate_changes.SnapshotManager.factory(
        str(work_dir), site_snapshot_settings, edition
    )
    assert snapshot_manager._data_collector.__class__.__name__ == snapshot_data_collector_class

    snapshot_manager.generate_snapshots()

    assert Path(snapshot_settings.work_dir).exists()

    return snapshot_settings


def _get_expected_paths(
    user_id: UserId, with_local: bool, edition: cmk_version.Edition
) -> list[str]:
    expected_paths = [
        "etc",
        "var",
        "etc/check_mk",
        "etc/check_mk/conf.d",
        "etc/check_mk/mkeventd.d",
        "etc/check_mk/multisite.d",
        "etc/check_mk/conf.d/wato",
        "etc/check_mk/conf.d/wato/hosts.mk",
        "etc/check_mk/conf.d/wato/contacts.mk",
        "etc/check_mk/mkeventd.d/wato",
        "etc/check_mk/multisite.d/wato",
        "etc/check_mk/multisite.d/wato/global.mk",
        "var/check_mk",
        "var/check_mk/web",
        "etc/htpasswd",
        "etc/auth.serials",
        "etc/check_mk/multisite.d/wato/users.mk",
        "var/check_mk/web/%s" % user_id,
        "var/check_mk/web/%s/cached_profile.mk" % user_id,
        "var/check_mk/web/%s/enforce_pw_change.mk" % user_id,
        "var/check_mk/web/%s/last_pw_change.mk" % user_id,
        "var/check_mk/web/%s/num_failed_logins.mk" % user_id,
        "var/check_mk/web/%s/serial.mk" % user_id,
        "var/check_mk/stored_passwords",
        "var/check_mk/frozen_aggregations",
    ]

    # The new sync directories create all needed files on the central site now
    expected_paths += [
        "etc/check_mk/apache.d",
        "etc/check_mk/apache.d/wato",
        "etc/check_mk/apache.d/wato/sitespecific.mk",
        "etc/check_mk/conf.d/distributed_wato.mk",
        "etc/check_mk/conf.d/wato/sitespecific.mk",
        "etc/check_mk/mkeventd.d/wato/sitespecific.mk",
        "etc/check_mk/multisite.d/wato/ca-certificates_sitespecific.mk",
        "etc/check_mk/multisite.d/wato/sitespecific.mk",
        "etc/check_mk/rrdcached.d",
        "etc/check_mk/rrdcached.d/wato",
        "etc/check_mk/rrdcached.d/wato/sitespecific.mk",
        "etc/omd",
        "etc/omd/sitespecific.mk",
    ]

    if edition is not cmk_version.Edition.CRE:
        expected_paths += [
            "etc/check_mk/dcd.d/wato/distributed.mk",
            "etc/check_mk/dcd.d",
            "etc/check_mk/dcd.d/wato",
            "etc/check_mk/dcd.d/wato/sitespecific.mk",
            "etc/check_mk/mknotifyd.d",
            "etc/check_mk/mknotifyd.d/wato",
            "etc/check_mk/mknotifyd.d/wato/sitespecific.mk",
        ]

    if edition is not cmk_version.Edition.CME:
        expected_paths += ["etc/omd/site.conf"]

    # TODO: The second condition should not be needed. Seems to be a subtle difference between the
    # CME and CRE/CEE snapshot logic
    if edition is not cmk_version.Edition.CME:
        expected_paths += [
            "etc/check_mk/mkeventd.d/mkp",
            "etc/check_mk/mkeventd.d/mkp/rule_packs",
            "etc/check_mk/mkeventd.d/wato/rules.mk",
            "local",
            "var/check_mk/packages",
            "var/check_mk/disabled_packages",
            "var/check_mk/packages_local",
            "var/check_mk/topology",
        ]

    # TODO: Shouldn't we clean up these subtle differences?
    if edition is cmk_version.Edition.CME:
        expected_paths += [
            "etc/check_mk/conf.d/customer.mk",
            "etc/check_mk/conf.d/wato/groups.mk",
            "etc/check_mk/conf.d/wato/passwords.mk",
            "etc/check_mk/mkeventd.d/wato/rules.mk",
            "etc/check_mk/multisite.d/customer.mk",
            "etc/check_mk/multisite.d/wato/bi_config.bi",
            "etc/check_mk/multisite.d/wato/customers.mk",
            "etc/check_mk/multisite.d/wato/groups.mk",
            "etc/check_mk/multisite.d/wato/user_connections.mk",
        ]

        if with_local:
            expected_paths += [
                "local",
                "var/check_mk/packages",
            ]

        expected_paths = [
            p for p in expected_paths if p not in {"etc/check_mk/conf.d/wato/hosts.mk"}
        ]

    # TODO: The second condition should not be needed. Seems to be a subtle difference between the
    # CME and CRE/CEE snapshot logic
    if edition not in (cmk_version.Edition.CRE, cmk_version.Edition.CME):
        expected_paths += [
            "etc/check_mk/liveproxyd.d",
            "etc/check_mk/liveproxyd.d/wato",
        ]

    # The below lines are confusing and incorrect. The reason we need them is
    # because our test environments do not reflect our Checkmk editions properly.
    # We cannot fix that in the short (or even mid) term because the
    # precondition is a more cleanly separated structure.

    if is_enterprise_repo() and edition is cmk_version.Edition.CRE:
        # CEE paths are added when the CEE plugins for WATO are available, i.e.
        # when the "enterprise/" path is present.
        expected_paths += [
            "etc/check_mk/dcd.d",
            "etc/check_mk/dcd.d/wato",
            "etc/check_mk/dcd.d/wato/sitespecific.mk",
            "etc/check_mk/dcd.d/wato/distributed.mk",
            "etc/check_mk/mknotifyd.d",
            "etc/check_mk/mknotifyd.d/wato",
            "etc/check_mk/mknotifyd.d/wato/sitespecific.mk",
            "etc/check_mk/liveproxyd.d",
            "etc/check_mk/liveproxyd.d/wato",
        ]

    if is_managed_repo() and edition is not cmk_version.Edition.CME:
        # CME paths are added when the CME plugins for WATO are available, i.e.
        # when the "managed/" path is present.
        expected_paths += [
            "local/share",
            "local/share/check_mk",
            "local/share/check_mk/web",
            "local/share/check_mk/web/htdocs",
            "local/share/check_mk/web/htdocs/themes",
            "local/share/check_mk/web/htdocs/themes/facelift",
            "local/share/check_mk/web/htdocs/themes/facelift/images",
            "local/share/check_mk/web/htdocs/themes/modern-dark",
            "local/share/check_mk/web/htdocs/themes/modern-dark/images",
        ]

    return expected_paths


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize("remote_site", [SiteId("unit_remote_1"), SiteId("unit_remote_2")])
def test_generate_snapshot(
    edition: cmk_version.Edition,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    with_user_login: UserId,
    remote_site: SiteId,
) -> None:
    snapshot_data_collector_class = (
        "CMESnapshotDataCollector"
        if edition is cmk_version.Edition.CME
        else "CRESnapshotDataCollector"
    )

    activation_manager = _get_activation_manager(monkeypatch, remote_site)

    snapshot_settings = _create_sync_snapshot(
        activation_manager,
        snapshot_data_collector_class,
        monkeypatch,
        tmp_path,
        remote_site=remote_site,
        edition=edition,
    )

    expected_paths = _get_expected_paths(
        user_id=with_user_login,
        with_local=active_config.sites[remote_site].get("replicate_mkps", False),
        edition=edition,
    )

    work_dir = Path(snapshot_settings.work_dir)
    paths = [str(p.relative_to(work_dir)) for p in work_dir.glob("**/*")]
    assert sorted(paths) == sorted(expected_paths)


@pytest.mark.parametrize(
    "master, slave, result",
    [
        pytest.param(
            {"first": {"customer": "tribe"}},
            {"first": {"customer": "tribe"}, "second": {"customer": "tribe"}},
            {"first": {"customer": "tribe"}},
            id="Delete user from master",
        ),
        pytest.param(
            {
                "cmkadmin": {
                    "customer": None,
                    "notification_rules": [{"description": "adminevery"}],
                },
                "first": {"customer": "tribe", "notification_rules": []},
            },
            {},
            {
                "cmkadmin": {
                    "customer": None,
                    "notification_rules": [{"description": "adminevery"}],
                },
                "first": {"customer": "tribe", "notification_rules": []},
            },
            id="New users",
        ),
        pytest.param(
            {
                "cmkadmin": {
                    "customer": None,
                    "notification_rules": [{"description": "all admins"}],
                },
                "first": {"customer": "tribe", "notification_rules": []},
            },
            {
                "cmkadmin": {
                    "customer": None,
                    "notification_rules": [{"description": "adminevery"}],
                },
                "first": {
                    "customer": "tribe",
                    "notification_rules": [{"description": "Host on fire"}],
                },
            },
            {
                "cmkadmin": {
                    "customer": None,
                    "notification_rules": [{"description": "all admins"}],
                },
                "first": {
                    "customer": "tribe",
                    "notification_rules": [{"description": "Host on fire"}],
                },
            },
            id="Update Global user notifications. Retain Customer user notifications",
        ),
    ],
)
def test_update_contacts_dict(master: dict, slave: dict, result: dict) -> None:
    assert config_sync._update_contacts_dict(master, slave) == result


# This test does not perform the full synchronization. It executes the central site parts and mocks
# the remote site HTTP calls
@pytest.mark.usefixtures("request_context")
def test_synchronize_site(  # type:ignore[no-untyped-def]
    mocked_responses: responses.RequestsMock,
    monkeypatch: pytest.MonkeyPatch,
    edition: cmk_version.Edition,
    tmp_path: Path,
    mocker: MockerFixture,
):
    if edition is cmk_version.Edition.CME:
        pytest.skip("Seems faked site environment is not 100% correct")

    mocked_responses.add(
        method=responses.POST,
        url="http://localhost/unit_remote_1/check_mk/automation.py?command=get-config-sync-state",
        body=repr(
            (
                {
                    "etc/check_mk/conf.d/wato/hosts.mk": (
                        33204,
                        15,
                        None,
                        "0fc4df48a03c3e972a86c9d573bc04f6e2a5d91aa368d7f4ce4ec5cd93ee5725",
                    ),
                    "etc/check_mk/multisite.d/wato/global.mk": (
                        33204,
                        6,
                        None,
                        "0e10d5fc5aedd798b68706c0189aeccadccae1fa6cc72324524293769336571c",
                    ),
                    "etc/htpasswd": (
                        33204,
                        0,
                        None,
                        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    ),
                },
                0,
            )
        ),
    )

    mocked_responses.add(
        method=responses.POST,
        url="http://localhost/unit_remote_1/check_mk/automation.py?command=receive-config-sync",
        body="True",
    )

    snapshot_data_collector_class = (
        "CMESnapshotDataCollector"
        if edition is cmk_version.Edition.CME
        else "CRESnapshotDataCollector"
    )

    monkeypatch.setattr(cmk_version, "is_raw_edition", lambda: edition is cmk_version.Edition.CRE)
    monkeypatch.setattr(
        cmk_version, "is_managed_edition", lambda: edition is cmk_version.Edition.CME
    )

    activation_manager = _get_activation_manager(monkeypatch)
    assert activation_manager._activation_id is not None
    snapshot_settings = _create_sync_snapshot(
        activation_manager,
        snapshot_data_collector_class,
        monkeypatch,
        tmp_path,
        remote_site=SiteId("unit_remote_1"),
        edition=edition,
    )

    site_activation = activate_changes.ActivateChangesSite(
        SiteId("unit_remote_1"),
        snapshot_settings,
        activation_manager._activation_id,
        prevent_activate=True,
    )

    site_activation._time_started = time.time()
    site_activation._synchronize_site()
