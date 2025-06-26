#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This script demonstrates the use of OpenTelemetry for metrics export via Prometheus."""

import logging
import signal
import sys
import time

from prometheus_client import Counter, start_http_server

logger = logging.getLogger("otel.prometheus")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

PROMETHEUS_PORT = 9090
SLEEP_DURATION = 30

DEFAULT_OTEL_COLLECTOR_PROMETHEUS_METRIC_COUNT = 5  # metrics the site collector adds
DEFAULT_PROMETHEUS_METRIC_COUNT = 10  # metrics the client sdk adds
DEFAULT_CMK_SERVICE_COUNT = 2  # Check_MK and Check_MK Discovery
PROMETHEUS_METRIC_COUNT = 1  # only one Counter metric is used in this script
EXPECTED_PROMETHEUS_SERVICE_COUNT = (
    DEFAULT_OTEL_COLLECTOR_PROMETHEUS_METRIC_COUNT
    + DEFAULT_PROMETHEUS_METRIC_COUNT
    + DEFAULT_CMK_SERVICE_COUNT
    + PROMETHEUS_METRIC_COUNT * 2
)


def shutdown_handler(signum: object, frame: object) -> None:
    logger.info("Shutting down Prometheus HTTP server.")
    sys.exit(0)


def main() -> None:
    # Create a Prometheus counter metric
    prometheus_counter = Counter("test_counter", "A simple counter for testing")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info(f"Starting Prometheus HTTP server on port {PROMETHEUS_PORT}.")
    start_http_server(PROMETHEUS_PORT)

    counter = 0
    while True:
        logger.info(f"Counter value is {counter}.")
        prometheus_counter.inc()
        counter += 1
        time.sleep(SLEEP_DURATION)


if __name__ == "__main__":
    main()
