#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import re
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import responses
from pytest_mock import MockerFixture

from livestatus import NetworkSocketDetails, SiteConfiguration, TLSParams

import cmk.ccc.version as cmk_version
import cmk.gui.mkeventd.wato
import cmk.utils.paths
from cmk import trace
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.nodevis.utils import topology_dir
from cmk.gui.watolib import activate_changes, config_sync
from cmk.gui.watolib.automations import (
    remote_automation_config_from_site_config,
)
from cmk.messaging import rabbitmq
from cmk.utils.automation_config import RemoteAutomationConfig
from tests.testlib.common.repo import (
    is_cloud_repo,
    is_pro_repo,
    is_ultimate_repo,
    is_ultimatemt_repo,
)


@pytest.fixture(name="mocked_responses")
def fixture_mocked_responses() -> Iterable[responses.RequestsMock]:
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(autouse=True)
def fixture_fake_site_states(monkeypatch: pytest.MonkeyPatch) -> None:
    # During these tests we treat all sites a being online
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


@pytest.fixture(autouse=True)
def fixture_disable_ec_rule_stats_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    # During CME config computation the EC rule packs are loaded which currently also load the
    # rule usage information from the running EC. Since we do not have a EC running this fails
    # and causes timeouts. Disable this for these tests.
    monkeypatch.setattr(cmk.gui.mkeventd.wato, "_get_rule_stats_from_ec", lambda: {})


@pytest.fixture(autouse=True)
def fixture_disable_cmk_update_config(monkeypatch: pytest.MonkeyPatch) -> None:
    # During CME config computation the EC rule packs are loaded which currently also load the
    # rule usage information from the running EC. Since we do not have a EC running this fails
    # and causes timeouts. Disable this for these tests.
    monkeypatch.setattr(
        cmk.gui.watolib.activate_changes, "_execute_cmk_update_config", lambda: None
    )


@contextmanager
def _create_sync_snapshot(
    activation_manager: activate_changes.ActivateChangesManager,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    remote_site: SiteId,
    edition: cmk_version.Edition,
) -> Iterator[config_sync.SnapshotSettings]:
    with _create_test_sync_config(monkeypatch):
        yield _generate_sync_snapshot(
            activation_manager,
            tmp_path,
            remote_site=remote_site,
            edition=edition,
        )


