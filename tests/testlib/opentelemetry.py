#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import enum
import logging
import os
import signal
import subprocess
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path

from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site
from tests.testlib.utils import execute

logger = logging.getLogger(__name__)

OPENTELEMETRY_DIR_FILES = Path("var/check_mk/otel_collector")
OPENTELEMETRY_DIR_AUTOCOMPLETE = Path("tmp/check_mk/otel_collector")


class ScriptFileName(enum.Enum):
    OTEL_ALL_METRIC_TYPES = "opentelemetry_all_metric_types.py"
    OTEL_HTTP = "opentelemetry_http.py"
    OTEL_GRPC = "opentelemetry_grpc.py"
    PROMETHEUS = "opentelemetry_prometheus.py"

    def __str__(self):
        return self.value


@contextmanager
def opentelemetry_app(
    script_file_name: ScriptFileName, additional_args: list[str] | None = None
) -> Iterator[subprocess.Popen]:
    """Context manager to run an OpenTelemetry application script, handles its lifecycle,
    and raises errors if execution fails."""
    scripts_folder = repo_path() / "tests" / "scripts"
    script_path = scripts_folder / str(script_file_name)
    env = os.environ.copy()
    # by default, OpenTelemetry SDK is disabled in system tests
    env["OTEL_SDK_DISABLED"] = "false"

    command = ["python", str(script_path)]
    if additional_args:
        command.extend(additional_args)

    logger.info("Starting OpenTelemetry application with script: %s", script_file_name)
    with execute(
        command,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    ) as process:
        try:
            yield process
        finally:
            logger.info("Terminating OpenTelemetry application")
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate()
            logger.info(f"OpenTelemetry application output:\n{stdout.strip()}")
            if process.returncode != 0 or stderr:
                error_message = (
                    f"OpenTelemetry application encountered an issue.\n"
                    f"Exit code: {process.returncode}\n"
                    f"Error output:\n{stderr.strip()}"
                )
                logger.error(error_message)
                raise RuntimeError(
                    "Failed to execute OpenTelemetry application. Check logs for details."
                )


def wait_for_opentelemetry_data(
    site: Site, host_name: str, timeout: int = 90, interval: int = 5
) -> None:
    """Wait until OpenTelemetry data is available for the specified host."""
    opentelemetry_data_path = OPENTELEMETRY_DIR_FILES / f"host_monitoring/{host_name}"
    wait_until(
        lambda: site.file_exists(opentelemetry_data_path), timeout=timeout, interval=interval
    )


def delete_opentelemetry_data(site: Site) -> None:
    """Delete OpenTelemetry data for the site."""
    host_monitoring_data_path = OPENTELEMETRY_DIR_FILES / "host_monitoring"
    if site.file_exists(host_monitoring_data_path):
        site.delete_dir(host_monitoring_data_path)

    autocompleter_data_path = OPENTELEMETRY_DIR_AUTOCOMPLETE / "autocompleter"
    for file in site.listdir(autocompleter_data_path):
        site.delete_file(autocompleter_data_path / file)


def wait_for_otel_collector_conf(
    site: Site, host_name: str, timeout: int = 90, interval: int = 5
) -> None:
    """Wait until the OTel collector configuration is applied and services are created."""

    def _check_config():
        logger.info("Running service discovery and activating changes")
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)
        site.openapi.changes.activate_and_wait_for_completion()

        logger.info("Checking OTel services are created and have expected states")
        services = site.get_host_services(host_name)
        return len(services) > 10

    wait_until(_check_config, timeout=timeout, interval=interval)


@contextmanager
def otel_collector_enabled(site: Site) -> Generator[None]:
    # Don't use `site.omd_config` directly here.
    # `site.omd_config` uses `site.omd_stopped`, which complains if the site is partially running.
    # In the context of the OTel collector, this can happen if the last collector rule is removed.
    # Activating changes will then stop the collector, resulting in a partially running site.
    backed_up_setting = site.get_config("OPENTELEMETRY_COLLECTOR")
    site.set_config(
        "OPENTELEMETRY_COLLECTOR",
        "on",
        with_restart=True,
    )
    try:
        yield
    finally:
        site.set_config(
            "OPENTELEMETRY_COLLECTOR",
            backed_up_setting,
            with_restart=True,
        )
