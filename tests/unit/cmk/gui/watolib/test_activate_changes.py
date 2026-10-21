#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import io
import json
import logging
import os
import tarfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import override

import pytest
from werkzeug.test import create_environ

import cmk.gui.watolib.automations
import cmk.utils.paths
from cmk.ccc import store as ccc_store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.background_job.job import JobStatusStates
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request
from cmk.gui.sites import SiteStatus
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.userdb import get_user_attributes
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib import activate_changes
from cmk.gui.watolib import activate_changes as activate_changes_module
from cmk.gui.watolib.activate_changes import (
    _confirm_activated_changes,
    _distribute_piggyback_hub_configs,
    activate_remote_site,
    ActivateChanges,
    ActivateChangesManager,
    ActivationCleanupJob,
    ConfigSyncFileInfo,
    ConfigWarnings,
    default_rabbitmq_definitions,
    RemoteActivationBackgroundJob,
    RemoteActivationCrash,
    RemoteActivationStatus,
    sort_for_activation,
)
from cmk.gui.watolib.automations import MKRemoteSiteUnavailable
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ActivationContext,
    config_domain_registry,
    ConfigDomainName,
    DomainRequest,
    EXPERIMENTAL_FLAGS,
    OMD,
    SerializedSettings,
    SITE_CERTIFICATE,
)
from cmk.gui.watolib.config_sync import (
    ReplicationPath,
    ReplicationPathType,
)
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.site_changes import ChangeSpec, SiteChanges
from cmk.livestatus_client import (
    AuthenticationConnectionEntry,
    BrokerConnection,
    BrokerConnections,
    BrokerSite,
    ConnectionId,
    NetworkSocketDetails,
    SAMLAuthenticationEntry,
    SiteConfiguration,
    SiteConfigurations,
)
from cmk.messaging import CMKConnectionError, rabbitmq
from cmk.utils.automation_config import RemoteAutomationConfig
from cmk.utils.config_warnings import ConfigurationWarnings
from tests.testlib.unit.fake_site import pop_crash_report_file
from tests.testlib.unit.rabbitmq import get_expected_definition

logger = logging.getLogger(__name__)


def default_site_config() -> SiteConfiguration:
    return SiteConfiguration(
        id=SiteId("mysite"),
        alias="Site mysite",
        socket=("local", None),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix="/mysite/",
        multisiteurl="",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


@pytest.mark.usefixtures("request_context")
def test_active_connectors_for_user_preservation_includes_saml_connection_id() -> None:
    """SAML auth entries contribute the inner ``connection_id``, not the
    ``("saml", {...})`` tuple itself."""
    site_config = default_site_config()
    saml_entry: SAMLAuthenticationEntry = {"connection_id": "my_saml"}
    entries: list[AuthenticationConnectionEntry] = [("saml", saml_entry)]
    site_config["authentication_connections"] = entries
    assert activate_changes._active_connectors_for_user_preservation(site_config) == ["my_saml"]  # noqa: SLF001


@pytest.mark.usefixtures("remote_site")
def test_active_connectors_for_user_preservation_uses_propagated_attr_sync(
    load_config: Config,
) -> None:
    """On a remote site the attribute-sync connection list configured on the
    central site arrives via the propagated global; the seeded ``"all"`` in
    the remote's own ``sites.mk`` entry must not shadow it."""
    site_config = default_site_config()
    assert site_config["user_attribute_sync_connections"] == "all"  # the seeded self-default
    load_config.user_attribute_sync_connections = ["ldap_x"]
    load_config.authentication_connections = []
    assert activate_changes._active_connectors_for_user_preservation(site_config) == ["ldap_x"]  # noqa: SLF001


@pytest.mark.usefixtures("request_context")
def test_automation_get_config_sync_state() -> None:
    get_state = activate_changes.AutomationGetConfigSyncState()
    response = get_state.execute(
        [
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="abc",
                site_path="etc",
            )
        ]
    )
    assert response == (
        {
            "etc/check_mk/multisite.mk": (
                33200,
                0,
                None,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "etc/check_mk/mkeventd.mk": (
                33200,
                0,
                None,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "etc/check_mk/multisite.d/sites.mk": (
                33200,
                511,
                None,
                "718908c63cb855cdc56236425e995ff78b48d3d6024afa28af81dd609e07ba00",
            ),
            "etc/check_mk/mkeventd.d/wato/rules.mk": (
                33200,
                147,
                None,
                "b129ce86d7aa063c31b0de5062196082744813a1ab506308aae36e5919badc50",
            ),
            "etc/htpasswd": (
                33200,
                0,
                None,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "etc/passwordlist.txt": (
                33200,
                0,
                None,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            "etc/omd/site.conf": (
                33200,
                1037,
                None,
                "aa98b0e40b81e121cbed10c1e621cb7869b81f544e648f7208b2aaaa41563116",
            ),
        },
        0,
    )


def test_get_config_sync_file_infos() -> None:
    base_dir = cmk.utils.paths.omd_root / "replication"
    _create_get_config_sync_file_infos_test_config(base_dir)

    replication_paths = [
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="d1-empty",
            site_path="etc/d1",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="d2-not-existing",
            site_path="etc/d2",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="d3-single-file",
            site_path="etc/d3",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="d4-multiple-files",
            site_path="etc/d4",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="f1-not-existing",
            site_path="etc/f1",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="f2",
            site_path="bla/blub/f2",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="links",
            site_path="links",
        ),
    ]
    sync_infos = activate_changes._get_config_sync_file_infos(replication_paths, base_dir)  # noqa: SLF001

    assert sync_infos == {
        "bla/blub/f2": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=7,
            link_target=None,
            file_hash="ae973806ace987a1889dc02cfa6b320912b68b6eb3929e425762795955990f35",
        ),
        "etc/d3/xyz": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=5,
            link_target=None,
            file_hash="780518619e3c5dfc931121362c7f14fa8d06457995c762bd818072ed42e6e69e",
        ),
        "etc/d4/layer1/layer2/x3.xyz": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=6,
            link_target=None,
            file_hash="c213b1ced86472704fdc0f77e15cc41f67341c4370def7a0ae9d90bedf37c8ca",
        ),
        "etc/d4/layer1/layer2/x4.xyz": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=6,
            link_target=None,
            file_hash="c213b1ced86472704fdc0f77e15cc41f67341c4370def7a0ae9d90bedf37c8ca",
        ),
        "etc/d4/x1": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=6,
            link_target=None,
            file_hash="1c77fe07e738fd6cbf0075195a773043a7507d53d6deeb1161549244c02ea0ff",
        ),
        "etc/d4/x2": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=6,
            link_target=None,
            file_hash="c213b1ced86472704fdc0f77e15cc41f67341c4370def7a0ae9d90bedf37c8ca",
        ),
        "etc/f1": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=7,
            link_target=None,
            file_hash="4dd985602450dfdeb261cedf8562cb62c5173d1d8bb5f3ca26cd3519add67cf7",
        ),
        "links/broken-symlink": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=3,
            link_target="eeg",
            file_hash=None,
        ),
        "links/working-symlink-to-file": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=13,
            link_target="../etc/d3/xyz",
            file_hash=None,
        ),
        "links/working-symlink-to-dir": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=9,
            link_target="../etc/d3",
            file_hash=None,
        ),
    }