@contextmanager
def _create_test_sync_config(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Create some config files to be synchronized"""
    conf_dir = cmk.utils.paths.check_mk_config_dir / "wato"
    conf_dir.mkdir(parents=True, exist_ok=True)
    with conf_dir.joinpath("hosts.mk").open("w", encoding="utf-8") as f:
        f.write("all_hosts = []\n")

    (cmk.utils.paths.omd_root / "local").mkdir(parents=True, exist_ok=True)
    (cmk.utils.paths.var_dir / "packages").mkdir(parents=True, exist_ok=True)
    topology_dir.mkdir(parents=True, exist_ok=True)

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


def _get_site_configuration(remote_site: SiteId) -> SiteConfiguration:
    # TODO: Make this better testable: Extract site snapshot setting calculation
    if remote_site == SiteId("unit_remote_1"):
        return SiteConfiguration(
            id=SiteId("unit_remote_1"),
            customer="provider",
            url_prefix="/unit_remote_1/",
            status_host=None,
            user_sync=None,
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
            user_sync=None,
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
def _get_activation_manager(
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
                    user_sync=None,
                    is_trusted=False,
                ),
                remote_site: _get_site_configuration(remote_site),
            },
        )

        activation_manager = activate_changes.ActivateChangesManager()
        activation_manager._sites = [remote_site]
        activation_manager.changes._changes_by_site = {remote_site: []}
        activation_manager._activation_id = "123"
        yield activation_manager


def _generate_sync_snapshot(
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
        "etc/check_mk/multisite.d/wato/site_certificate",
        "var/check_mk",
        "var/check_mk/web",
        "etc/htpasswd",
        "etc/auth.serials",
        "etc/check_mk/multisite.d/wato/users.mk",
        "var/check_mk/web/%s" % user_id,
        "var/check_mk/web/%s/automation_user.mk" % user_id,
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
        "etc/check_mk/diskspace.d",
        "etc/check_mk/diskspace.d/wato",
        "etc/check_mk/diskspace.d/wato/sitespecific.mk",
        "etc/check_mk/mkeventd.d/wato/sitespecific.mk",
        "etc/check_mk/multisite.d/wato/ca-certificates_sitespecific.mk",
        "etc/check_mk/multisite.d/wato/site_certificate/sitespecific.mk",
        "etc/check_mk/multisite.d/wato/sitespecific.mk",
        "etc/check_mk/rrdcached.d",
        "etc/check_mk/rrdcached.d/wato",
        "etc/check_mk/rrdcached.d/wato/sitespecific.mk",
        "etc/omd",
        "etc/omd/distributed.mk",
        "etc/omd/sitespecific.mk",
        "etc/rabbitmq",
        "etc/rabbitmq/definitions.d",
        "etc/rabbitmq/definitions.d/definitions.next.json",
    ]

    if edition is not cmk_version.Edition.COMMUNITY:
        expected_paths += [
            "etc/check_mk/dcd.d/wato/distributed.mk",
            "etc/check_mk/dcd.d",
            "etc/check_mk/dcd.d/wato",
            "etc/check_mk/dcd.d/wato/connections.mk",
            "etc/check_mk/dcd.d/wato/sitespecific.mk",
            "etc/check_mk/mknotifyd.d",
            "etc/check_mk/mknotifyd.d/wato",
            "etc/check_mk/mknotifyd.d/wato/sitespecific.mk",
        ]

    if edition is not cmk_version.Edition.ULTIMATEMT:
        expected_paths += ["etc/omd/site.conf"]

    # TODO: The second condition should not be needed. Seems to be a subtle difference between the
    # CME and CRE/CEE snapshot logic
    if edition is not cmk_version.Edition.ULTIMATEMT:
        expected_paths += [
            "etc/check_mk/mkeventd.d/mkp",
            "etc/check_mk/mkeventd.d/mkp/rule_packs",
            "etc/check_mk/mkeventd.d/wato/rules.mk",
            "local",
            "var/check_mk/packages",
            "var/check_mk/packages_local",
            "var/check_mk/disabled_packages",
            "var/check_mk/topology",
        ]

    # TODO: Shouldn't we clean up these subtle differences?
    if edition is cmk_version.Edition.ULTIMATEMT:
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
            "etc/password_store.secret",
            "etc/check_mk/apache.d/wato/global.mk",
            "etc/check_mk/conf.d/wato/global.mk",
            "etc/check_mk/diskspace.d/wato/global.mk",
            "etc/check_mk/multisite.d/wato/ca-certificates.mk",
            "etc/check_mk/multisite.d/wato/site_certificate/global.mk",
            "etc/check_mk/rrdcached.d/wato/global.mk",
            "etc/omd/global.mk",
            "etc/check_mk/dcd.d/wato/global.mk",
            "etc/check_mk/mknotifyd.d/wato/global.mk",
            "etc/check_mk/mkeventd.d/wato/global.mk",
            "etc/check_mk/otel_collector.d/wato/global.mk",
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
    if edition not in (cmk_version.Edition.COMMUNITY, cmk_version.Edition.ULTIMATEMT):
        expected_paths += [
            "etc/check_mk/liveproxyd.d",
            "etc/check_mk/liveproxyd.d/wato",
        ]

    # The below lines are confusing and incorrect. The reason we need them is
    # because our test environments do not reflect our Checkmk editions properly.
    # We cannot fix that in the short (or even mid) term because the
    # precondition is a more cleanly separated structure.

    if is_pro_repo() and edition is cmk_version.Edition.COMMUNITY:
        # CEE paths are added when the CEE plug-ins for WATO are available, i.e.
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

    if is_ultimatemt_repo() and edition is not cmk_version.Edition.ULTIMATEMT:
        # CME paths are added when the CME plug-ins for WATO are available, i.e.
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

    if (is_ultimate_repo() and edition is cmk_version.Edition.ULTIMATE) or (
        is_ultimatemt_repo() and edition is cmk_version.Edition.ULTIMATEMT
    ):
        expected_paths += [
            "etc/check_mk/otel_collector.d",
            "etc/check_mk/otel_collector.d/wato",
            "etc/check_mk/otel_collector.d/wato/otel_collector_receivers.mk",
            "etc/check_mk/otel_collector.d/wato/otel_collector_prom_scrape.mk",
            "etc/check_mk/otel_collector.d/wato/sitespecific.mk",
        ]

    if any(
        [
            (is_ultimate_repo() and edition is cmk_version.Edition.ULTIMATE),
            (is_ultimatemt_repo() and edition is cmk_version.Edition.ULTIMATEMT),
            (is_cloud_repo() and edition is cmk_version.Edition.CLOUD),
        ]
    ):
        expected_paths += [
            "etc/check_mk/metric_backend.d",
            "etc/check_mk/metric_backend.d/wato",
            "etc/check_mk/metric_backend.d/wato/global.mk",
            "etc/check_mk/metric_backend.d/wato/sitespecific.mk",
        ]

    return expected_paths


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize("remote_site", [SiteId("unit_remote_1"), SiteId("unit_remote_2")])
def test_generate_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    with_user_login: UserId,
    remote_site: SiteId,
) -> None:
    # Unfortunately we can not use the edition fixture anymore, which parameterizes the test with
    # all editions. The reason for this is that cmk.gui.main_modules now executes the registrations
    # for the edition it detects. In the future we want be able to create edition specific
    # application objects, which would make testing them independently possible. Until then we have
    # to accept the smaller test scope.
    edition = cmk_version.edition(cmk.utils.paths.omd_root)

    with _get_activation_manager(monkeypatch, remote_site) as activation_manager:
        with _create_sync_snapshot(
            activation_manager,
            monkeypatch,
            tmp_path,
            remote_site=remote_site,
            edition=edition,
        ) as snapshot_settings:
            expected_paths = _get_expected_paths(
                user_id=with_user_login,
                with_local=active_config.sites[remote_site].get("replicate_mkps", False),
                edition=edition,
            )

            work_dir = Path(snapshot_settings.work_dir)
            paths = [str(p.relative_to(work_dir)) for p in work_dir.glob("**/*")]
            assert sorted(paths) == sorted(expected_paths)


# This test does not perform the full synchronization. It executes the central site parts and mocks
# the remote site HTTP calls
@pytest.mark.usefixtures("request_context")
def test_synchronize_site(
    mocked_responses: responses.RequestsMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Unfortunately we can not use the edition fixture anymore, which parameterizes the test with
    # all editions. The reason for this is that cmk.gui.main_modules now executes the registrations
    # for the edition it detects. In the future we want be able to create edition specific
    # application objects, which would make testing them independently possible. Until then we have
    # to accept the smaller test scope.
    edition = cmk_version.edition(cmk.utils.paths.omd_root)

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

    monkeypatch.setattr(cmk_version, "edition", lambda *args, **kw: edition)

    file_filter_func = None
    site_id = SiteId("unit_remote_1")
    with _get_activation_manager(monkeypatch, SiteId("unit_remote_1")) as activation_manager:
        assert activation_manager._activation_id is not None
        with _create_sync_snapshot(
            activation_manager,
            monkeypatch,
            tmp_path,
            remote_site=SiteId("unit_remote_1"),
            edition=edition,
        ) as snapshot_settings:
            _synchronize_site(
                activation_manager,
                site_id,
                snapshot_settings,
                file_filter_func,
                remote_automation_config_from_site_config(
                    active_config.sites[SiteId("unit_remote_1")]
                ),
            )


def _synchronize_site(
    activation_manager: activate_changes.ActivateChangesManager,
    site_id: SiteId,
    snapshot_settings: config_sync.SnapshotSettings,
    file_filter_func: Callable[[str], bool] | None,
    automation_config: RemoteAutomationConfig,
) -> None:
    assert activation_manager._activation_id is not None
    site_activation_state = activate_changes._initialize_site_activation_state(
        site_id,
        snapshot_settings.site_config,
        activation_manager._activation_id,
        activation_manager.changes,
        time.time(),
        "GUI",
    )

    current_span = trace.get_current_span()
    fetch_state_result = activate_changes.fetch_sync_state(
        snapshot_settings.snapshot_components,
        site_activation_state,
        {},
        current_span,
        automation_config,
        debug=True,
    )

    assert fetch_state_result is not None
    sync_state, site_activation_state, sync_start = fetch_state_result

    calc_delta_result = activate_changes.calc_sync_delta(
        sync_state,
        bool(snapshot_settings.site_config.get("sync_files")),
        file_filter_func,
        site_activation_state,
        sync_start,
        current_span,
    )
    assert calc_delta_result is not None
    sync_delta, site_activation_state, sync_start = calc_delta_result

    sync_result = activate_changes.synchronize_files(
        sync_delta,
        sync_state.remote_config_generation,
        Path(snapshot_settings.work_dir),
        site_activation_state,
        sync_start,
        current_span,
        automation_config,
        debug=True,
    )
    assert sync_result is not None


def test_replication_path_factory_ok() -> None:
    assert config_sync.ReplicationPath.make(
        ty=config_sync.ReplicationPathType.DIR,
        ident="some_dir",
        site_path="some_path",
        excludes_exact_match=["xyz"],
        excludes_regex_match=[".*abc"],
    ) == config_sync.ReplicationPath(
        ty=config_sync.ReplicationPathType.DIR,
        ident="some_dir",
        site_path="some_path",
        excludes_exact_match=frozenset(["xyz"]),
        excludes_regex_match=frozenset([re.compile(".*abc"), re.compile(r"^\..*\.new.*")]),
    )


def test_replication_path_factory_error_absolute_path() -> None:
    with pytest.raises(Exception):
        config_sync.ReplicationPath.make(
            ty=config_sync.ReplicationPathType.FILE,
            ident="some_file",
            site_path="/abs",
        )


@pytest.mark.parametrize(
    ("entry", "expected_result"),
    [
        ("xyz", True),
        ("123abc", True),
        (".filename.newabc123", True),
        ("something.mk", False),
        ("my-new-file", False),
    ],
)
def test_replication_path_is_excluded(entry: str, expected_result: bool) -> None:
    assert (
        config_sync.ReplicationPath.make(
            ty=config_sync.ReplicationPathType.DIR,
            ident="some_dir",
            site_path="some_path",
            excludes_exact_match=["xyz"],
            excludes_regex_match=[".*abc"],
        ).is_excluded(entry)
        is expected_result
    )


def test_replication_path_serialize_deserialize_round_trip() -> None:
    replication_path = config_sync.ReplicationPath.make(
        ty=config_sync.ReplicationPathType.FILE,
        ident="some-file",
        site_path="a/b/c.mk",
        excludes_exact_match=["xyz"],
        excludes_regex_match=[".*abc"],
    )
    assert config_sync.ReplicationPath.deserialize(replication_path.serialize()) == replication_path


def test_replication_path_deserialize_legacy_format() -> None:
    assert config_sync.ReplicationPath.deserialize(
        ("dir", "ident", "x/y/z", ["1", "2"])
    ) == config_sync.ReplicationPath.make(
        ty=config_sync.ReplicationPathType.DIR,
        ident="ident",
        site_path="x/y/z",
        excludes_exact_match=["1", "2"],
    )


def test_replication_path_serialize_deserialize_error() -> None:
    with pytest.raises(TypeError):
        config_sync.ReplicationPath.deserialize(("file", "ident", "some_path/x.mk"))
