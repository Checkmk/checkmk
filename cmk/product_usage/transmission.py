#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ipaddress
import json
import logging
import os
import re
import socket
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from urllib.parse import urlparse

import requests

from cmk.product_usage.collectors.grafana import remove_grafana_usage_data
from cmk.product_usage.exceptions import EndpointUnreachableError, InvalidProductUsageEndpointError
from cmk.utils.http_proxy_config import EnvironmentProxyConfig, HTTPProxyConfig

DEFAULT_PROXY = EnvironmentProxyConfig()


def resolve_host(host: str) -> Sequence[str]:
    return sorted(
        {str(info[4][0]) for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    )


def transmit_data(
    var_dir: Path,
    logger: logging.Logger,
    proxy_config: HTTPProxyConfig = DEFAULT_PROXY,
    resolve: Callable[[str], Sequence[str]] = resolve_host,
) -> None:
    """Send the stored files, oldest first

    Raises EndpointUnreachableError if the endpoint can not be reached. The remaining files are
    kept for the next run then."""
    logger.info("Data transmission starts")

    directory = var_dir / "product_usage"

    # Ignored mypy error: it only checks filenames that already match the pattern, so it will never call group() on None
    files = sorted(
        directory.glob("product_usage_[0-9]*.json"),
        key=lambda f: int(re.search(r"product_usage_(\d+)\.json", f.name).group(1)),  # type: ignore[union-attr]
    )

    transmission_results: dict[str, bool] = {}
    for file_path in files:
        try:
            successful_response = _transmit_single_file(file_path, proxy_config, logger)
        except (requests.ConnectionError, requests.Timeout) as e:
            raise EndpointUnreachableError(
                _unreachable_message(_get_api_url(), e, proxy_config.to_requests_proxies(), resolve)
            ) from e
        transmission_results[file_path.name] = successful_response
        if successful_response:
            file_path.unlink()

    # Earlier we sorted the files ascending, so the newest is the last one.
    # Now we check if the last file was transmitted successfully to decide whether to delete grafana usage data.
    if files:
        newest_file = files[-1]
        if transmission_results.get(newest_file.name):
            logger.info("Removing Grafana usage data")
            remove_grafana_usage_data(var_dir)


def _transmit_single_file(
    file_path: Path, proxy_config: HTTPProxyConfig, logger: logging.Logger
) -> bool:
    logger.info("Tansmitting %s", file_path)

    with file_path.open("r", encoding="utf-8") as f:
        json_data = json.load(f)

    response = requests.post(
        _get_api_url(),
        json=json_data,
        timeout=30,
        proxies=proxy_config.to_requests_proxies(),
    )

    if not response.ok:
        logger.error("Error during transmission: status %s %s", response.status_code, response.text)

    return response.ok


def _unreachable_message(
    url: str,
    error: requests.RequestException,
    proxies: Mapping[str, str] | None,
    resolve: Callable[[str], Sequence[str]],
) -> str:
    host = urlparse(url).hostname or url
    message = f"Could not connect to {host} ({_root_cause(error)})"
    retry = "The data is sent with the next run."
    if _uses_proxy(url, proxies):
        return f"{message} via the configured proxy. {retry}"

    # A DNS block list (Pi-hole, AdGuard, ...) answers with 0.0.0.0, which some resolvers turn
    # into 127.0.0.1. The connection then ends at a local web server and fails with a
    # certificate error that does not point to the cause.
    try:
        addresses = resolve(host)
    except OSError:
        return f"{message}: the host name can not be resolved. {retry}"
    if addresses and all(_is_blocked_address(address) for address in addresses):
        return (
            f"{message}: it resolves to {', '.join(addresses)}, so a DNS block list probably"
            f" blocks it. Allow {host} in your DNS filter to send product usage analytics."
            f" {retry}"
        )
    return f"{message}. {retry}"


def _root_cause(error: BaseException) -> str:
    """The innermost error of the chain requests and urllib3 wrap around it

    The text of the outer errors repeats the inner ones, for example
    "HTTPSConnectionPool(...): Max retries exceeded with url: /upload (Caused by SSLError(...))".
    """
    cause = error
    while (inner := _inner_error(cause)) is not None:
        cause = inner
    return str(cause) or type(cause).__name__


def _inner_error(error: BaseException) -> BaseException | None:
    # urllib3's MaxRetryError keeps the failed attempt in "reason", requests and urllib3 pass
    # the wrapped error as the first argument.
    for candidate in (getattr(error, "reason", None), *error.args[:1], error.__cause__):
        if isinstance(candidate, BaseException) and candidate is not error:
            return candidate
    return None


def _uses_proxy(url: str, proxies: Mapping[str, str] | None) -> bool:
    if proxies is None:
        proxies = requests.utils.get_environ_proxies(url)
    return bool(requests.utils.select_proxy(url, dict(proxies)))


def _is_blocked_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_unspecified


def _get_api_url() -> str:
    domain = os.environ.get("CMK_PRODUCT_USAGE_URL", "https://analytics.checkmk.com/upload")
    parsed = urlparse(domain)
    if parsed.scheme != "https" or not parsed.netloc:
        raise InvalidProductUsageEndpointError
    return domain
