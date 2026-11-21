#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import override

from cmk.ccc.crash_reporting import ABCCrashReport, CrashReportStore, make_crash_report_base_path
from cmk.ccc.version import Edition, edition
from cmk.ccc.version_info import get_general_version_infos
from cmk.product_usage.collection import (
    collect_cloud_trial_data,
    collect_data,
    data_storage_path,
    store_data,
)
from cmk.product_usage.config import (
    get_proxy_config,
    load_product_usage_config,
    ProxyConfig,
    ProxySetting,
)
from cmk.product_usage.exceptions import EndpointUnreachableError
from cmk.product_usage.logger import init_logging
from cmk.product_usage.schedule import (
    create_next_random_ts,
    create_next_ts,
    get_next_run_ts,
    next_run_file_path,
    next_run_interval,
    should_run_collection_on_schedule,
    store_next_run_ts,
)
from cmk.product_usage.transmission import transmit_data
from cmk.utils import paths
from cmk.utils.licensing.handler import LicenseState


@dataclass(frozen=True, kw_only=True)
class ProductUsageRequest:
    collect: bool = False
    store: bool = False
    upload: bool = False
    schedule: bool = False
    write_to_stdout: bool = True


def resolve_proxy_config(proxy_setting: ProxySetting) -> ProxyConfig:
    # Building the base app and loading the base config is expensive and pulls in cmk.base (and
    # its transitive `import livestatus`). It is only needed to read the configured HTTP proxies
    # for the upload, so we import it lazily and call this only on the upload path. This keeps
    # disabled and not-due runs cheap and free of cmk.base imports.
    from cmk.base.app import make_app
    from cmk.base.config import load

    this_edition = edition(paths.omd_root)
    base_config = load(
        discovery_rulesets=(),
        get_builtin_host_labels=make_app(this_edition).get_builtin_host_labels,
    )

    return get_proxy_config(
        proxy_setting=proxy_setting,
        global_proxies=base_config.loaded_config.http_proxies,
    )


class ProductUsageCrashReport(ABCCrashReport[None]):
    @classmethod
    @override
    def type(cls) -> str:
        return "product-usage"


def create_crash_report(omd_root: Path) -> str:
    """Store a crash report of the exception being handled and return its crash ID"""
    crash = ProductUsageCrashReport(
        crash_report_base_path=make_crash_report_base_path(omd_root),
        crash_info=ProductUsageCrashReport.make_crash_info(
            get_general_version_infos(omd_root), None
        ),
    )
    CrashReportStore().save(crash)
    return crash.ident_to_text()


def main(
    args: Sequence[str],
    *,
    report_crash: Callable[[], str] = lambda: create_crash_report(paths.omd_root),
) -> int:
    request = parse_args(args)
    logger = init_logging(paths.log_dir)
    now = datetime.now()
    settings = load_product_usage_config(paths.default_config_dir, logger)
    next_run_fp = next_run_file_path(paths.var_dir)
    upload_error: EndpointUnreachableError | None = None

    try:
        if request.schedule:
            if settings.enabled != "enabled":
                return 0

            # If this is the first run after product usage analytics being enabled,
            # we need to create a random next timestamp within the first-run window and then exit.
            if not get_next_run_ts(next_run_fp):
                next_scheduled_run_at = create_next_random_ts(now)
                logger.info(
                    "First scheduled execution, planning the next execution at %s",
                    next_scheduled_run_at,
                )
                store_next_run_ts(next_run_fp, next_scheduled_run_at)
                return 0

            if not should_run_collection_on_schedule(paths.var_dir, now):
                return 0

            logger.info("Scheduled run starts")

        cloud_trial = (request.collect or request.schedule) and is_cloud_trial(
            edition=edition(paths.omd_root),
            read_license_state=_read_cloud_license_state,
            logger=logger,
        )

        if request.collect:
            data = collect_data(
                paths.var_dir,
                paths.check_mk_config_dir,
                paths.default_config_dir,
                paths.omd_root,
                paths.locale_dir,
                logger,
            )
            if cloud_trial:
                data = collect_cloud_trial_data(
                    data,
                    var_dir=paths.var_dir,
                    default_config_dir=paths.default_config_dir,
                    logger=logger,
                )
            if request.write_to_stdout:
                sys.stdout.write(
                    data.model_dump_with_metadata_json(indent=2).decode("utf-8") + "\n"
                )
                sys.stdout.flush()

            if request.store:
                store_data(data, paths.var_dir)

        if request.upload:
            proxy_config = resolve_proxy_config(settings.proxy_setting)
            try:
                transmit_data(paths.var_dir, logger, proxy_config=proxy_config)
            except EndpointUnreachableError as e:
                upload_error = e

        if upload_error is not None:
            # Not a crash: the network of the site decides about this, so the message is enough
            # and a traceback would only hide it.
            logger.error("%(error)s", {"error": upload_error})
            _write_error(request, f"cmk-product-usage: {upload_error}")

        if request.schedule:
            interval = next_run_interval(cloud_trial=cloud_trial)
            next_scheduled_run_at = create_next_ts(now, interval=interval)
            logger.info(
                "Planning the next execution at %s, in %s days",
                next_scheduled_run_at,
                interval.days,
            )
            store_next_run_ts(next_run_fp, next_scheduled_run_at)

    except Exception as e:
        crash_id = _report_crash(report_crash, logger)
        _write_error(request, f"cmk-product-usage: {e} (Crash ID: {crash_id})")
        logger.exception("Unexpected error (Crash ID: %(crash_id)s)", {"crash_id": crash_id})
        return -1

    if upload_error is not None:
        return 1

    logger.info("Successfully ran")

    return 0