def _create_get_config_sync_file_infos_test_config(base_dir: Path) -> None:
    base_dir.joinpath("etc/d1").mkdir(parents=True, exist_ok=True)

    base_dir.joinpath("etc/d3").mkdir(parents=True, exist_ok=True)
    with base_dir.joinpath("etc/d3").joinpath("xyz").open("w", encoding="utf-8") as f:
        f.write("Däng")

    base_dir.joinpath("etc/d4").mkdir(parents=True, exist_ok=True)
    with base_dir.joinpath("etc/d4").joinpath("x1").open("w", encoding="utf-8") as f:
        f.write("Däng1")
    with base_dir.joinpath("etc/d4").joinpath("x2").open("w", encoding="utf-8") as f:
        f.write("Däng2")
    base_dir.joinpath("etc/d4/layer1/layer2").mkdir(parents=True, exist_ok=True)
    with (
        base_dir.joinpath("etc/d4/layer1/layer2")
        .joinpath("x3.xyz")
        .open("w", encoding="utf-8") as f
    ):
        f.write("Däng2")

    with (
        base_dir.joinpath("etc/d4/layer1/layer2")
        .joinpath("x4.xyz")
        .open("w", encoding="utf-8") as f
    ):
        f.write("Däng2")

    with base_dir.joinpath("etc/f1").open("w", encoding="utf-8") as f:
        f.write("Ef-eins")

    base_dir.joinpath("bla/blub").mkdir(parents=True, exist_ok=True)
    with base_dir.joinpath("bla/blub/f2").open("w", encoding="utf-8") as f:
        f.write("Ef-zwei")

    base_dir.joinpath("links").mkdir(parents=True, exist_ok=True)
    base_dir.joinpath("links/broken-symlink").symlink_to("eeg")
    base_dir.joinpath("links/working-symlink-to-dir").symlink_to("../etc/d3")
    base_dir.joinpath("links/working-symlink-to-file").symlink_to("../etc/d3/xyz")


@pytest.mark.usefixtures("request_context")
def test_get_file_names_to_sync_without_file_sync() -> None:
    remote, central = _get_test_file_infos()
    sync_delta = activate_changes.get_file_names_to_sync(
        site_logger=logger,
        sync_state=activate_changes.SyncState(
            central_file_infos=central, remote_file_infos=remote, remote_config_generation=0
        ),
        file_sync_enabled=False,
        file_filter_func=None,
    )

    assert sorted(sync_delta.to_sync_new + sync_delta.to_sync_changed) == sorted(
        [
            "both-differ-mode",
            "both-differ-size",
            "both-differ-hash",
            "central-only",
            "central-file-remote-link",
            "central-link-remote-file",
            "link-changed",
            "central-link-remote-dir-with-file",
        ]
    )

    assert sorted(sync_delta.to_delete) == sorted(
        [
            "remote-only",
            "central-link-remote-dir-with-file/file",
        ]
    )


@pytest.mark.usefixtures("request_context")
def test_get_file_names_to_sync_with_file_sync() -> None:
    remote, central = _get_test_file_infos()
    central["var/check_mk/web/orphaned/some_file"] = remote[
        "var/check_mk/web/orphaned/some_file"
    ] = ConfigSyncFileInfo(
        st_mode=33200,
        st_size=37,
        link_target=None,
        file_hash="3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb09",
    )
    remote["var/check_mk/web/remote_only/some_file"] = ConfigSyncFileInfo(
        st_mode=33200,
        st_size=37,
        link_target=None,
        file_hash="3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb09",
    )
    sync_delta = activate_changes.get_file_names_to_sync(
        site_logger=logger,
        sync_state=activate_changes.SyncState(
            central_file_infos=central, remote_file_infos=remote, remote_config_generation=0
        ),
        file_sync_enabled=True,
        file_filter_func=None,
    )

    assert sorted(sync_delta.to_sync_new + sync_delta.to_sync_changed) == sorted(
        [
            "both-differ-mode",
            "both-differ-size",
            "both-differ-hash",
            "central-only",
            "central-file-remote-link",
            "central-link-remote-file",
            "link-changed",
            "central-link-remote-dir-with-file",
        ]
    )

    assert sorted(sync_delta.to_delete) == sorted(
        [
            "remote-only",
            "central-link-remote-dir-with-file/file",
        ]
    )


def _get_test_file_infos() -> tuple[dict[str, ConfigSyncFileInfo], dict[str, ConfigSyncFileInfo]]:
    remote = {
        "remote-only": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=2,
            link_target=None,
            file_hash="9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        ),
        "both": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=37,
            link_target=None,
            file_hash="3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "both-differ-mode": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash="xbaece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "both-differ-size": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash="xbaece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "both-differ-hash": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash="xxxece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "link-equal": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target="abc",
            file_hash=None,
        ),
        "link-changed": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target="abc",
            file_hash=None,
        ),
        "central-file-remote-link": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash="xxxece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "central-link-remote-file": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target="abc",
            file_hash=None,
        ),
        "central-link-remote-dir-with-file/file": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash="xxxece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
    }
    central = {
        "central-only": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=2,
            link_target=None,
            file_hash="9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        ),
        "both": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=37,
            link_target=None,
            file_hash="3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "both-differ-mode": ConfigSyncFileInfo(
            st_mode=33202,
            st_size=36,
            link_target=None,
            file_hash="xbaece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "both-differ-size": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=38,
            link_target=None,
            file_hash="xbaece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "both-differ-hash": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash="3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "link-equal": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target="abc",
            file_hash=None,
        ),
        "link-changed": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target="/ddd/abc",
            file_hash=None,
        ),
        "central-file-remote-link": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target="abc",
            file_hash=None,
        ),
        "central-link-remote-file": ConfigSyncFileInfo(
            st_mode=33200,
            st_size=36,
            link_target=None,
            file_hash="3baece9027e3e7e034d693c1bcd4bc64c5171135d562295cd482920ed9c8eb08",
        ),
        "central-link-remote-dir-with-file": ConfigSyncFileInfo(
            st_mode=41471,
            st_size=1,
            link_target="auuuuu",
            file_hash=None,
        ),
    }

    return remote, central


def test_get_sync_archive(tmp_path: Path) -> None:
    sync_archive = _get_test_sync_archive(tmp_path)
    with tarfile.TarFile(mode="r", fileobj=io.BytesIO(sync_archive)) as f:
        assert sorted(f.getnames()) == sorted(
            [
                "etc/abc",
                "file-to-dir/aaa",
                "dir-to-file",
                "ding",
                "broken-symlink",
                "working-symlink",
            ]
        )


