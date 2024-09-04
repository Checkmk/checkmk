#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuraton values"""

import ssl
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import pika
from pydantic import BaseModel

if TYPE_CHECKING:
    F = TypeVar("F", bound=Callable[[], int])

    def lru_cache(_f: F) -> F: ...

else:
    from functools import lru_cache


_TLS_PATH = ("etc", "rabbitmq", "ssl")
_TLS_PATH_MULTISITE = (*_TLS_PATH, "multisite")
TLS_PATH_CUSTOMERS = (*_TLS_PATH_MULTISITE, "customers")


class BrokerCertificates(BaseModel):
    """The certificates for the messaging broker"""

    key: bytes
    cert: bytes
    central_ca: bytes
    customer_ca: bytes | None = None


@lru_cache
def get_local_port() -> int:
    """Get the port of the local messaging broker"""
    return int(subprocess.check_output(["omd", "config", "show", "RABBITMQ_PORT"]))


def cacert_file(omd_root: Path) -> Path:
    """Get the path of the local messaging broker ca"""
    return omd_root.joinpath(*_TLS_PATH, "ca.pem")


def cert_file(omd_root: Path) -> Path:
    """Get the path of the local messaging broker certificate"""
    return omd_root.joinpath(*_TLS_PATH, "cert.pem")


def key_file(omd_root: Path) -> Path:
    """Get the path of the local messaging broker key"""
    return omd_root.joinpath(*_TLS_PATH, "key.pem")


def multisite_cacert_file(omd_root: Path, customer: str = "") -> Path:
    """Get the path of the messaging broker ca for a customer"""
    base_path = (
        omd_root.joinpath(*TLS_PATH_CUSTOMERS, customer)
        if customer
        else omd_root.joinpath(*_TLS_PATH_MULTISITE)
    )
    return base_path.joinpath("ca.pem")


def multisite_cert_file(omd_root: Path, site: str, customer: str = "") -> Path:
    """Get the path of the messaging broker certificate for a customer's site"""
    base_path = (
        omd_root.joinpath(*TLS_PATH_CUSTOMERS, customer)
        if customer
        else omd_root.joinpath(*_TLS_PATH_MULTISITE)
    )
    return base_path.joinpath(f"{site}_cert.pem")


def multisite_key_file(omd_root: Path, site: str, customer: str = "") -> Path:
    """Get the path of the local messaging broker key"""
    base_path = (
        omd_root.joinpath(*TLS_PATH_CUSTOMERS, customer)
        if customer
        else omd_root.joinpath(*_TLS_PATH_MULTISITE)
    )
    return base_path.joinpath(f"{site}_key.pem")


def make_connection_params(omd_root: Path, server: str, port: int) -> pika.ConnectionParameters:
    return pika.ConnectionParameters(
        host=server,
        port=port,
        ssl_options=pika.SSLOptions(_make_ssl_context(omd_root)),
        credentials=pika.credentials.ExternalCredentials(),
        heartbeat=0,
        blocked_connection_timeout=300,
    )


def _make_ssl_context(omd_root: Path) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=cacert_file(omd_root))
    context.check_hostname = False  # the host name in the cert is the site name, not the server.
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(cert_file(omd_root), key_file(omd_root))
    return context