def _write_error(request: ProductUsageRequest, message: str) -> None:
    # cron mails everything written to stderr. Scheduled runs only log, the admin finds the
    # errors in the log and the crash reports.
    if not request.schedule:
        sys.stderr.write(f"{message}\n")


def _report_crash(report_crash: Callable[[], str], logger: logging.Logger) -> str:
    """Create the crash report, which must not hide the exception it reports"""
    try:
        return report_crash()
    except Exception:
        logger.exception("Could not create a crash report")
        return "none"


def parse_args(args: Sequence[str]) -> ProductUsageRequest:
    storage_directory = data_storage_path(paths.var_dir).absolute()
    parser = argparse.ArgumentParser(
        prog="cmk-product-usage",
        usage="cmk-product-usage [--collection | --upload | --dry-run]",
        description=(
            "Collect and send product usage data. "
            f"You can collect and store data locally in `{storage_directory}`, "
            "upload product usage files, "
            "or display product usage data in a dry-run mode."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--collection",
        action="store_true",
        help=f"Collect product usage data and store it locally in `{storage_directory}`.",
    )
    group.add_argument(
        "--upload",
        action="store_true",
        help=f"Send local product usage data files from `{storage_directory}`.",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show product usage data in output without storing or sending.",
    )
    group.add_argument(
        "--cron",
        action="store_true",
        help="Used by the crontab to trigger the collection, storing and transmission on a regular schedule.",
    )

    parsed_args = parser.parse_args(args)

    if parsed_args.collection:
        return ProductUsageRequest(collect=True, store=True)
    elif parsed_args.upload:
        return ProductUsageRequest(upload=True)
    elif parsed_args.dry_run:
        return ProductUsageRequest(collect=True)
    elif parsed_args.cron:
        return ProductUsageRequest(
            collect=True, store=True, upload=True, schedule=True, write_to_stdout=False
        )
    return ProductUsageRequest(collect=True, store=True, upload=True)


def is_cloud_trial(
    *,
    edition: Edition,
    read_license_state: Callable[[], LicenseState],
    logger: logging.Logger,
) -> bool:
    # Read the license state only on Cloud: only Cloud has the trial schedule, and reading the
    # state there needs the commercial Cloud licensing handler.
    if edition is not Edition.CLOUD:
        return False
    try:
        return read_license_state() is LicenseState.TRIAL
    except Exception:
        logger.exception("Could not read the license state, assuming no Cloud trial")
        return False


def _read_cloud_license_state() -> LicenseState:
    from cmk.utils.nonfree.pro.licensing.registry import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
        get_available_licensing_handler_type,
    )

    # Without the commercial packages the import is untyped, so pin the type here
    state: LicenseState = get_available_licensing_handler_type(Edition.CLOUD).make().state
    return state


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