def _get_test_sync_archive(tmp_path: Path) -> bytes:
    tmp_path.joinpath("etc").mkdir(parents=True, exist_ok=True)
    with tmp_path.joinpath("etc/abc").open("w", encoding="utf-8") as f:
        f.write("gä")

    tmp_path.joinpath("file-to-dir").mkdir(parents=True, exist_ok=True)
    with tmp_path.joinpath("file-to-dir/aaa").open("w", encoding="utf-8") as f:
        f.write("gä")

    with tmp_path.joinpath("dir-to-file").open("w", encoding="utf-8") as f:
        f.write("di")

    with tmp_path.joinpath("ding").open("w", encoding="utf-8") as f:
        f.write("dong")

    tmp_path.joinpath("broken-symlink").symlink_to("eeg")
    tmp_path.joinpath("working-symlink").symlink_to("ding")

    return activate_changes._get_sync_archive(  # noqa: SLF001
        [
            "etc/abc",
            "file-to-dir/aaa",
            "ding",
            "dir-to-file",
            "broken-symlink",
            "working-symlink",
        ],
        tmp_path,
    )


class TestAutomationReceiveConfigSync:
    @pytest.mark.usefixtures("request_context")
    def test_automation_receive_config_sync(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        remote_path = tmp_path / "remote"
        monkeypatch.setattr(cmk.utils.paths, "omd_root", remote_path)

        # Disable for the moment, because the unit test fake environment is not ready for this yet
        monkeypatch.setattr(
            cmk.gui.watolib.activate_changes,
            "_execute_post_config_sync_actions",
            lambda site_id, local_files_changed, use_git: None,  # noqa: ARG005
        )

        remote_path.mkdir(parents=True, exist_ok=True)

        dir_to_symlink_file = remote_path.joinpath("working-symlink/file")
        dir_to_symlink_file.parent.mkdir(parents=True, exist_ok=True)
        with dir_to_symlink_file.open("w", encoding="utf-8") as f:
            f.write("ig")

        dir_to_file = remote_path.joinpath("dir-to-file/file")
        dir_to_file.parent.mkdir(parents=True, exist_ok=True)
        with dir_to_file.open("w", encoding="utf-8") as f:
            f.write("fi")

        file_to_dir = remote_path.joinpath("file-to-dir")
        with file_to_dir.open("w", encoding="utf-8") as f:
            f.write("za")

        to_delete_path = remote_path.joinpath("to_delete")
        with to_delete_path.open("w", encoding="utf-8") as f:
            f.write("äää")

        assert to_delete_path.exists()
        assert not remote_path.joinpath("etc/abc").exists()
        assert not remote_path.joinpath("ding").exists()

        automation = activate_changes.AutomationReceiveConfigSync()
        automation.execute(
            activate_changes.ReceiveConfigSyncRequest(
                site_id=SiteId("remote"),
                sync_archive=_get_test_sync_archive(tmp_path.joinpath("central")),
                to_delete=[
                    "to_delete",
                    "working-symlink/file",
                    "file-to-dir",
                ],
                config_generation=0,
                use_git=False,
                site_config=SiteConfiguration(
                    id=SiteId("remote"),
                    alias="remote site",
                    disable_wato=True,
                    disabled=False,
                    insecure=False,
                    multisiteurl="http://127.0.0.1/remote/check_mk/",
                    persist=False,
                    replicate_ec=True,
                    replicate_mkps=True,
                    replication="slave",
                    message_broker_port=5673,
                    secret="watosecret",
                    status_host=None,
                    timeout=2,
                    user_login=True,
                    url_prefix="/remote/",
                    proxy=None,
                    socket=(
                        "tcp",
                        NetworkSocketDetails(
                            address=("127.0.0.1", 6790),
                            tls=("encrypted", {"verify": True}),
                        ),
                    ),
                    authentication_connections=("all", ["ldap", "saml"]),
                    user_attribute_sync_connections="all",
                    is_trusted=False,
                ),
                user_attributes=get_user_attributes([]),
            )
        )

        assert not to_delete_path.exists()
        assert remote_path.joinpath("etc/abc").exists()
        assert remote_path.joinpath("ding").exists()

        assert not dir_to_symlink_file.exists()
        assert dir_to_symlink_file.parent.is_symlink()

        assert not dir_to_file.parent.is_dir()
        assert dir_to_file.parent.exists()

        assert file_to_dir.is_dir()
        assert file_to_dir.joinpath("aaa").exists()

    def test_get_request(self) -> None:
        request = Request(
            create_environ(
                method="POST",
                data={
                    "site_id": "NO_SITE",
                    "to_delete": "['x/y/z.txt', 'abc.ending', '/ä/☃/☕']",
                    "config_generation": "123",
                    "sync_archive": (
                        io.BytesIO(b"some data"),
                        "sync_archive",
                        "sync_archive",
                    ),
                },
            )
        )
        config = Config()
        config.sites = SiteConfigurations(
            {
                SiteId("NO_SITE"): SiteConfiguration(
                    id=SiteId("NO_SITE"),
                    alias="NO_SITE site",
                    disable_wato=True,
                    disabled=False,
                    insecure=False,
                    multisiteurl="http://127.0.0.1/NO_SITE/check_mk/",
                    persist=False,
                    replicate_ec=False,
                    replicate_mkps=False,
                    replication=None,
                    message_broker_port=5673,
                    secret="watosecret",
                    status_host=None,
                    timeout=2,
                    user_login=True,
                    url_prefix="/NO_SITE/",
                    proxy=None,
                    socket=("local", None),
                    user_attribute_sync_connections="all",
                    is_trusted=False,
                )
            }
        )
        r = activate_changes.AutomationReceiveConfigSync().get_request(config, request)
        assert r.site_id == SiteId("NO_SITE")
        assert r.sync_archive == b"some data"
        assert r.to_delete == ["x/y/z.txt", "abc.ending", "/ä/☃/☕"]
        assert r.config_generation == 123
        assert r.use_git is False
        assert r.site_config == config.sites[SiteId("NO_SITE")]
        assert sorted([e[0] for e in r.user_attributes]) == sorted(
            [e[0] for e in get_user_attributes(config.wato_user_attrs)]
        )


def test_get_current_config_generation() -> None:
    assert activate_changes._get_current_config_generation() == 0  # noqa: SLF001
    activate_changes.update_config_generation()
    assert activate_changes._get_current_config_generation() == 1  # noqa: SLF001
    activate_changes.update_config_generation()
    activate_changes.update_config_generation()
    assert activate_changes._get_current_config_generation() == 3  # noqa: SLF001


def test_activation_cleanup_background_job(caplog: pytest.LogCaptureFixture) -> None:
    act_dir = (
        cmk.utils.paths.tmp_dir / "wato" / "activation" / "9a61e24f-d991-4710-b8e7-04700c309594"
    )
    act_dir.mkdir(parents=True, exist_ok=True)
    (act_dir / "info.mk").write_text(
        repr(
            {
                "_sites": ["heute"],
                "_activate_until": "bf4b5431-bb60-4c89-973b-147b9e012188",
                "_comment": None,
                "_activate_foreign": False,
                "_activation_id": "9a61e24f-d991-4710-b8e7-04700c309594",
                "_time_started": 1720800187.7206023,
                "_persisted_changes": [
                    {
                        "id": "bf4b5431-bb60-4c89-973b-147b9e012188",
                        "user_id": "cmkadmin",
                        "action_name": "edit-folder",
                        "text": "Edited properties of folder Main",
                        "time": 1720800176.985953,
                    }
                ],
            }
        )
    )
    (act_dir / "site_heute.mk").write_text(
        repr(
            {
                "_site_id": "heute",
                "_activation_id": "9a61e24f-d991-4710-b8e7-04700c309594",
                "_phase": "done",
                "_state": "success",
                "_status_text": "Success",
                "_status_details": "Started at: 21:49:52. Finished at: 21:49:57.",
                "_time_started": 1720800192.3661854,
                "_time_updated": 1720800197.2661166,
                "_time_ended": 1720800197.2661166,
                "_expected_duration": 4.40388298034668,
                "_pid": 794410,
                "_user_id": "cmkadmin",
                "_source": "GUI",
            }
        )
    )
    os.utime(act_dir, (1720800187.7206023, 1720800187.7206023))

    with caplog.at_level(logging.INFO, logger="cmk.web"):
        ActivationCleanupJob().do_execute()
    assert any("Activation cleanup finished" in m for m in caplog.messages)
    assert not act_dir.exists()


@pytest.mark.parametrize(
    "site_configs, peer_to_peer_connections, expected_definitions",
    [
        pytest.param(
            {},
            {},
            {},
            id="no connection",
        ),
        pytest.param(
            {
                SiteId("remote_1"): SiteConfiguration(
                    id=SiteId("remote_1"),
                    alias="remote site",
                    disable_wato=True,
                    disabled=False,
                    insecure=False,
                    multisiteurl="http://127.0.0.1/remote_1/check_mk/",
                    persist=False,
                    replicate_ec=True,
                    replicate_mkps=True,
                    replication="slave",
                    message_broker_port=5673,
                    secret="watosecret",
                    status_host=None,
                    timeout=2,
                    user_login=True,
                    url_prefix="/heute/",
                    proxy=None,
                    socket=(
                        "tcp",
                        NetworkSocketDetails(
                            address=("127.0.0.1", 6790),
                            tls=("encrypted", {"verify": True}),
                        ),
                    ),
                    user_attribute_sync_connections="all",
                    is_trusted=False,
                ),
            },
            {},
            get_expected_definition("NO_SITE", {"remote_1": 5673}, {}),
            id="replicated site",
        ),
        pytest.param(
            {
                SiteId("remote_1"): SiteConfiguration(
                    id=SiteId("remote_1"),
                    alias="remote site",
                    disable_wato=True,
                    disabled=False,
                    insecure=False,
                    multisiteurl="http://127.0.0.1:5001/remote_1/check_mk/",
                    persist=False,
                    replicate_ec=True,
                    replicate_mkps=True,
                    replication="slave",
                    message_broker_port=5672,
                    secret="watosecret",
                    status_host=None,
                    timeout=2,
                    user_login=True,
                    url_prefix="/heute/",
                    proxy=None,
                    socket=(
                        "tcp",
                        NetworkSocketDetails(
                            address=("127.0.0.1", 6790),
                            tls=("encrypted", {"verify": True}),
                        ),
                    ),
                    user_attribute_sync_connections="all",
                    is_trusted=False,
                ),
            },
            {},
            get_expected_definition("NO_SITE", {"remote_1": 5672}, {}),
            id="replicated site with apache port in multisiteurl",
        ),
        pytest.param(
            {
                SiteId("remote_1"): SiteConfiguration(
                    id=SiteId("remote_1"),
                    alias="remote site",
                    disable_wato=True,
                    disabled=False,
                    insecure=False,
                    multisiteurl="http://127.0.0.1/remote_1/check_mk/",
                    persist=False,
                    replicate_ec=True,
                    replicate_mkps=True,
                    replication="slave",
                    message_broker_port=5673,
                    secret="watosecret",
                    status_host=None,
                    timeout=2,
                    user_login=True,
                    url_prefix="/heute/",
                    proxy=None,
                    socket=(
                        "tcp",
                        NetworkSocketDetails(
                            address=("127.0.0.1", 6790),
                            tls=("encrypted", {"verify": True}),
                        ),
                    ),
                    user_attribute_sync_connections="all",
                    is_trusted=False,
                ),
                "remote_2": SiteConfiguration(
                    id=SiteId("remote_2"),
                    alias="remote site 2",
                    disable_wato=True,
                    disabled=False,
                    insecure=False,
                    multisiteurl="http://127.0.0.1/remote_2/check_mk/",
                    persist=False,
                    replicate_ec=True,
                    replicate_mkps=True,
                    replication="slave",
                    message_broker_port=5674,
                    secret="watosecret",
                    status_host=None,
                    timeout=2,
                    user_login=True,
                    url_prefix="/heute/",
                    proxy=None,
                    socket=(
                        "tcp",
                        NetworkSocketDetails(
                            address=("127.0.0.1", 6791),
                            tls=("encrypted", {"verify": True}),
                        ),
                    ),
                    user_attribute_sync_connections="all",
                    is_trusted=False,
                ),
            },
            BrokerConnections(
                {
                    ConnectionId("test"): BrokerConnection(
                        connecter=BrokerSite(site_id=SiteId("remote_1")),
                        connectee=BrokerSite(site_id=SiteId("remote_2")),
                    )
                }
            ),
            get_expected_definition(
                "NO_SITE", {"remote_1": 5673, "remote_2": 5674}, {"remote_1": "remote_2"}
            ),
            id="peer to peer connection",
        ),
        pytest.param(
            {
                SiteId("remote_1"): SiteConfiguration(
                    id=SiteId("remote_1"),
                    alias="remote site",
                    disable_wato=True,
                    disabled=False,
                    insecure=False,
                    multisiteurl="http://127.0.0.1/remote_1/check_mk/",
                    persist=False,
                    replicate_ec=True,
                    replicate_mkps=True,
                    replication="slave",
                    message_broker_port=5673,
                    secret="watosecret",
                    status_host=None,
                    timeout=2,
                    user_login=True,
                    url_prefix="/heute/",
                    proxy=None,
                    socket=(
                        "tcp",
                        NetworkSocketDetails(
                            address=("127.0.0.1", 6790),
                            tls=("encrypted", {"verify": True}),
                        ),
                    ),
                    user_attribute_sync_connections="all",
                    is_trusted=False,
                ),
                SiteId("remote_2"): SiteConfiguration(
                    id=SiteId("remote_2"),
                    alias="remote site 2",
                    disable_wato=True,
                    disabled=False,
                    insecure=False,
                    multisiteurl="http://127.0.0.1: 5001/remote_2/check_mk/",
                    persist=False,
                    replicate_ec=True,
                    replicate_mkps=True,
                    replication="slave",
                    message_broker_port=5674,
                    secret="watosecret",
                    status_host=None,
                    timeout=2,
                    user_login=True,
                    url_prefix="/heute/",
                    proxy=None,
                    socket=(
                        "tcp",
                        NetworkSocketDetails(
                            address=("127.0.0.1", 6791),
                            tls=("encrypted", {"verify": True}),
                        ),
                    ),
                    user_attribute_sync_connections="all",
                    is_trusted=False,
                ),
            },
            BrokerConnections(
                {
                    ConnectionId("test"): BrokerConnection(
                        connecter=BrokerSite(site_id=SiteId("remote_1")),
                        connectee=BrokerSite(site_id=SiteId("remote_2")),
                    )
                }
            ),
            get_expected_definition(
                "NO_SITE", {"remote_1": 5673, "remote_2": 5674}, {"remote_1": "remote_2"}
            ),
            id="peer to peer connection with apache port in multisiteurl",
        ),
    ],
)
def test_default_rabbitmq_definitions(
    site_configs: Mapping[SiteId, SiteConfiguration],
    peer_to_peer_connections: BrokerConnections,
    expected_definitions: Mapping[str, rabbitmq.Definitions],
) -> None:
    actual_definitions = default_rabbitmq_definitions(site_configs, peer_to_peer_connections)
    assert dict(actual_definitions) == expected_definitions


def _make_local_site_config(site_id: SiteId, disabled: bool = False) -> SiteConfiguration:
    return SiteConfiguration(
        id=site_id,
        alias=f"Site {site_id}",
        socket=("local", None),
        disable_wato=True,
        disabled=disabled,
        insecure=False,
        url_prefix=f"/{site_id}/",
        multisiteurl="",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication=None,
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


def _make_change_spec(
    change_id: str,
    user_id: str = "cmkadmin",
    has_been_activated: bool = False,
    change_time: float = 1720800176.0,
) -> ChangeSpec:
    return ChangeSpec(
        {
            "id": change_id,
            "action_name": "edit-host",
            "text": f"Changed host {change_id}",
            "object": None,
            "user_id": UserId(user_id),
            "domains": ["check_mk"],
            "time": change_time,
            "force_sync": True,
            "force_restart": not has_been_activated,
            "force_apache_reload": False,
            "domain_settings": {},
            "prevent_discard_changes": False,
            "diff_text": None,
        }
    )


class _ActivateUntil:
    """Stands in for the activation whose id the changes are looked up by."""

    def __init__(self, change_id: str) -> None:
        self._change_id = change_id

    def activate_until(self) -> str:
        return self._change_id


@pytest.mark.usefixtures("with_admin_login")
def test_change_older_than_the_marker_is_removed_by_its_activation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A change stored behind a newer one is still activated, so it must be removed.

    The remote-site sync appends a remote's changes to the central's log, and those were
    recorded earlier than what is already queued for that site -- so the log is not in
    time order. An activation runs up to the newest change by time and has to drop
    everything it covered, wherever in the log those entries happen to sit.
    """
    site_id = SiteId("mysite")
    site_changes = SiteChanges(site_id)
    site_changes.append(_make_change_spec("newer", change_time=200.0))
    site_changes.append(_make_change_spec("older", change_time=100.0))
    try:
        monkeypatch.setattr(
            activate_changes_module,
            "load_activate_change_manager_with_id",
            lambda _activation_id: _ActivateUntil("newer"),
        )
        changes = ActivateChanges()
        changes.load([site_id], SiteConfigurations({site_id: _make_local_site_config(site_id)}))
        changes.load_changes_until("activation-id", [site_id])

        _confirm_activated_changes(site_id, changes.get_changes_to_activate(site_id))

        assert site_changes.read() == []
    finally:
        site_changes.clear()


class _NoLicenseEffect:
    header = None
    block = None


class TestGetAllDataRequiredForActivationPopout:
    SITE_ID = SiteId("popout_test_site")

    @pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
    def _patch_externals(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Suppress license checks and livestatus calls by default.

        Also re-patch the module-level path constants that were computed at import
        time (before the conftest had a chance to redirect cmk.utils.paths), so
        that state files land in the test-scoped temp directory even when running
        with pytest directly.
        """
        monkeypatch.setattr(
            activate_changes,
            "ACTIVATION_PERISTED_DIR",
            str(cmk.utils.paths.var_dir / "wato/activation"),
        )
        monkeypatch.setattr(
            activate_changes,
            "ACTIVATION_TMP_BASE_DIR",
            str(cmk.utils.paths.tmp_dir / "wato/activation"),
        )
        monkeypatch.setattr(
            activate_changes,
            "get_licensing_user_effect",
            lambda *args, **kwargs: _NoLicenseEffect(),  # noqa: ARG005
        )
        monkeypatch.setattr(activate_changes, "_get_license_block_effect", lambda: None)
        monkeypatch.setattr(
            activate_changes,
            "get_status_for_site",
            lambda site_id, site: (  # noqa: ARG005
                SiteStatus({"state": "disabled"})
                if site.get("disabled")
                else SiteStatus({"state": "online"})
            ),
        )

    @pytest.mark.usefixtures("with_admin_login")
    def test_no_pending_changes_returns_empty_summary(self) -> None:
        sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})

        result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

        assert result.pendingChanges == []
        assert len(result.sites) == 1
        assert result.sites[0].siteId == self.SITE_ID
        assert result.sites[0].changes == 0
        assert result.sites[0].lastActivationStatus is None

    def test_pending_change_appears_in_summary(self, with_admin_login: UserId) -> None:
        change = _make_change_spec("change-001", user_id=str(with_admin_login))
        site_changes = SiteChanges(self.SITE_ID)
        site_changes.append(change)
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

            assert len(result.pendingChanges) == 1
            pending = result.pendingChanges[0]
            assert pending.changeId == "change-001"
            assert pending.changeText == "Changed host change-001"
            assert pending.user == str(with_admin_login)
            assert pending.time == 1720800176.0
            assert pending.foreignChange is False
        finally:
            site_changes.clear()

    @pytest.mark.usefixtures("with_admin_login")
    def test_activated_change_excluded_from_pending(self) -> None:
        site_changes = SiteChanges(self.SITE_ID)
        site_changes.append(_make_change_spec("change-activated", has_been_activated=True))
        site_changes.append(_make_change_spec("change-pending"))
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

            assert len(result.pendingChanges) == 1
            assert result.pendingChanges[0].changeId == "change-pending"
        finally:
            site_changes.clear()

    @pytest.mark.usefixtures("with_admin_login")
    def test_site_change_counter_counts_only_pending(self) -> None:
        site_changes = SiteChanges(self.SITE_ID)
        site_changes.append(_make_change_spec("c-1"))
        site_changes.append(_make_change_spec("c-2"))
        site_changes.append(_make_change_spec("c-activated", has_been_activated=True))
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

            assert result.sites[0].changes == 2
        finally:
            site_changes.clear()

    def test_foreign_change_flag(self, with_admin_login: UserId) -> None:
        site_changes = SiteChanges(self.SITE_ID)
        site_changes.append(_make_change_spec("c-foreign", user_id="other_user"))
        site_changes.append(_make_change_spec("c-own", user_id=str(with_admin_login)))
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

            by_id = {c.changeId: c for c in result.pendingChanges}
            assert by_id["c-foreign"].foreignChange is True
            assert by_id["c-own"].foreignChange is False
        finally:
            site_changes.clear()

    @pytest.mark.usefixtures("with_admin_login")
    def test_which_sites_all_sites_when_single_site(self) -> None:
        site_changes = SiteChanges(self.SITE_ID)
        site_changes.append(_make_change_spec("c-1"))
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

            assert result.pendingChanges[0].whichSites == ["All sites"]
        finally:
            site_changes.clear()

    @pytest.mark.usefixtures("with_admin_login")
    def test_which_sites_specific_when_only_one_of_two_sites_affected(self) -> None:
        site_a = SiteId("popout_site_a")
        site_b = SiteId("popout_site_b")
        site_changes_a = SiteChanges(site_a)
        site_changes_a.append(_make_change_spec("c-1"))
        try:
            sites = SiteConfigurations(
                {
                    site_a: _make_local_site_config(site_a),
                    site_b: _make_local_site_config(site_b),
                }
            )
            result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

            assert result.pendingChanges[0].whichSites == [site_a]
        finally:
            site_changes_a.clear()

    @pytest.mark.usefixtures("with_admin_login")
    def test_last_activation_status_is_none_without_persisted_state(self) -> None:
        sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
        result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

        assert result.sites[0].lastActivationStatus is None

    @pytest.mark.usefixtures("with_admin_login")
    def test_last_activation_status_from_persisted_state(self) -> None:
        persisted_path = Path(ActivateChangesManager.persisted_site_state_path(self.SITE_ID))
        persisted_path.parent.mkdir(parents=True, exist_ok=True)
        ccc_store.save_object_to_file(
            persisted_path,
            {
                "_phase": "done",
                "_state": "success",
                "_status_text": "Success",
                "_status_details": "Finished at 12:00:00.",
                "_time_started": 1720800192.0,
                "_time_ended": 1720800197.0,
            },
        )
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

            last = result.sites[0].lastActivationStatus
            assert last is not None
            assert last.phase == "done"
            assert last.state == "success"
            assert last.status_text == "Success"
            assert last.status_details == "Finished at 12:00:00."
            assert last.start_time == 1720800192.0
            assert last.end_time == 1720800197.0
        finally:
            persisted_path.unlink(missing_ok=True)

    @pytest.mark.usefixtures("with_admin_login")
    def test_last_activation_status_with_activation_id_reads_live_state(self) -> None:
        activation_id = "abcdef12-1234-1234-1234-abcdef123456"
        live_path = Path(ActivateChangesManager.site_state_path(activation_id, self.SITE_ID))
        live_path.parent.mkdir(parents=True, exist_ok=True)
        ccc_store.save_object_to_file(
            live_path,
            {
                "_phase": "sync",
                "_state": "success",
                "_status_text": "Synchronizing",
                "_status_details": None,
                "_time_started": 1720800200.0,
                "_time_ended": 0.0,
            },
        )
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            result = ActivateChanges().get_all_data_required_for_activation_popout(
                sites, activation_id
            )

            last = result.sites[0].lastActivationStatus
            assert last is not None
            assert last.phase == "sync"
            assert last.status_text == "Synchronizing"
        finally:
            live_path.unlink(missing_ok=True)

    @pytest.mark.usefixtures("with_admin_login")
    def test_last_activation_status_falls_back_to_persisted_when_live_absent(self) -> None:
        activation_id = "fallback12-1234-1234-1234-abcdef123456"
        persisted_path = Path(ActivateChangesManager.persisted_site_state_path(self.SITE_ID))
        persisted_path.parent.mkdir(parents=True, exist_ok=True)
        ccc_store.save_object_to_file(
            persisted_path,
            {
                "_phase": "done",
                "_state": "success",
                "_status_text": "Success",
                "_status_details": "",
                "_time_started": 1720800192.0,
                "_time_ended": 1720800197.0,
            },
        )
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            # Live file does NOT exist for this activation_id; must fall back to persisted state.
            result = ActivateChanges().get_all_data_required_for_activation_popout(
                sites, activation_id
            )

            last = result.sites[0].lastActivationStatus
            assert last is not None
            assert last.phase == "done"
            assert last.state == "success"
        finally:
            persisted_path.unlink(missing_ok=True)

    @pytest.mark.usefixtures("with_admin_login")
    def test_html_stripped_from_status_details(self) -> None:
        persisted_path = Path(ActivateChangesManager.persisted_site_state_path(self.SITE_ID))
        persisted_path.parent.mkdir(parents=True, exist_ok=True)
        ccc_store.save_object_to_file(
            persisted_path,
            {
                "_phase": "done",
                "_state": "error",
                "_status_text": "Failed",
                "_status_details": "Error: <b>host not found</b> &amp; more",
                "_time_started": 1720800192.0,
                "_time_ended": 1720800197.0,
            },
        )
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

            last = result.sites[0].lastActivationStatus
            assert last is not None
            assert "<b>" not in last.status_details
            assert "host not found" in last.status_details
            assert "& more" in last.status_details
        finally:
            persisted_path.unlink(missing_ok=True)

    @pytest.mark.usefixtures("with_admin_login")
    def test_site_version_strips_build_suffix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            activate_changes,
            "get_status_for_site",
            lambda site_id, site: SiteStatus({"livestatus_version": "2.4.0p1-20250101"}),  # noqa: ARG005
        )
        sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
        result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

        assert result.sites[0].version == "2.4.0p1"

    @pytest.mark.usefixtures("with_admin_login")
    def test_disabled_site_returns_empty_version(self) -> None:
        sites = SiteConfigurations(
            {self.SITE_ID: _make_local_site_config(self.SITE_ID, disabled=True)}
        )
        result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

        assert result.sites[0].version == ""

    @pytest.mark.usefixtures("with_admin_login")
    def test_license_message_included_in_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _FakeHeader:
            message_html = "Your license is expiring soon."

        class _FakeLicenseEffect:
            header = _FakeHeader()

        monkeypatch.setattr(
            activate_changes,
            "get_licensing_user_effect",
            lambda *args, **kwargs: _FakeLicenseEffect(),  # noqa: ARG005
        )
        monkeypatch.setattr(activate_changes, "_get_license_block_effect", lambda: None)

        sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
        result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

        assert result.licenseMessage == "Your license is expiring soon."
        assert result.licenseIsBlocking is False

    @pytest.mark.usefixtures("with_admin_login")
    def test_license_is_blocking_when_block_effect_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _FakeBlock:
            pass

        monkeypatch.setattr(activate_changes, "_get_license_block_effect", _FakeBlock)

        sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
        result = ActivateChanges().get_all_data_required_for_activation_popout(sites, None)

        assert result.licenseIsBlocking is True


