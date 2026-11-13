#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Literal
from unittest import mock
from unittest.mock import MagicMock

import pytest

import cmk.product_usage.cli as product_usage_cli
import cmk.product_usage.collectors.checks as checks_collector
import cmk.product_usage.collectors.inventory as inventory_collector
import cmk.product_usage.collectors.site_info as site_info_collector
from cmk.ccc.version import Edition
from cmk.product_usage.config import load_product_usage_config, ProductUsageAnalyticsSettings
from cmk.product_usage.exceptions import ConfigError, EndpointUnreachableError
from cmk.product_usage.schema import InventoryData, SiteInfo
from cmk.utils import http_proxy_config, paths
from cmk.utils.licensing.handler import LicenseState


def test_resolve_proxy_config_falls_back_to_environment_when_no_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The base config carries no configured proxies, so an unknown "global" proxy name must
    # fall back to the environment proxy instead of raising.
    mock_base_config = MagicMock()
    mock_base_config.loaded_config.http_proxies = {}
    monkeypatch.setattr("cmk.base.config.load", MagicMock(return_value=mock_base_config))
    monkeypatch.setattr("cmk.base.app.make_app", MagicMock())

    proxy_config = product_usage_cli.resolve_proxy_config(("global", "missing"))

    assert isinstance(proxy_config, http_proxy_config.EnvironmentProxyConfig)


