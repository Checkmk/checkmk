#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
OpenTelemetry Metrics Sender
Sends counter, gauge, and histogram metrics to an OTEL HTTP receiver every 30 seconds.
"""

import argparse
import logging
import random
import string
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import requests
import urllib3
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

# Enable OpenTelemetry logging to see export errors
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("opentelemetry.exporter.otlp").setLevel(logging.DEBUG)


@dataclass(frozen=True)
class ServiceContext:
    app_id: int
    service_id: int
    provider: MeterProvider
    meter: Meter
    request_counters: list[Any]
    gauges: list[Any]
    histograms: list[Any]
    long_labels: dict[str, str]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="OpenTelemetry Metrics Sender")
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="OTEL collector hostname (e.g., example.com)",
    )
    parser.add_argument(
        "--port", type=int, default=4318, help="OTEL collector port (default: 4318)"
    )
    parser.add_argument("--username", type=str, required=True, help="OTEL collector username")
    parser.add_argument("--password", type=str, required=True, help="OTEL collector password")
    parser.add_argument(
        "--num-apps", type=int, default=5, help="Number of applications (default: 5)"
    )
    parser.add_argument(
        "--services-per-app",
        type=int,
        default=3,
        help="Number of services per application (default: 3)",
    )
    parser.add_argument(
        "--num-counters",
        type=int,
        default=5,
        help="Number of counters per service (default: 5)",
    )
    parser.add_argument(
        "--num-gauges",
        type=int,
        default=3,
        help="Number of gauges per service (default: 3)",
    )
    parser.add_argument(
        "--num-histograms",
        type=int,
        default=3,
        help="Number of histograms per service (default: 3)",
    )
    parser.add_argument(
        "--label-size",
        type=int,
        default=100,
        help="Size of each long label value in characters (default: 100)",
    )
    parser.add_argument(
        "--num-labels",
        type=int,
        default=3,
        help="Number of long label attributes to add (default: 3)",
    )
    parser.add_argument(
        "--export-interval",
        type=int,
        default=15,
        help="Export interval for sending metrics to collector in seconds (default: 15)",
    )
    parser.add_argument(
        "--sleep-interval",
        type=int,
        default=15,
        help="Sleep interval between metric generation iterations in seconds (default: 15)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=0,
        help="Number of metric generation iterations (default: 0 = run forever)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL certificate verification (for self-signed certs)",
    )
    parser.add_argument("--http", action="store_true", help="Use HTTP instead of HTTPS")
    return parser.parse_args()


def generate_long_labels(num_labels: int, label_size: int) -> dict[str, str]:
    """Generate static long labels for a service."""
    chars = string.ascii_letters + string.digits
    return {
        f"long_label_{i + 1}": "".join(random.choice(chars) for _ in range(label_size))
        for i in range(num_labels)
    }


def setup_metrics(
    app_id: int,
    service_id: int,
    endpoint: str,
    username: str,
    password: str,
    export_interval_ms: int,
    insecure: bool = False,
) -> tuple[MeterProvider, "Meter"]:
    """Initialize OpenTelemetry metrics with OTLP HTTP exporter for a specific resource."""
    resource = Resource(
        attributes={
            "application.name": f"app-{app_id}",
            "service.name": f"app-{app_id}-copy-{service_id}",
            "service.version": "1.0.0",
            "service.instance.id": f"app-{app_id}-instance-{service_id}",
            "deployment.environment": "test",
            "project": "otel-metrics-test",
            "host.name": f"server-{app_id:02d}-{service_id:02d}",
        }
    )

    # Configure exporter with basic authentication
    session = requests.Session()
    session.headers.update({"Authorization": f"Basic {get_basic_auth_header(username, password)}"})
    if insecure:
        session.verify = False
        # Some versions of the OTLP exporter pass verify= explicitly when calling
        # session.send(), overriding session.verify.  Mounting a custom adapter
        # ensures SSL verification is disabled at the transport level regardless.
        from requests.adapters import HTTPAdapter

        class _NoVerifyAdapter(HTTPAdapter):
            def send(
                self,
                request: requests.PreparedRequest,
                stream: bool = False,
                timeout: float | tuple[float, float] | tuple[float, None] | None = None,
                verify: bool | str = True,
                cert: bytes | str | tuple[bytes | str, bytes | str] | None = None,
                proxies: Mapping[str, str] | None = None,
            ) -> requests.Response:
                del verify
                return super().send(
                    request,
                    stream=stream,
                    timeout=timeout,
                    verify=False,
                    cert=cert,
                    proxies=proxies,
                )

        session.mount("https://", _NoVerifyAdapter())

    exporter = OTLPMetricExporter(
        endpoint=endpoint,
        session=session,
    )

    reader = PeriodicExportingMetricReader(
        exporter=exporter, export_interval_millis=export_interval_ms
    )

    provider = MeterProvider(resource=resource, metric_readers=[reader])
    meter = metrics.get_meter(__name__, meter_provider=provider)

    return provider, meter


def get_basic_auth_header(username: str, password: str) -> str:
    """Generate base64 encoded credentials for basic auth."""
    import base64

    credentials = f"{username}:{password}"
    return base64.b64encode(credentials.encode()).decode()


def check_connectivity(host: str, port: int, scheme: str) -> None:
    """Check if the OTEL collector endpoint is reachable."""
    import socket

    try:
        with socket.create_connection((host, port), timeout=5):
            pass
    except OSError:
        print(
            f"\nERROR: Cannot connect to {scheme}://{host}:{port}\n"
            "\nPlease make sure that:\n"
            "  1. The correct host and port are provided\n"
            "  2. The 'Metric Backend' has been enabled in the site\n"
            "  3. The 'OpenTelemetry Collector' has been enabled in the site\n"
        )
        raise SystemExit(1)


def main() -> None:
    """Main loop to generate and send metrics."""
    args = parse_args()

    # Build full endpoint URL from host and port
    scheme = "http" if args.http else "https"
    otel_endpoint = f"{scheme}://{args.host}:{args.port}/v1/metrics"

    check_connectivity(args.host, args.port, scheme)

    total_services = args.num_apps * args.services_per_app

    if args.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print("Starting OTEL metrics sender...")
    print(f"Sending metrics to: {otel_endpoint}")
    if args.insecure:
        print("SSL verification: DISABLED (self-signed certs allowed)")
    print(f"Authentication: Basic (username: {args.username})")
    print(f"Export interval: {args.export_interval} seconds")
    print(f"Number of applications: {args.num_apps}")
    print(f"Services per application: {args.services_per_app}")
    print(f"Total services: {total_services}")
    print(f"Number of counters per service: {args.num_counters}")
    print(f"Number of gauges per service: {args.num_gauges}")
    print(f"Number of histograms per service: {args.num_histograms}")
    print(f"Long labels per metric: {args.num_labels} (size: {args.label_size} chars each)")
    print(f"Sleep interval between iterations: {args.sleep_interval} seconds")
    if args.iterations == 0:
        print("Iterations: infinite")
    else:
        print(f"Iterations: {args.iterations}")

    # Calculate metric series
    counter_series_per_service = (
        args.num_counters * 3
    )  # 3 attribute combinations per counter (GET/200, POST/201, GET/404)
    gauge_series_per_service = args.num_gauges * 2  # 2 cores per gauge
    histogram_series_per_service = args.num_histograms * 1  # 1 endpoint per histogram
    series_per_service = (
        counter_series_per_service + gauge_series_per_service + histogram_series_per_service
    )
    total_series = series_per_service * total_services

    print("\nMetric series calculation:")
    print(
        f"  Per service: {counter_series_per_service} counter + {gauge_series_per_service} gauge"
        f" + {histogram_series_per_service} histogram = {series_per_service} series"
    )
    print(
        f"  Total across all services: {series_per_service} × {total_services} = {total_series}"
        " metric series\n"
    )

    # Set up multiple resources with their own meters
    services: list[ServiceContext] = []
    export_interval_ms = args.export_interval * 1000  # Convert seconds to milliseconds
    for app_id in range(1, args.num_apps + 1):
        for service_id in range(1, args.services_per_app + 1):
            provider, meter = setup_metrics(
                app_id,
                service_id,
                otel_endpoint,
                args.username,
                args.password,
                export_interval_ms,
                insecure=args.insecure,
            )

            # Generate static long labels for this service
            long_labels = generate_long_labels(args.num_labels, args.label_size)

            # Create multiple counter instruments for each resource
            request_counters = []
            for counter_idx in range(args.num_counters):
                counter = meter.create_counter(
                    name=f"http.requests.total.counter_{counter_idx + 1}",
                    description=f"Total number of HTTP requests for counter {counter_idx + 1}",
                    unit="1",
                )
                request_counters.append(counter)

            # Create multiple gauge instruments
            gauges = []
            for gauge_idx in range(args.num_gauges):
                gauge = meter.create_gauge(
                    name=f"system.metric.gauge_{gauge_idx + 1}",
                    description=f"System metric gauge {gauge_idx + 1}",
                    unit="%",
                )
                gauges.append(gauge)

            # Create multiple histogram instruments
            histograms = []
            for hist_idx in range(args.num_histograms):
                histogram = meter.create_histogram(
                    name=f"http.request.duration.histogram_{hist_idx + 1}",
                    description=f"HTTP request duration histogram {hist_idx + 1}",
                    unit="ms",
                )
                histograms.append(histogram)

            services.append(
                ServiceContext(
                    app_id=app_id,
                    service_id=service_id,
                    provider=provider,
                    meter=meter,
                    request_counters=request_counters,
                    gauges=gauges,
                    histograms=histograms,
                    long_labels=long_labels,
                )
            )

            print(
                f"  Initialized app-{app_id}-copy-{service_id}"
                f" (server-{app_id:02d}-{service_id:02d})"
                f" with {args.num_counters} counters, {args.num_gauges} gauges,"
                f" {args.num_histograms} histograms"
            )

    print()

    try:
        iteration = 0
        while args.iterations == 0 or iteration < args.iterations:
            iteration += 1
            print(f"[Iteration {iteration}] Generating metrics for {total_services} services...")

            # Generate metrics for each service
            for service in services:
                app_id = service.app_id
                service_id = service.service_id
                request_counters = service.request_counters
                gauges = service.gauges
                histograms = service.histograms
                long_labels = service.long_labels

                # Record counter metrics for each counter
                total_requests = 0
                for counter_idx, counter in enumerate(request_counters):
                    request_count = random.randint(10, 100)
                    counter.add(
                        request_count,
                        {
                            "method": "GET",
                            "status": "200",
                            "endpoint": f"/api/endpoint_{counter_idx + 1}",
                            **long_labels,
                        },
                    )
                    counter.add(
                        random.randint(1, 10),
                        {
                            "method": "POST",
                            "status": "201",
                            "endpoint": f"/api/endpoint_{counter_idx + 1}",
                            **long_labels,
                        },
                    )
                    counter.add(
                        random.randint(0, 5),
                        {
                            "method": "GET",
                            "status": "404",
                            "endpoint": f"/api/endpoint_{counter_idx + 1}",
                            **long_labels,
                        },
                    )
                    total_requests += request_count

                # Record gauge metrics - simulate various system metrics
                for gauge_idx, gauge in enumerate(gauges):
                    gauge_value = random.uniform(20.0, 80.0)
                    gauge.set(
                        gauge_value,
                        {
                            "core": "0",
                            "metric_type": f"type_{gauge_idx + 1}",
                            **long_labels,
                        },
                    )
                    gauge.set(
                        random.uniform(15.0, 75.0),
                        {
                            "core": "1",
                            "metric_type": f"type_{gauge_idx + 1}",
                            **long_labels,
                        },
                    )

                # Record histogram metrics - simulate request durations
                total_histogram_records = 0
                for hist_idx, histogram in enumerate(histograms):
                    num_requests = random.randint(50, 150)
                    total_histogram_records += num_requests
                    for _ in range(num_requests):
                        # Simulate normal distribution of request times (50-500ms)
                        duration = random.gauss(150, 80)
                        duration = max(10, min(1000, duration))  # Clamp between 10-1000ms
                        histogram.record(
                            duration,
                            {
                                "method": "GET",
                                "endpoint": f"/api/data_{hist_idx + 1}",
                                **long_labels,
                            },
                        )

                print(
                    f"    app-{app_id}-copy-{service_id}: {total_requests} counter requests,"
                    f" {len(gauges)} gauges, {total_histogram_records} histogram records"
                )

            print()

            # Wait only if another iteration is pending.
            if args.iterations == 0 or iteration < args.iterations:
                time.sleep(args.sleep_interval)

        print("\nCompleted requested iterations.")
        print("Metrics sent successfully!")

    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        print("Metrics sent successfully!")
    finally:
        for service in services:
            service.provider.shutdown()


if __name__ == "__main__":
    main()