class TestSiteHasForeignChanges:
    SITE_ID = SiteId("foreign_changes_test_site")

    @pytest.mark.usefixtures("with_admin_login")
    def test_activated_foreign_change_does_not_count_as_foreign(self) -> None:
        site_changes = SiteChanges(self.SITE_ID)
        site_changes.append(
            _make_change_spec(
                "activated-by-other",
                user_id="other_user",
                has_been_activated=True,
            )
        )
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            changes = ActivateChanges()
            changes.load([self.SITE_ID], sites)

            assert changes.site_has_foreign_changes(self.SITE_ID) is False
            by_id = {c["id"]: c for c in changes.changes_of_site(self.SITE_ID)}
            assert by_id["activated-by-other"]["has_been_activated"] is True
        finally:
            site_changes.clear()

    @pytest.mark.usefixtures("with_admin_login")
    def test_pending_foreign_change_still_counts_as_foreign(self) -> None:
        site_changes = SiteChanges(self.SITE_ID)
        site_changes.append(_make_change_spec("pending-by-other", user_id="other_user"))
        try:
            sites = SiteConfigurations({self.SITE_ID: _make_local_site_config(self.SITE_ID)})
            changes = ActivateChanges()
            changes.load([self.SITE_ID], sites)

            assert changes.site_has_foreign_changes(self.SITE_ID) is True
        finally:
            site_changes.clear()