def test_load_product_usage_config_defaults_when_file_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing/unreadable config file yields the safe 'not_decided' default."""
    monkeypatch.setattr(
        "cmk.product_usage.config.read_config_file", MagicMock(side_effect=ConfigError)
    )

    settings = load_product_usage_config(paths.default_config_dir, mock.Mock())

    assert settings.enabled == "not_decided"
    assert settings.proxy_setting == ("environment", "environment")


@pytest.mark.parametrize("state", ["disabled", "not_decided"])
def test_cron_skips_heavy_work_when_not_enabled(
    monkeypatch: pytest.MonkeyPatch, state: Literal["disabled", "not_decided"]
) -> None:
    """A scheduled run must return early without the heavy proxy load or any collection."""
    monkeypatch.setattr(product_usage_cli, "init_logging", MagicMock())
    monkeypatch.setattr(
        product_usage_cli,
        "load_product_usage_config",
        MagicMock(
            return_value=ProductUsageAnalyticsSettings(
                enabled=state, proxy_setting=("environment", "environment")
            )
        ),
    )
    resolve_spy = MagicMock()
    collect_spy = MagicMock()
    transmit_spy = MagicMock()
    monkeypatch.setattr(product_usage_cli, "resolve_proxy_config", resolve_spy)
    monkeypatch.setattr(product_usage_cli, "collect_data", collect_spy)
    monkeypatch.setattr(product_usage_cli, "transmit_data", transmit_spy)

    assert product_usage_cli.main(["--cron"]) == 0

    resolve_spy.assert_not_called()
    collect_spy.assert_not_called()
    transmit_spy.assert_not_called()


def test_cron_enabled_first_run_only_schedules(monkeypatch: pytest.MonkeyPatch) -> None:
    """The first scheduled run after enabling only plans the next run; it does not collect."""
    monkeypatch.setattr(product_usage_cli, "init_logging", MagicMock())
    monkeypatch.setattr(
        product_usage_cli,
        "load_product_usage_config",
        MagicMock(
            return_value=ProductUsageAnalyticsSettings(
                enabled="enabled", proxy_setting=("environment", "environment")
            )
        ),
    )
    monkeypatch.setattr(product_usage_cli, "get_next_run_ts", MagicMock(return_value=None))
    store_spy = MagicMock()
    resolve_spy = MagicMock()
    collect_spy = MagicMock()
    monkeypatch.setattr(product_usage_cli, "store_next_run_ts", store_spy)
    monkeypatch.setattr(product_usage_cli, "resolve_proxy_config", resolve_spy)
    monkeypatch.setattr(product_usage_cli, "collect_data", collect_spy)

    assert product_usage_cli.main(["--cron"]) == 0

    store_spy.assert_called_once()
    resolve_spy.assert_not_called()
    collect_spy.assert_not_called()


def test_upload_resolves_proxy_and_transmits(monkeypatch: pytest.MonkeyPatch) -> None:
    """The upload path resolves the proxy config and hands it to the transmission."""
    monkeypatch.setattr(product_usage_cli, "init_logging", MagicMock())
    settings = ProductUsageAnalyticsSettings(enabled="enabled", proxy_setting=("no_proxy", None))
    monkeypatch.setattr(
        product_usage_cli, "load_product_usage_config", MagicMock(return_value=settings)
    )
    sentinel_proxy = MagicMock()
    resolve_spy = MagicMock(return_value=sentinel_proxy)
    transmit_spy = MagicMock()
    monkeypatch.setattr(product_usage_cli, "resolve_proxy_config", resolve_spy)
    monkeypatch.setattr(product_usage_cli, "transmit_data", transmit_spy)

    assert product_usage_cli.main(["--upload"]) == 0

    resolve_spy.assert_called_once_with(("no_proxy", None))
    transmit_spy.assert_called_once()
    assert transmit_spy.call_args.kwargs["proxy_config"] is sentinel_proxy


def test_parse_args_cron_enables_all_phases() -> None:
    assert product_usage_cli.parse_args(["--cron"]) == product_usage_cli.ProductUsageRequest(
        collect=True, store=True, upload=True, schedule=True, write_to_stdout=False
    )


def test_parse_args_collection_collects_and_stores() -> None:
    assert product_usage_cli.parse_args(["--collection"]) == product_usage_cli.ProductUsageRequest(
        collect=True, store=True
    )


def test_parse_args_dry_run_collects_only() -> None:
    assert product_usage_cli.parse_args(["--dry-run"]) == product_usage_cli.ProductUsageRequest(
        collect=True
    )


def test_parse_args_upload_only() -> None:
    assert product_usage_cli.parse_args(["--upload"]) == product_usage_cli.ProductUsageRequest(
        upload=True
    )


@pytest.mark.parametrize(
    ("cloud_trial", "payload_name"),
    [
        pytest.param(True, "cloud_trial_analytics", id="cloud trial"),
        pytest.param(False, "product_usage_analytics", id="any other site"),
    ],
)
def test_dry_run_writes_the_cloud_trial_payload_only_on_a_cloud_trial_site(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cloud_trial: bool,
    payload_name: str,
) -> None:
    monkeypatch.setattr(product_usage_cli, "init_logging", MagicMock())
    monkeypatch.setattr(product_usage_cli, "is_cloud_trial", MagicMock(return_value=cloud_trial))
    monkeypatch.setattr(
        site_info_collector,
        "collect",
        MagicMock(
            return_value=SiteInfo(
                id=uuid.UUID("0f8fad5b-d9cb-469f-a165-70867728950e"),
                count_hosts=1,
                count_services=2,
                count_folders=3,
                edition="cloud",
                cmk_version="2.5.0-2026.01.06",
                os="Ubuntu 24.04.3 LTS",
            )
        ),
    )
    monkeypatch.setattr(checks_collector, "collect", MagicMock(return_value={}))
    monkeypatch.setattr(
        inventory_collector,
        "collect",
        MagicMock(return_value=InventoryData(hosts_with_inventory=0)),
    )

    assert product_usage_cli.main(["--dry-run"]) == 0

    assert json.loads(capsys.readouterr().out)["metadata"]["name"] == payload_name


def test_cloud_site_in_trial_is_a_cloud_trial() -> None:
    result = product_usage_cli.is_cloud_trial(
        edition=Edition.CLOUD,
        read_license_state=lambda: LicenseState.TRIAL,
        logger=logging.getLogger(__name__),
    )

    assert result is True


def test_cloud_site_with_license_is_not_a_cloud_trial() -> None:
    result = product_usage_cli.is_cloud_trial(
        edition=Edition.CLOUD,
        read_license_state=lambda: LicenseState.LICENSED,
        logger=logging.getLogger(__name__),
    )

    assert result is False


@pytest.mark.parametrize("edition", [e for e in Edition if e is not Edition.CLOUD])
def test_on_prem_site_in_trial_is_not_a_cloud_trial(edition: Edition) -> None:
    result = product_usage_cli.is_cloud_trial(
        edition=edition,
        read_license_state=lambda: LicenseState.TRIAL,
        logger=logging.getLogger(__name__),
    )

    assert result is False


def test_failing_license_read_falls_back_to_no_cloud_trial_and_logs_the_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    result = product_usage_cli.is_cloud_trial(
        edition=Edition.CLOUD,
        read_license_state=_raise_license_error,
        logger=logging.getLogger(__name__),
    )

    assert result is False
    assert [record.levelname for record in caplog.records] == ["ERROR"]


@pytest.mark.parametrize("edition", [e for e in Edition if e is not Edition.CLOUD])
def test_on_prem_site_does_not_read_the_license_state(edition: Edition) -> None:
    product_usage_cli.is_cloud_trial(
        edition=edition,
        read_license_state=_fail_on_license_read,
        logger=logging.getLogger(__name__),
    )


def _raise_license_error() -> LicenseState:
    raise RuntimeError("license files missing")


def _fail_on_license_read() -> LicenseState:
    # pytest.fail raises a BaseException, so the gate's `except Exception` cannot swallow it
    pytest.fail("the license state must not be read on non-Cloud editions")


def _run_failing_dry_run(monkeypatch: pytest.MonkeyPatch, report_crash: Callable[[], str]) -> int:
    monkeypatch.setattr(
        product_usage_cli,
        "init_logging",
        MagicMock(return_value=logging.getLogger("cmk.product_usage.test")),
    )
    monkeypatch.setattr(product_usage_cli, "is_cloud_trial", MagicMock(return_value=False))
    monkeypatch.setattr(
        product_usage_cli, "collect_data", MagicMock(side_effect=RuntimeError("collector broke"))
    )
    return product_usage_cli.main(["--dry-run"], report_crash=report_crash)


def test_unexpected_error_reports_the_crash_id(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _run_failing_dry_run(monkeypatch, lambda: "4711") == -1

    assert "Unexpected error (Crash ID: 4711)" in caplog.text
    assert "(Crash ID: 4711)" in capsys.readouterr().err


def test_failing_crash_report_keeps_the_original_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def report_crash() -> str:
        raise OSError("crash directory not writable")

    assert _run_failing_dry_run(monkeypatch, report_crash) == -1

    last = caplog.records[-1]
    assert last.getMessage() == "Unexpected error (Crash ID: none)"
    assert last.exc_info is not None
    assert isinstance(last.exc_info[1], RuntimeError)


def test_create_crash_report_stores_the_handled_exception(tmp_path: Path) -> None:
    (tmp_path / "etc/omd").mkdir(parents=True)
    (tmp_path / "etc/omd/site.conf").write_text("CONFIG_CORE='cmc'\n")
    try:
        raise RuntimeError("collector broke")
    except RuntimeError:
        crash_id = product_usage_cli.create_crash_report(tmp_path)

    crash_info = json.loads(
        (tmp_path / "var/check_mk/crashes/product-usage" / crash_id / "crash.info").read_text()
    )
    assert crash_info["exc_type"] == "RuntimeError"
    assert crash_info["exc_value"] == "collector broke"


def _patch_unreachable_endpoint(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch the CLI to have nothing to collect and an unreachable endpoint"""
    monkeypatch.setattr(
        product_usage_cli,
        "init_logging",
        MagicMock(return_value=logging.getLogger("cmk.product_usage.test")),
    )
    monkeypatch.setattr(
        product_usage_cli,
        "load_product_usage_config",
        MagicMock(
            return_value=ProductUsageAnalyticsSettings(
                enabled="enabled", proxy_setting=("no_proxy", None)
            )
        ),
    )
    monkeypatch.setattr(product_usage_cli, "should_run_collection_on_schedule", lambda *_: True)
    monkeypatch.setattr(product_usage_cli, "get_next_run_ts", MagicMock(return_value=1))
    monkeypatch.setattr(product_usage_cli, "is_cloud_trial", MagicMock(return_value=False))
    monkeypatch.setattr(product_usage_cli, "collect_data", MagicMock())
    monkeypatch.setattr(product_usage_cli, "store_data", MagicMock())
    monkeypatch.setattr(product_usage_cli, "resolve_proxy_config", MagicMock())
    monkeypatch.setattr(
        product_usage_cli,
        "transmit_data",
        MagicMock(side_effect=EndpointUnreachableError("Could not connect")),
    )
    store_next_run_spy = MagicMock()
    monkeypatch.setattr(product_usage_cli, "store_next_run_ts", store_next_run_spy)
    return store_next_run_spy


