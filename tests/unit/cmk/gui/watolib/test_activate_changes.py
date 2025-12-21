#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"


import io
import logging
import os
import tarfile
from collections.abc import Mapping
from pathlib import Path

import pytest
from werkzeug.test import create_environ

from livestatus import SiteConfiguration, SiteConfigurations

import cmk.ccc.version as cmk_version
import cmk.gui.watolib.utils
import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.userdb import get_user_attributes
from cmk.gui.watolib import activate_changes
from cmk.gui.watolib.activate_changes import (
    ActivationCleanupJob,
    ConfigSyncFileInfo,
    default_rabbitmq_definitions,
)
from cmk.gui.watolib.config_sync import (
    replication_path_registry,
    ReplicationPath,
    ReplicationPathType,
)
from cmk.livestatus_client import (
    BrokerConnection,
    BrokerConnections,
    BrokerSite,
    ConnectionId,
    NetworkSocketDetails,
)
from cmk.messaging import rabbitmq
from tests.testlib.common.repo import is_pro_repo, is_ultimatemt_repo
from tests.testlib.unit.rabbitmq import get_expected_definition
from tests.testlib.unit.utils import reset_registries

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def restore_orig_replication_paths():
    with reset_registries([replication_path_registry]):
        yield


def _expected_replication_paths(edition: cmk_version.Edition) -> list[ReplicationPath]:
    expected = [
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="check_mk",
            site_path="etc/check_mk/conf.d/wato",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="multisite",
            site_path="etc/check_mk/multisite.d/wato",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="htpasswd",
            site_path="etc/htpasswd",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="auth.secret",
            site_path="etc/auth.secret",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="password_store.secret",
            site_path="etc/password_store.secret",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="auth.serials",
            site_path="etc/auth.serials",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="stored_passwords",
            site_path="var/check_mk/stored_passwords",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="telemetry",
            site_path="etc/check_mk/telemetry.mk",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="usersettings",
            site_path="var/check_mk/web",
            excludes_exact_match=["last_login.mk", "report-thumbnails", "session_info.mk"],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkps",
            site_path="var/check_mk/packages",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkps_avail",
            site_path="var/check_mk/packages_local",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkps_disabled",
            site_path="var/check_mk/disabled_packages",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="local",
            site_path="local",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="distributed_wato",
            site_path="etc/check_mk/conf.d/distributed_wato.mk",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="omd",
            site_path="etc/omd",
            excludes_exact_match=["site.conf", "instance_id"],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="rabbitmq",
            site_path="etc/rabbitmq/definitions.d",
            excludes_exact_match=["00-default.json", "definitions.json"],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="frozen_aggregations",
            site_path="var/check_mk/frozen_aggregations",
            excludes_exact_match=[],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="topology",
            site_path="var/check_mk/topology",
            excludes_exact_match=[],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="apache_proccess_tuning",
            site_path="etc/check_mk/apache.d/wato",
            excludes_exact_match=[],
        ),
    ]

    if edition is not cmk_version.Edition.COMMUNITY:
        expected += [
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="liveproxyd",
                site_path="etc/check_mk/liveproxyd.d/wato",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="dcd",
                site_path="etc/check_mk/dcd.d/wato",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="mknotify",
                site_path="etc/check_mk/mknotifyd.d/wato",
            ),
            # CMK-20769
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="otel_collector",
                site_path="etc/check_mk/otel_collector.d/wato",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="metric_backend",
                site_path="etc/check_mk/metric_backend.d/wato",
            ),
        ]

    expected += [
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkeventd",
            site_path="etc/check_mk/mkeventd.d/wato",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkeventd_mkp",
            site_path="etc/check_mk/mkeventd.d/mkp/rule_packs",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="diskspace",
            site_path="etc/check_mk/diskspace.d/wato",
        ),
    ]

    if edition is cmk_version.Edition.ULTIMATEMT:
        expected += [
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="customer_check_mk",
                site_path="etc/check_mk/conf.d/customer.mk",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="customer_gui_design",
                site_path="etc/check_mk/multisite.d/zzz_customer_gui_design.mk",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="customer_multisite",
                site_path="etc/check_mk/multisite.d/customer.mk",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="login_logo_dark",
                site_path="local/share/check_mk/web/htdocs/themes/modern-dark/images/login_logo.png",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="login_logo_facelift",
                site_path="local/share/check_mk/web/htdocs/themes/facelift/images/login_logo.png",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="navbar_logo_dark",
                site_path="local/share/check_mk/web/htdocs/themes/modern-dark/images/navbar_logo.png",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="navbar_logo_facelift",
                site_path="local/share/check_mk/web/htdocs/themes/facelift/images/navbar_logo.png",
            ),
        ]

    # The below lines are confusing and incorrect. The reason we need them is
    # because our test environments do not reflect our Checkmk editions properly.
    # We cannot fix that in the short (or even mid) term because the
    # precondition is a more cleanly separated structure.

    if is_pro_repo() and edition is cmk_version.Edition.COMMUNITY:
        # CEE paths are added when the CEE plug-ins for WATO are available, i.e.
        # when the "enterprise/" path is present.
        expected += [
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="dcd",
                site_path="etc/check_mk/dcd.d/wato",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="mknotify",
                site_path="etc/check_mk/mknotifyd.d/wato",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="liveproxyd",
                site_path="etc/check_mk/liveproxyd.d/wato",
            ),
            # CMK-20769
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="otel_collector",
                site_path="etc/check_mk/otel_collector.d/wato",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.DIR,
                ident="metric_backend",
                site_path="etc/check_mk/metric_backend.d/wato",
            ),
        ]

    if is_ultimatemt_repo() and edition is not cmk_version.Edition.ULTIMATEMT:
        # CME paths are added when the CME plug-ins for WATO are available, i.e.
        # when the "managed/" path is present.
        expected += [
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="customer_check_mk",
                site_path="etc/check_mk/conf.d/customer.mk",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="customer_gui_design",
                site_path="etc/check_mk/multisite.d/zzz_customer_gui_design.mk",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="customer_multisite",
                site_path="etc/check_mk/multisite.d/customer.mk",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="login_logo_dark",
                site_path="local/share/check_mk/web/htdocs/themes/modern-dark/images/login_logo.png",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="login_logo_facelift",
                site_path="local/share/check_mk/web/htdocs/themes/facelift/images/login_logo.png",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="navbar_logo_dark",
                site_path="local/share/check_mk/web/htdocs/themes/modern-dark/images/navbar_logo.png",
            ),
            ReplicationPath.make(
                ty=ReplicationPathType.FILE,
                ident="navbar_logo_facelift",
                site_path="local/share/check_mk/web/htdocs/themes/facelift/images/navbar_logo.png",
            ),
        ]

    return expected