def test_domains_restarting_the_site_are_activated_last() -> None:
    requests = [
        DomainRequest(EXPERIMENTAL_FLAGS),
        DomainRequest(OMD),
        DomainRequest(SITE_CERTIFICATE),
    ]

    assert [request.name for request in sort_for_activation(requests)] == [
        SITE_CERTIFICATE,
        OMD,
        EXPERIMENTAL_FLAGS,
    ]


_REMOTE_SITE_ID = SiteId("remote")
_REMOTE_AUTOMATION_CONFIG = RemoteAutomationConfig(
    site_id=_REMOTE_SITE_ID,
    base_url="http://remote/remote/check_mk/",
    secret="secret",
    insecure=False,
)


def _activation_status(
    state: str,
    *,
    is_active: bool,
    exception: Sequence[str] = (),
    traceback: str = "",
    crash_id: str = "",
    warnings: ConfigWarnings | None = None,
) -> RemoteActivationStatus:
    return RemoteActivationStatus(
        state=state,
        is_active=is_active,
        exception=list(exception),
        traceback=traceback,
        crash_id=crash_id,
        warnings=warnings or {},
    )


class _FakeRemoteSite:
    """Answers the automation calls of the central site with the given status sequence

    The last status is repeated once the sequence is exhausted. An exception in the sequence is
    raised instead of being answered."""

    def __init__(self, statuses: Sequence[RemoteActivationStatus | Exception]) -> None:
        self._statuses = list(statuses)
        self.started_domains: list[object] = []

    def do_remote_automation(
        self,
        automation_config: RemoteAutomationConfig,  # noqa: ARG002
        command: str,
        vars_: Sequence[tuple[str, str]],
        debug: bool = False,  # noqa: ARG002
    ) -> object:
        if command == "activate-changes-start":
            self.started_domains.append(dict(vars_)["domains"])
            return "activate-changes-remote-6ff3d0a9-4a9e-4f4b-a65d-2df7b3dbcc52"
        assert command == "activate-changes-get-status"
        status = self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]
        if isinstance(status, Exception):
            raise status
        return status


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture(name="clock")
def fixture_clock(monkeypatch: pytest.MonkeyPatch) -> _FakeClock:
    clock = _FakeClock()
    monkeypatch.setattr(time, "monotonic", clock.monotonic)
    monkeypatch.setattr(time, "sleep", clock.sleep)
    return clock


