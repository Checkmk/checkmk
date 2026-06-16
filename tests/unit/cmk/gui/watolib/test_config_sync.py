#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import re
import time
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest
import responses
from pytest_mock import MockerFixture

import cmk.ccc.version as cmk_version
import cmk.gui.mkeventd.wato
from cmk import trace
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui.config import active_config
from cmk.gui.watolib import activate_changes, config_sync
from cmk.gui.watolib.automations import (
    remote_automation_config_from_site_config,
)
from cmk.utils.automation_config import RemoteAutomationConfig
from tests.testlib.unit.gui.config_sync_test_helper import (
    create_sync_snapshot,
    get_activation_manager,
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


def _get_expected_paths(user_id: UserId) -> list[str]:
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
        "etc/check_mk/product_usage_analytics.mk",
        "etc/check_mk/release_flag.json",
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

    expected_paths += [
        "etc/omd/site.conf",
        "etc/check_mk/mkeventd.d/mkp",
        "etc/check_mk/mkeventd.d/mkp/rule_packs",
        "etc/check_mk/mkeventd.d/wato/rules.mk",
        "local",
        "var/check_mk/packages",
        "var/check_mk/packages_local",
        "var/check_mk/disabled_packages",
        "var/check_mk/topology",
        "var/check_mk/topology/configs",
    ]

    return expected_paths


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize("remote_site", [SiteId("unit_remote_1"), SiteId("unit_remote_2")])
def test_generate_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    with_user_login: UserId,
    remote_site: SiteId,
    test_edition: Edition,
) -> None:
    with get_activation_manager(monkeypatch, remote_site) as activation_manager:
        with create_sync_snapshot(
            activation_manager,
            monkeypatch,
            tmp_path,
            remote_site=remote_site,
            edition=test_edition,
        ) as snapshot_settings:
            expected_paths = _get_expected_paths(user_id=with_user_login)

            work_dir = Path(snapshot_settings.work_dir)
            snapshot_paths = [str(p.relative_to(work_dir)) for p in work_dir.glob("**/*")]
            assert sorted(snapshot_paths) == sorted(expected_paths)


# This test does not perform the full synchronization. It executes the central site parts and mocks
# the remote site HTTP calls
@pytest.mark.usefixtures("request_context")
def test_synchronize_site(
    mocked_responses: responses.RequestsMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: MockerFixture,
    test_edition: Edition,
) -> None:
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

    monkeypatch.setattr(cmk_version, "edition", lambda *args, **kw: test_edition)

    file_filter_func = None
    site_id = SiteId("unit_remote_1")
    with get_activation_manager(monkeypatch, SiteId("unit_remote_1")) as activation_manager:
        assert activation_manager._activation_id is not None
        with create_sync_snapshot(
            activation_manager,
            monkeypatch,
            tmp_path,
            remote_site=SiteId("unit_remote_1"),
            edition=test_edition,
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


class _FakeConfig:
    def __init__(self, sites: dict) -> None:
        self.sites = sites


def _patch_central(monkeypatch: pytest.MonkeyPatch, authentication_connections: object) -> None:
    monkeypatch.setattr(config_sync, "omd_site", lambda: SiteId("central"))
    monkeypatch.setattr(
        config_sync,
        "active_config",
        _FakeConfig(
            {SiteId("central"): {"authentication_connections": authentication_connections}}
        ),
    )


def test_central_site_inherited_connections_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_central(monkeypatch, [])
    assert config_sync.central_site_inherited_connections("https://cb") == []


def test_central_site_inherited_connections_saml_populates_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_central(monkeypatch, [("saml", {"connection_id": "testsaml"})])
    monkeypatch.setattr(
        config_sync,
        "_saml_endpoint_urls",
        lambda callback_url, connection_id: (
            f"https://meta/{connection_id}",
            f"https://acs/{connection_id}",
        ),
    )
    assert config_sync.central_site_inherited_connections("https://cb") == [
        (
            "saml",
            {
                "connection_id": "testsaml",
                "metadata_endpoint": "https://meta/testsaml",
                "acs_endpoint": "https://acs/testsaml",
            },
        )
    ]
