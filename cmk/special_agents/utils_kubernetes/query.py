#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow-any-unimported
# mypy: disallow-any-decorated
# mypy: disallow-any-explicit
# mypy: disallow-any-generics
# mypy: disallow-subclassing-any
# mypy: warn-return-any

import argparse
import enum
import logging
from typing import Mapping, NewType

import requests
import urllib3
from pydantic import BaseModel

from cmk.utils.http_proxy_config import deserialize_http_proxy_config

TCPTimeout = NewType("TCPTimeout", tuple[int, int])


class CollectorPath(str, enum.Enum):
    metadata = "/metadata"
    container_metrics = "/container_metrics"
    machine_sections = "/machine_sections"


class NoUsageConfig(BaseModel):
    token: str

    class Config:
        allow_mutable = False


class SessionConfig(NoUsageConfig):
    cluster_collector_proxy: str
    cluster_collector_read_timeout: int
    cluster_collector_connect_timeout: int
    verify_cert_collector: bool

    def requests_timeout(self) -> TCPTimeout:
        return TCPTimeout(
            (self.cluster_collector_connect_timeout, self.cluster_collector_read_timeout)
        )

    def requests_proxies(self) -> Mapping[str, str]:
        return (
            deserialize_http_proxy_config(self.cluster_collector_proxy).to_requests_proxies() or {}
        )


class CollectorSessionConfig(SessionConfig):
    cluster_collector_endpoint: str


def create_session(config: SessionConfig, logger: logging.Logger) -> requests.Session:
    if not config.verify_cert_collector:
        logger.warning("Disabling SSL certificate verification.")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.proxies.update(config.requests_proxies())
    session.headers.update(
        {} if config.token is None else {"Authorization": f"Bearer {config.token}"}
    )
    return session


def parse_session_config(
    arguments: argparse.Namespace,
) -> CollectorSessionConfig | NoUsageConfig:
    class _AllConfigs(BaseModel):
        config: CollectorSessionConfig | NoUsageConfig

    return _AllConfigs.parse_obj(arguments.__dict__).config