def test_cron_with_unreachable_endpoint_logs_only_and_plans_the_next_run(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store_next_run_spy = _patch_unreachable_endpoint(monkeypatch)

    assert product_usage_cli.main(["--cron"], report_crash=MagicMock()) == 1

    assert capsys.readouterr().err == ""
    assert [
        (r.getMessage(), r.exc_info) for r in caplog.records if r.levelno >= logging.WARNING
    ] == [("Could not connect", None)]
    store_next_run_spy.assert_called_once()


def test_manual_upload_with_unreachable_endpoint_reports_the_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_unreachable_endpoint(monkeypatch)

    assert product_usage_cli.main(["--upload"], report_crash=MagicMock()) == 1

    assert capsys.readouterr().err == "cmk-product-usage: Could not connect\n"


def test_unreachable_endpoint_creates_no_crash_report(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_unreachable_endpoint(monkeypatch)
    report_crash = MagicMock()

    product_usage_cli.main(["--upload"], report_crash=report_crash)

    report_crash.assert_not_called()


def test_cron_writes_no_crash_to_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_unreachable_endpoint(monkeypatch)
    monkeypatch.setattr(
        product_usage_cli, "collect_data", MagicMock(side_effect=RuntimeError("collector broke"))
    )

    assert product_usage_cli.main(["--cron"], report_crash=lambda: "4711") == -1

    assert capsys.readouterr().err == ""
