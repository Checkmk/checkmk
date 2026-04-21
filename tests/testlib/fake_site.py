#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Suite-neutral helpers for setting up a fake Checkmk site in unit-test contexts."""

import json
import logging
import logging.handlers
import os
import pprint
import queue
import shutil
import tempfile
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Final
from unittest.mock import patch

import pytest
from fakeredis import FakeRedis

import livestatus

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
import cmk.crypto.password_hashing
import cmk.utils.caching
import cmk.utils.paths
from cmk.ccc.crash_reporting import make_crash_report_base_path
from cmk.ccc.site import omd_site, SiteId
from cmk.utils import redis
from tests.testlib.common.repo import is_non_free_repo, repo_path

logger = logging.getLogger(__name__)


def _dump(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(data)


def makedirs(path: Path) -> None:
    path.mkdir(mode=0o770, parents=True, exist_ok=True)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _report_crashes() -> None:
    for crash_file in make_crash_report_base_path(cmk.utils.paths.omd_root).glob("**/crash.info"):
        crash = json.loads(crash_file.read_text())
        pytest.fail(
            f"Crash report detected! {crash.get('exc_type', '')}: {crash.get('exc_value', '')}\n"
            "If this is an intended crash (for rest api tests), use `assert_rest_api_crash` to "
            f"remove the file as part of the test.\n{pprint.pformat(crash)}"
        )


def fake_paths() -> None:
    """Patch `cmk.utils.paths.*` into a temp directory so the tests run isolated"""
    from pytest import MonkeyPatch

    monkeypatch = MonkeyPatch()
    tmp_dir = tempfile.mkdtemp(prefix="pytest_cmk_")

    unpatched_paths: Final = {
        # FIXME :-(
        # dropping these makes tests/unit/cmk/gui/watolib/test_config_sync.py fail.
        "local_dashboards_dir",
        "local_views_dir",
        "local_reports_dir",
        # cse_config_dir is patched explicitly below (starts with /etc, not under omd_root)
        "cse_config_dir",
        # these start with /opt and will not be changed in the code below
        "rrd_multiple_dir",
        "rrd_single_dir",
        "mkbackup_lock_dir",
    }

    # patch `cmk.utils.paths` before `cmk.ccc.versions`
    logger.info("Patching `cmk.utils.paths`.")
    import cmk.utils.paths

    # Unit test context: load all available modules
    original_omd_root = Path(cmk.utils.paths.omd_root)
    for name, value in vars(cmk.utils.paths).items():
        if name.startswith("_") or not isinstance(value, str | Path) or name in unpatched_paths:
            continue

        assert Path(value).is_relative_to(original_omd_root)
        try:
            monkeypatch.setattr(
                f"cmk.utils.paths.{name}",
                type(value)(tmp_dir / Path(value).relative_to(original_omd_root)),
            )
        except ValueError:
            pass  # path is outside of omd_root

    # these use repo_path
    monkeypatch.setattr("cmk.utils.paths.agents_dir", repo_path() / "agents")
    monkeypatch.setattr("cmk.utils.paths.checks_dir", repo_path() / "checks")

    # Merge notification scripts from community and non-free packages into a
    # combined directory (in production, all scripts are installed to share/check_mk/notifications/).
    # Use a separate temp dir so it doesn't get cleaned up by the session cleanup fixture.
    notifications_tmp = Path(tempfile.mkdtemp(prefix="pytest_cmk_notif_"))
    for f in (repo_path() / "packages/cmk-notification-plugins/notifications").iterdir():
        if f.is_file():
            (notifications_tmp / f.stem).symlink_to(f)
    nonfree_notif = repo_path() / "non-free/packages/cmk-notification-plugins-nonfree/notifications"
    if nonfree_notif.is_dir():
        for f in nonfree_notif.iterdir():
            if f.is_file() and not (notifications_tmp / f.stem).exists():
                (notifications_tmp / f.stem).symlink_to(f)
    monkeypatch.setattr("cmk.utils.paths.notifications_dir", notifications_tmp)

    # Patch cse_config_dir (starts with /etc, not under omd_root) so cloud edition
    # registration can load its config in the test environment.
    cse_tmp = Path(tmp_dir) / "etc" / "cse"
    cse_tmp.mkdir(parents=True, exist_ok=True)
    (cse_tmp / "edition_config.json").write_text(
        json.dumps(
            {
                "uap_url": "https://test.example.com",
                "bug_tracker_url": "https://test.example.com",
                "download_agent_user": "test",
                "tenant_id": "test-tenant",
                "otel_collector_receiver_activation_script_path": "/dev/null",
                "enable_ai": False,
            }
        )
    )
    monkeypatch.setattr("cmk.utils.paths.cse_config_dir", cse_tmp)

    monkeypatch.setattr("cmk.utils.paths.inventory_dir", repo_path() / "inventory")
    monkeypatch.setattr("cmk.utils.paths.legacy_check_manpages_dir", repo_path() / "checkman")


def edition() -> cmk_version.Edition:
    if edition_ := os.environ.get("EDITION"):
        return cmk_version.Edition.from_long_edition(edition_)

    return cmk_version.Edition.from_long_edition(
        "ultimatemt" if is_non_free_repo() else "community"
    )


def setup_fake_omd_site(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("OMD_ROOT", str(cmk.utils.paths.omd_root))
    omd_site.cache_clear()

    _touch(cmk.utils.paths.htpasswd_file)
    makedirs(cmk.utils.paths.autochecks_dir)
    makedirs(cmk.utils.paths.var_dir / "web")
    makedirs(cmk.utils.paths.var_dir / "php-api")
    makedirs(cmk.utils.paths.var_dir / "wato/php-api")
    makedirs(cmk.utils.paths.var_dir / "wato/auth")
    makedirs(cmk.utils.paths.tmp_dir / "wato/activation")
    makedirs(cmk.utils.paths.omd_root / "var/log")
    makedirs(cmk.utils.paths.omd_root / "tmp/check_mk")
    makedirs(cmk.utils.paths.default_config_dir / "conf.d/wato")
    makedirs(cmk.utils.paths.default_config_dir / "multisite.d/wato")
    makedirs(cmk.utils.paths.default_config_dir / "mkeventd.d/wato")
    makedirs(cmk.utils.paths.local_dashboards_dir)
    makedirs(cmk.utils.paths.local_views_dir)
    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        # needed for visuals.load()
        makedirs(cmk.utils.paths.local_reports_dir)
    _touch(cmk.utils.paths.default_config_dir / "mkeventd.mk")
    _touch(cmk.utils.paths.default_config_dir / "multisite.mk")
    _touch(cmk.utils.paths.omd_root / "etc/passwordlist.txt")
    _dump(
        Path(cmk.utils.paths.omd_root, "etc/omd/site.conf"),
        """CONFIG_ADMIN_MAIL=''
CONFIG_AGENT_RECEIVER='on'
CONFIG_AGENT_RECEIVER_PORT='8000'
CONFIG_APACHE_MODE='own'
CONFIG_APACHE_TCP_ADDR='127.0.0.1'
CONFIG_APACHE_TCP_PORT='5002'
CONFIG_AUTOMATION_HELPER='on'
CONFIG_AUTOSTART='off'
CONFIG_CORE='cmc'
CONFIG_LIVEPROXYD='on'
CONFIG_LIVESTATUS_TCP='off'
CONFIG_LIVESTATUS_TCP_ONLY_FROM='0.0.0.0 ::/0'
CONFIG_LIVESTATUS_TCP_PORT='6557'
CONFIG_LIVESTATUS_TCP_TLS='on'
CONFIG_MKEVENTD='on'
CONFIG_MKEVENTD_SNMPTRAP='off'
CONFIG_MKEVENTD_SYSLOG='on'
CONFIG_MKEVENTD_SYSLOG_TCP='off'
CONFIG_MULTISITE_AUTHORISATION='on'
CONFIG_MULTISITE_COOKIE_AUTH='on'
CONFIG_NSCA='off'
CONFIG_NSCA_TCP_PORT='5667'
CONFIG_PNP4NAGIOS='on'
CONFIG_PIGGYBACK_HUB='off'
CONFIG_RABBITMQ_PORT='5672'
CONFIG_RABBITMQ_ONLY_FROM='0.0.0.0 ::'
CONFIG_RABBITMQ_DIST_PORT='25672'
CONFIG_TRACE_JAEGER_ADMIN_PORT='14269'
CONFIG_TRACE_JAEGER_UI_PORT='13333'
CONFIG_TRACE_RECEIVE='off'
CONFIG_TRACE_RECEIVE_ADDRESS='[::1]'
CONFIG_TRACE_RECEIVE_PORT='4321'
CONFIG_TRACE_SEND='off'
CONFIG_TRACE_SEND_TARGET='local_site'
CONFIG_TMPFS='on'""",
    )
    _dump(
        cmk.utils.paths.default_config_dir / "mkeventd.d/wato/rules.mk",
        r"""
# Written by WATO
# encoding: utf-8

rule_packs += \
[{'id': 'default', 'title': 'Default rule pack', 'rules': [], 'disabled': False, 'hits': 0}]
""",
    )
    _dump(
        cmk.utils.paths.default_config_dir / "multisite.d/sites.mk",
        r"""
# Written by conftest.py
# encoding: utf-8

sites.update(%r)
        """
        % livestatus.SiteConfigurations(
            {
                SiteId("NO_SITE"): livestatus.SiteConfiguration(
                    {
                        "id": SiteId("NO_SITE"),
                        "alias": "Local site NO_SITE",
                        "socket": ("local", None),
                        "disable_wato": True,
                        "disabled": False,
                        "insecure": False,
                        "url_prefix": "/NO_SITE/",
                        "multisiteurl": "",
                        "persist": False,
                        "replicate_ec": False,
                        "replicate_mkps": False,
                        "replication": None,
                        "timeout": 5,
                        "user_login": True,
                        "proxy": None,
                        "user_sync": "all",
                        "status_host": None,
                        "message_broker_port": 5672,
                        "is_trusted": True,
                    }
                )
            }
        ),
    )

    yield
    omd_site.cache_clear()


def cleanup_cmk_tmp_dir() -> Iterator[None]:
    yield

    import cmk.utils.paths

    if "pytest_cmk_" not in str(cmk.utils.paths.tmp_dir):
        return

    try:
        shutil.rmtree(str(cmk.utils.paths.tmp_dir))
    except FileNotFoundError:
        pass


def cleanup_omd_root_after_test() -> Iterator[None]:
    yield

    if cmk.utils.paths.omd_root == Path(""):
        logger.warning("OMD_ROOT not set, skipping cleanup")
        return

    # Fail the execution in case any crash reports were created
    try:
        _report_crashes()
    finally:
        # Ensure there is no file left over in the unit test fake site
        # to prevent tests involving each other
        for entry in cmk.utils.paths.omd_root.iterdir():
            # This randomly fails for some unclear reasons. Looks like a race condition, but I
            # currently have no idea which triggers this since the tests are not executed in
            # parallel at the moment. This is meant as quick hack, trying to reduce flaky results.
            try:
                if entry.is_dir():
                    shutil.rmtree(str(entry))
                else:
                    entry.unlink()
            except OSError as e:
                logger.debug("Failed to cleanup %s after test: %s. Keep going anyway", entry, e)


def prevent_livestatus_connect() -> Iterator[None]:
    """Prevent tests from trying to open livestatus connections. This will result in connect
    timeouts which slow down our tests."""

    orig_init = livestatus.MultiSiteConnection.__init__

    def init_mock(
        self: livestatus.MultiSiteConnection,
        sites: livestatus.SiteConfigurations,
        disabled_sites: livestatus.SiteConfigurations | None = None,
        only_sites_postprocess: Callable[
            [Sequence[SiteId] | None], list[SiteId] | None
        ] = lambda x: list(x) if x else None,
    ) -> None:
        orig_init(self, sites, disabled_sites, only_sites_postprocess)
        if self.deadsites:
            pytest.fail("Dead sites: %r" % self.deadsites)

    with patch.object(
        livestatus.SingleSiteConnection,
        "_create_socket",
        lambda *_: pytest.fail(
            "The test tried to use a livestatus connection. This will result in connect timeouts. "
            "Use mock_livestatus for mocking away the livestatus API"
        ),
    ) as _:
        with patch.object(livestatus.MultiSiteConnection, "__init__", init_mock) as _:
            yield


def use_fakeredis() -> Iterator[None]:
    """Use fakeredis client instead of redis.Redis"""
    with patch.object(redis, "Redis", FakeRedis) as _:
        redis.get_redis_client().flushall()
        yield


def enable_cmk_debug() -> Iterator[None]:
    debug_mode = cmk.ccc.debug.debug_mode
    cmk.ccc.debug.enable()
    yield
    cmk.ccc.debug.debug_mode = debug_mode


def reduce_password_hashing_rounds() -> Iterator[None]:
    """Reduce the number of rounds for hashing with bcrypt to the allowed minimum"""
    with patch.object(cmk.crypto.password_hashing, "BCRYPT_ROUNDS", 4):
        yield


def prevent_security_event_file_logging() -> Iterator[queue.Queue[logging.LogRecord]]:
    """cmk.utils.log.security_event.log_security_event implicitly opens a file logger upon it's
    first call which we want to avoid in the unit test context."""
    q: queue.Queue[logging.LogRecord] = queue.Queue()
    queue_handler = logging.handlers.QueueHandler(q)

    logger = logging.getLogger("cmk_security")
    logger.addHandler(queue_handler)
    try:
        yield q
    finally:
        logger.removeHandler(queue_handler)


def clear_caches() -> None:
    cmk.utils.caching.cache_manager.clear()
    cmk_version.edition.cache_clear()