def _install_remote_site(
    monkeypatch: pytest.MonkeyPatch, statuses: Sequence[RemoteActivationStatus | Exception]
) -> _FakeRemoteSite:
    remote_site = _FakeRemoteSite(statuses)
    # Legacy compromise: the HTTP transport to the remote site is not injectable.
    monkeypatch.setattr(
        cmk.gui.watolib.automations, "do_remote_automation", remote_site.do_remote_automation
    )
    return remote_site


@pytest.mark.usefixtures("clock")
def test_remote_activation_returns_warnings_once_the_job_finished(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_remote_site(
        monkeypatch,
        [
            _activation_status(JobStatusStates.RUNNING, is_active=True),
            _activation_status(
                JobStatusStates.FINISHED, is_active=False, warnings={"check_mk": ["warning"]}
            ),
        ],
    )

    warnings = activate_remote_site(
        _REMOTE_AUTOMATION_CONFIG, _REMOTE_SITE_ID, [DomainRequest(OMD)], debug=False
    )

    assert warnings == {"check_mk": ["warning"]}


@pytest.mark.usefixtures("clock")
def test_remote_activation_waits_while_the_remote_site_restarts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_remote_site(
        monkeypatch,
        [
            MKRemoteSiteUnavailable("HTTP Error - 502: Proxy Error"),
            _activation_status(
                JobStatusStates.FINISHED, is_active=False, warnings={"omd": ["restarted"]}
            ),
        ],
    )

    warnings = activate_remote_site(
        _REMOTE_AUTOMATION_CONFIG, _REMOTE_SITE_ID, [DomainRequest(OMD)], debug=False
    )

    assert warnings == {"omd": ["restarted"]}


@pytest.mark.usefixtures("clock")
def test_remote_activation_failure_reports_the_job_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_remote_site(
        monkeypatch,
        [
            _activation_status(
                JobStatusStates.EXCEPTION, is_active=False, exception=["core config broken"]
            )
        ],
    )

    with pytest.raises(MKGeneralException) as excinfo:
        activate_remote_site(
            _REMOTE_AUTOMATION_CONFIG, _REMOTE_SITE_ID, [DomainRequest(OMD)], debug=False
        )

    assert str(excinfo.value) == f"Activation on site {_REMOTE_SITE_ID} failed: core config broken"


@pytest.mark.usefixtures("clock")
def test_remote_activation_failure_reports_the_traceback_of_the_remote_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_remote_site(
        monkeypatch,
        [
            _activation_status(
                JobStatusStates.EXCEPTION,
                is_active=False,
                exception=["core config broken"],
                traceback="Traceback (most recent call last):\n...",
            )
        ],
    )

    with pytest.raises(MKGeneralException) as excinfo:
        activate_remote_site(
            _REMOTE_AUTOMATION_CONFIG, _REMOTE_SITE_ID, [DomainRequest(OMD)], debug=False
        )

    assert (
        str(excinfo.value) == f"Activation on site {_REMOTE_SITE_ID} failed: core config broken"
        "<pre>Traceback (most recent call last):\n...</pre>"
    )


@pytest.mark.usefixtures("clock")
def test_remote_activation_crash_refers_to_the_crash_report_of_the_remote_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_remote_site(
        monkeypatch,
        [
            _activation_status(
                JobStatusStates.EXCEPTION,
                is_active=False,
                exception=["Exception (crash ID: 894e40f4-c7dd-11f1-b42f-80e4baae41ab): bug"],
                crash_id="894e40f4-c7dd-11f1-b42f-80e4baae41ab",
            )
        ],
    )

    with pytest.raises(RemoteActivationCrash) as excinfo:
        activate_remote_site(
            _REMOTE_AUTOMATION_CONFIG, _REMOTE_SITE_ID, [DomainRequest(OMD)], debug=False
        )

    assert (excinfo.value.site_id, excinfo.value.crash_id) == (
        _REMOTE_SITE_ID,
        "894e40f4-c7dd-11f1-b42f-80e4baae41ab",
    )


def test_remote_activation_fails_when_the_job_is_no_longer_running(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    _install_remote_site(
        monkeypatch, [_activation_status(JobStatusStates.RUNNING, is_active=False)]
    )

    with pytest.raises(MKGeneralException, match="no longer running"):
        activate_remote_site(
            _REMOTE_AUTOMATION_CONFIG, _REMOTE_SITE_ID, [DomainRequest(OMD)], debug=False
        )

    assert 30 < clock.now < 32


def test_remote_activation_fails_when_the_job_does_not_finish_in_time(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    _install_remote_site(monkeypatch, [_activation_status(JobStatusStates.RUNNING, is_active=True)])

    with pytest.raises(MKGeneralException, match="did not finish within 30 minutes"):
        activate_remote_site(
            _REMOTE_AUTOMATION_CONFIG, _REMOTE_SITE_ID, [DomainRequest(OMD)], debug=False
        )

    assert 1800 < clock.now < 1802


def test_remote_activation_fails_when_the_remote_site_stays_unreachable(
    monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    _install_remote_site(monkeypatch, [MKRemoteSiteUnavailable("Site is not running")])

    with pytest.raises(MKRemoteSiteUnavailable):
        activate_remote_site(
            _REMOTE_AUTOMATION_CONFIG, _REMOTE_SITE_ID, [DomainRequest(OMD)], debug=False
        )

    assert 300 < clock.now < 302


def test_remote_activation_fails_on_other_errors_of_the_remote_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_remote_site(
        monkeypatch, [MKUserError("_passwd", "Authentication failed. Invalid login/password.")]
    )

    with pytest.raises(MKUserError, match="Authentication failed"):
        activate_remote_site(
            _REMOTE_AUTOMATION_CONFIG, _REMOTE_SITE_ID, [DomainRequest(OMD)], debug=False
        )


# fmt: off
@pytest.mark.parametrize(
    "job_id",
    [
        pytest.param("../../../etc/passwd", id="path traversal"),
        pytest.param("activate-changes-remote-../../../etc", id="path traversal after prefix"),
        pytest.param("automation-6ff3d0a9-4a9e-4f4b-a65d-2df7b3dbcc52", id="job of other type"),
    ],
)
# fmt: on
def test_remote_activation_job_rejects_foreign_job_ids(job_id: str) -> None:
    with pytest.raises(MKUserError):
        RemoteActivationBackgroundJob.from_job_id(job_id)


class _FailingDomain(ABCConfigDomain):
    def __init__(self, error: Exception) -> None:
        self._error = error

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return ConfigDomainName("failing")

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        raise self._error

    @override
    def activate(
        self, settings: SerializedSettings | None = None, *, ctx: ActivationContext
    ) -> ConfigurationWarnings:
        return []

    @override
    def config_dir(self) -> Path:
        return Path("/nonexistent")

    @override
    def default_globals(self) -> GlobalSettings:
        return {}


def _run_remote_activation_job_failing_with(error: Exception) -> RemoteActivationStatus:
    config_domain_registry.register(_FailingDomain(error))
    try:
        job = RemoteActivationBackgroundJob.start_activation(
            make_folder_tree(Config()),
            [DomainRequest(_FailingDomain.ident())],
            UserPermissionSerializableConfig(
                roles={}, user_roles={}, default_user_profile_roles=[]
            ),
        )
        job.wait_for_completion(30)
    finally:
        config_domain_registry.unregister(_FailingDomain.ident())
    return job.activation_status()


@pytest.mark.usefixtures("patch_omd_site", "allow_background_jobs")
@pytest.mark.parametrize(
    "error",
    [
        pytest.param(MKGeneralException("core config broken"), id="MKGeneralException"),
        pytest.param(MKUserError(None, "core config broken"), id="MKUserError"),
    ],
)
def test_remote_activation_job_reports_user_errors_without_crash_report(error: Exception) -> None:
    status = _run_remote_activation_job_failing_with(error)

    assert status["state"] == JobStatusStates.EXCEPTION
    assert status["exception"] == ["core config broken"]
    assert status["crash_id"] == ""
    assert status["traceback"].startswith("Traceback (most recent call last):")
    assert "core config broken" in status["traceback"]


@pytest.mark.usefixtures("patch_omd_site", "allow_background_jobs")
def test_remote_activation_job_reports_other_errors_with_crash_report() -> None:
    status = _run_remote_activation_job_failing_with(KeyError("bug"))

    assert status["state"] == JobStatusStates.EXCEPTION
    crash_info = pop_crash_report_file("gui", "crash.info")
    assert crash_info is not None
    assert status["crash_id"] == json.loads(crash_info)["id"]
    assert status["crash_id"] in "\n".join(status["exception"])
    assert status["traceback"] == ""


def _fail_to_connect_to_broker(*_args: object) -> None:
    raise CMKConnectionError("certificate verify failed: self-signed certificate")


@pytest.mark.xfail(raises=CMKConnectionError, reason="Crash group 4014: CMKConnectionError")
@pytest.mark.usefixtures("request_context")
def test_failing_broker_connection_during_hub_config_distribution_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    features = replace(
        next(iter(activate_changes.activation_features_registry.values())),
        distribute_piggyback_hub_configs=_fail_to_connect_to_broker,
    )

    with caplog.at_level(logging.WARNING, logger="cmk.web"):
        _distribute_piggyback_hub_configs(
            features, SiteConfigurations({}), [], make_folder_tree(Config())
        )

    assert any("message broker" in m for m in caplog.messages)
