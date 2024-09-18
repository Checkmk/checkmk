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


#
# Non-CME setup central site
#
# /etc/rabbitmq/ssl
#                ├── multisite
#                │   ├── ca_cert.pem      (multisite_cacert_file)
#                │   ├── ca_key.pem       (multisite_ca_key_file)
#                │   └── <site>_cert.pem  (multisite_cert_file)
#                ├── ca_cert.pem          (cacert_file)
#                ├── cert.pem             (site_cert_file)
#                └── key.pem              (site_key_file)
#
# CME setup central site
#
# /etc/rabbitmq/ssl
#                ├── multisite
#                │   └── customers
#                │       └── <customer>
#                │           ├── ca_cert.pem      (multisite_cacert_file)
#                │           ├── ca_key.pem       (multisite_ca_key_file)
#                │           ├── <site>_cert.pem  (multisite_cert_file)
#                │           └── <site>_key.pem   (multisite_key_file)
#                ├── ca_cert.pem                  (cacert_file)
#                ├── cert.pem                     (site_cert_file)
#                └── key.pem                      (site_key_file)
#
# remote sites (both CME and Non-CME)
#
# /etc/rabbitmq/ssl
#                ├── ca_cert.pem          (cacert_file)
#                ├── cert.pem             (site_cert_file)
#                └── key.pem              (site_key_file)
#


def cacert_file(omd_root: Path) -> Path:
    """The certificate of the local message broker CA.

    In a multisite setup, this is the CA of the customer.
    """
    return omd_root.joinpath(*_TLS_PATH, "ca_cert.pem")


def ca_key_file(omd_root: Path) -> Path:
    """The certificate of the local message broker CA.

    In a multisite setup, this is the CA of the customer.
    """
    return omd_root.joinpath(*_TLS_PATH, "ca_key.pem")


def site_cert_file(omd_root: Path) -> Path:
    """Get the path of the local messaging broker certificate"""
    return omd_root.joinpath(*_TLS_PATH, "cert.pem")


def site_key_file(omd_root: Path) -> Path:
    """Get the path of the local messaging broker key"""
    return omd_root.joinpath(*_TLS_PATH, "key.pem")


def multisite_cacert_file(omd_root: Path, customer: str = "") -> Path:
    """Get the path of the messaging broker ca for a customer or the provider"""
    base_path = (
        omd_root.joinpath(*TLS_PATH_CUSTOMERS, customer)
        if customer
        else omd_root.joinpath(*_TLS_PATH_MULTISITE)
    )
    return base_path.joinpath("ca_cert.pem")


def multisite_ca_key_file(omd_root: Path, customer: str = "") -> Path:
    """Get the path of the messaging broker ca for a customer or the provider"""
    base_path = (
        omd_root.joinpath(*TLS_PATH_CUSTOMERS, customer)
        if customer
        else omd_root.joinpath(*_TLS_PATH_MULTISITE)
    )
    return base_path.joinpath("ca_key.pem")


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
    context.load_cert_chain(site_cert_file(omd_root), site_key_file(omd_root))
    return context