def test_get_replication_paths_defaults(
    edition: cmk_version.Edition, request_context: None
) -> None:
    expected = _expected_replication_paths(edition)
    assert sorted(
        replication_path_registry.values(),
        key=lambda replication_path: replication_path.ident,
    ) == sorted(
        expected,
        key=lambda replication_path: replication_path.ident,
    )


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
        user_sync="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


@pytest.mark.parametrize("replicate_ec", [None, True, False])
@pytest.mark.parametrize("replicate_mkps", [None, True, False])
def test_get_replication_components(
    edition: cmk_version.Edition,
    monkeypatch: pytest.MonkeyPatch,
    replicate_ec: bool | None,
    replicate_mkps: bool | None,
    request_context: None,
) -> None:
    site_config = default_site_config()

    if replicate_ec is not None:
        site_config["replicate_ec"] = replicate_ec
    if replicate_mkps is not None:
        site_config["replicate_mkps"] = replicate_mkps

    expected = _expected_replication_paths(edition)

    if not replicate_ec:
        expected = [e for e in expected if e.ident not in ["mkeventd", "mkeventd_mkp"]]

    if not replicate_mkps:
        expected = [
            e for e in expected if e.ident not in ["local", "mkps", "mkps_avail", "mkps_disabled"]
        ]

    assert sorted(
        activate_changes._get_replication_components(site_config),
        key=lambda replication_path: replication_path.ident,
    ) == sorted(
        expected,
        key=lambda replication_path: replication_path.ident,
    )


def test_automation_get_config_sync_state(request_context: None) -> None:
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
                489,
                None,
                "670166ff0481b8da011e7b3bf27750667b3b0851bcd63063cb75843643ae5ece",
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
            "etc/omd/site.conf": (
                33200,
                1010,
                None,
                "4a1a223aa376f18e6e7775157d88f554c49eec3d968a02ecb781a2b31c7a375d",
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
    sync_infos = activate_changes._get_config_sync_file_infos(replication_paths, base_dir)

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


def test_get_file_names_to_sync_without_file_sync(request_context: None) -> None:
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


def test_get_file_names_to_sync_with_file_sync(request_context: None) -> None:
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

    return activate_changes._get_sync_archive(
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
    def test_automation_receive_config_sync(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        request_context: None,
    ) -> None:
        remote_path = tmp_path / "remote"
        monkeypatch.setattr(cmk.utils.paths, "omd_root", remote_path)

        # Disable for the moment, because the unit test fake environment is not ready for this yet
        monkeypatch.setattr(
            cmk.gui.watolib.activate_changes,
            "_execute_post_config_sync_actions",
            lambda site_id, local_files_changed, use_git: None,
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
                    user_sync="all",
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
                    user_sync="all",
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
    assert activate_changes._get_current_config_generation() == 0
    activate_changes.update_config_generation()
    assert activate_changes._get_current_config_generation() == 1
    activate_changes.update_config_generation()
    activate_changes.update_config_generation()
    assert activate_changes._get_current_config_generation() == 3


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
                    user_sync="all",
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
                    user_sync="all",
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
                    user_sync="all",
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
                    user_sync="all",
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
                    user_sync="all",
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
                    user_sync="all",
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
