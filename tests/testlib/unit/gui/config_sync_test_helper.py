#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

"""Shared helpers for config sync tests across editions."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from livestatus import NetworkSocketDetails, SiteConfiguration, TLSParams

import cmk.ccc.version as cmk_version
import cmk.gui.mkeventd.wato
import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.nodevis.utils import topology_configs_dir
from cmk.gui.watolib import activate_changes, config_sync
from cmk.messaging import rabbitmq


def setup_fake_site_states(monkeypatch: pytest.MonkeyPatch) -> None:
    """During these tests we treat all sites as being online"""
    monkeypatch.setattr(
        activate_changes,
        "get_status_for_site",
        lambda a, b: (
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


def setup_disable_ec_rule_stats_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    # During CME config computation the EC rule packs are loaded which currently also load the
    # rule usage information from the running EC. Since we do not have a EC running this fails
    # and causes timeouts. Disable this for these tests.
    monkeypatch.setattr(cmk.gui.mkeventd.wato, "_get_rule_stats_from_ec", dict)


def setup_disable_cmk_update_config(monkeypatch: pytest.MonkeyPatch) -> None:
    # During CME config computation the EC rule packs are loaded which currently also load the
    # rule usage information from the running EC. Since we do not have a EC running this fails
    # and causes timeouts. Disable this for these tests.
    monkeypatch.setattr(
        cmk.gui.watolib.activate_changes, "_execute_cmk_update_config", lambda: None
    )


@contextmanager
def create_sync_snapshot(
    activation_manager: activate_changes.ActivateChangesManager,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    remote_site: SiteId,
    edition: cmk_version.Edition,
) -> Iterator[config_sync.SnapshotSettings]:
    with create_test_sync_config(monkeypatch):
        yield generate_sync_snapshot(
            activation_manager,
            tmp_path,
            remote_site=remote_site,
            edition=edition,
        )


@contextmanager
def create_test_sync_config(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Create some config files to be synchronized"""
    conf_dir = cmk.utils.paths.check_mk_config_dir / "wato"
    conf_dir.mkdir(parents=True, exist_ok=True)
    with conf_dir.joinpath("hosts.mk").open("w", encoding="utf-8") as f:
        f.write("all_hosts = []\n")

    (cmk.utils.paths.omd_root / "local").mkdir(parents=True, exist_ok=True)
    (cmk.utils.paths.var_dir / "packages").mkdir(parents=True, exist_ok=True)
    topology_configs_dir.mkdir(parents=True, exist_ok=True)

    gui_conf_dir = cmk.utils.paths.default_config_dir / "multisite.d/wato"
    gui_conf_dir.mkdir(parents=True, exist_ok=True)
    with gui_conf_dir.joinpath("global.mk").open("w", encoding="utf-8") as f:
        f.write("# 123\n")

    stored_passwords_dir = cmk.utils.paths.var_dir
    with stored_passwords_dir.joinpath("stored_passwords").open("w", encoding="utf-8") as f:
        f.write("DUMMY_PWD_ENTRY \n")

    with monkeypatch.context() as m:
        if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.ULTIMATEMT:
            m.setattr(
                active_config,
                "customers",
                {"provider": {"name": "Provider"}},
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
            m.setattr(
                cmk.gui.watolib.password_store.PasswordStore,
                "load_for_reading",
                lambda x: dummy_password,
            )
        yield


def get_site_configuration(remote_site: SiteId) -> SiteConfiguration:
    # TODO: Make this better testable: Extract site snapshot setting calculation
    if remote_site == SiteId("unit_remote_1"):
        return SiteConfiguration(
            id=SiteId("unit_remote_1"),
            customer="provider",
            url_prefix="/unit_remote_1/",
            status_host=None,
            socket=(
                "tcp",
                NetworkSocketDetails(
                    address=("127.0.0.1", 6790),
                    tls=("encrypted", TLSParams(verify=True)),
                ),
            ),
            replication="slave",
            user_login=True,
            insecure=False,
            disable_wato=True,
            disabled=False,
            alias="unit_remote_1",
            secret="watosecret",
            replicate_mkps=False,
            proxy={"params": None},
            timeout=2,
            persist=False,
            replicate_ec=True,
            multisiteurl="http://localhost/unit_remote_1/check_mk/",
            message_broker_port=5672,
            is_trusted=False,
        )
    if remote_site == SiteId("unit_remote_2"):
        return SiteConfiguration(
            id=SiteId("unit_remote_2"),
            customer="provider",
            url_prefix="/unit_remote_1/",
            status_host=None,
            socket=(
                "tcp",
                NetworkSocketDetails(
                    address=("127.0.0.1", 6790),
                    tls=("encrypted", TLSParams(verify=True)),
                ),
            ),
            replication="slave",
            user_login=True,
            insecure=False,
            disable_wato=True,
            disabled=False,
            alias="unit_remote_1",
            secret="watosecret",
            replicate_mkps=True,
            proxy={"params": None},
            timeout=2,
            persist=False,
            replicate_ec=True,
            multisiteurl="http://localhost/unit_remote_1/check_mk/",
            message_broker_port=5672,
            is_trusted=False,
        )
    raise ValueError(remote_site)


@contextmanager
def get_activation_manager(
    monkeypatch: pytest.MonkeyPatch, remote_site: SiteId
) -> Iterator[activate_changes.ActivateChangesManager]:
    with monkeypatch.context() as m:
        m.setattr(
            active_config,
            "sites",
            {
                SiteId("unit"): SiteConfiguration(
                    id=SiteId("unit"),
                    alias="Die Zentrale",
                    disable_wato=True,
                    url_prefix="/unit/",
                    disabled=False,
                    insecure=False,
                    multisiteurl="",
                    message_broker_port=5672,
                    persist=False,
                    replicate_ec=False,
                    replicate_mkps=False,
                    replication=None,
                    status_host=None,
                    socket=(
                        "tcp",
                        NetworkSocketDetails(
                            address=("127.0.0.1", 6790),
                            tls=("encrypted", TLSParams(verify=True)),
                        ),
                    ),
                    timeout=10,
                    user_login=True,
                    proxy=None,
                    is_trusted=False,
                ),
                remote_site: get_site_configuration(remote_site),
            },
        )

        activation_manager = activate_changes.ActivateChangesManager()
        activation_manager._sites = [remote_site]
        activation_manager.changes._changes_by_site = {remote_site: []}
        activation_manager._activation_id = "123"
        yield activation_manager


def generate_sync_snapshot(
    activation_manager: activate_changes.ActivateChangesManager,
    tmp_path: Path,
    remote_site: SiteId,
    *,
    edition: cmk_version.Edition,
) -> config_sync.SnapshotSettings:
    snapshot_data_collector_class = (
        "CMESnapshotDataCollector"
        if edition is cmk_version.Edition.ULTIMATEMT
        else "CRESnapshotDataCollector"
    )

    assert activation_manager._activation_id is not None
    site_snapshot_settings = activation_manager._get_site_snapshot_settings(
        activation_manager._activation_id,
        {site_id: active_config.sites[site_id] for site_id in activation_manager._sites},
        {remote_site: rabbitmq.Definitions()},
    )
    snapshot_settings = site_snapshot_settings[remote_site]

    assert not Path(snapshot_settings.snapshot_path).exists()
    assert not Path(snapshot_settings.work_dir).exists()

    # Now create the snapshot
    work_dir = tmp_path / "activation"
    snapshot_manager = activate_changes.activation_features_registry[
        str(edition)
    ].snapshot_manager_factory(str(work_dir), site_snapshot_settings)
    assert snapshot_manager._data_collector.__class__.__name__ == snapshot_data_collector_class

    snapshot_manager.generate_snapshots()

    assert Path(snapshot_settings.work_dir).exists()

    return snapshot_settings
