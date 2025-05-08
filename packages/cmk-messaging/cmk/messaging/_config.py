#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuraton values"""

import os
import ssl
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pika
from pydantic import BaseModel

from cmk.ccc.site import get_omd_config

_TLS_PATH = ("etc", "rabbitmq", "ssl")
_TLS_PATH_MULTISITE_CAS = (*_TLS_PATH, "multisite_cas")
_TLS_PATH_MULTISITE_CERTS = (*_TLS_PATH, "multisite_certs")


class BrokerCertificates(BaseModel):
    """The certificates for the messaging broker"""

    cert: bytes
    signing_ca: bytes
    additionally_trusted_ca: bytes = b""


def _omd_root() -> Path:
    return Path(os.environ["OMD_ROOT"])


def get_local_port() -> int:
    """Get the port of the local messaging broker"""
    if (port := get_omd_config(_omd_root()).get("CONFIG_RABBITMQ_PORT")) is None:
        raise RuntimeError("Could not read rabbitmq port")
    return int(port)


#
# Non-CME setup central site
#
# /etc/rabbitmq/ssl
#                ├── multisite_certs
#                │   └── <site>_cert.pem  (multisite_cert_file)
#                ├── trusted_cas.pem      (cacert_file)
#                ├── ca_cert.pem          (cacert_file)
#                ├── ca_key.pem           (ca_key_file)
#                ├── cert.pem             (site_cert_file)
#                └── key.pem              (site_key_file)
#
# CME setup central site
#
# /etc/rabbitmq/ssl
#                ├── multisite_cas
#                │   ├── <customer>_ca_cert.pem   (multisite_cacert_file)
#                │   └── <customer>_ca_key.pem    (multisite_ca_key_file)
#                ├── multisite_certs
#                │   └── <site>_cert.pem          (multisite_cert_file)
#                ├── trusted_cas.pem      (cacert_file)
#                ├── ca_cert.pem          (cacert_file)
#                ├── ca_key.pem           (ca_key_file)
#                ├── cert.pem             (site_cert_file)
#                └── key.pem                      (site_key_file)
#
# remote sites (both CME and Non-CME)
#
# /etc/rabbitmq/ssl
#                ├── trusted_cas.pem      (cacert_file)
#                ├── ca_cert.pem          (cacert_file)
#                ├── ca_key.pem           (ca_key_file)
#                ├── cert.pem             (site_cert_file)
#                └── key.pem              (site_key_file)
#


def trusted_cas_file(omd_root: Path) -> Path:
    """The trusted CAs of the local message broker"""
    return omd_root.joinpath(*_TLS_PATH, "trusted_cas.pem")


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


def all_cme_cacert_files(omd_root: Path) -> Iterator[Path]:
    """Get the path of the messaging broker ca certificate for a customer or the provider"""
    base_path = omd_root.joinpath(*_TLS_PATH_MULTISITE_CAS)
    return base_path.glob("*_ca_cert.pem")


def all_cert_files(omd_root: Path) -> Iterator[Path]:
    """Get all sites certificates files"""
    base_path = omd_root.joinpath(*_TLS_PATH_MULTISITE_CERTS)
    return base_path.glob("*_cert.pem")


def multisite_cacert_file(omd_root: Path, customer: str) -> Path:
    """Get the path of the messaging broker ca for a customer or the provider"""
    base_path = omd_root.joinpath(
        *_TLS_PATH_MULTISITE_CAS,
    )
    return base_path.joinpath(f"{customer}_ca_cert.pem")


def multisite_ca_key_file(omd_root: Path, customer: str) -> Path:
    """Get the path of the messaging broker ca for a customer or the provider"""
    base_path = omd_root.joinpath(*_TLS_PATH_MULTISITE_CAS)
    return base_path.joinpath(f"{customer}_ca_key.pem")


def multisite_cert_file(omd_root: Path, site: str) -> Path:
    """Get the path of the messaging broker certificate for a customer's site"""
    base_path = omd_root.joinpath(*_TLS_PATH_MULTISITE_CERTS)
    return base_path.joinpath(f"{site}_cert.pem")


def make_connection_params(
    omd_root: Path, server: str, port: int, omd_site: str, connection_name: str
) -> pika.ConnectionParameters:
    client_props: dict[str, str] = {"connection_name": connection_name}
    return pika.ConnectionParameters(
        host=server,
        port=port,
        ssl_options=pika.SSLOptions(_make_ssl_context(omd_root), omd_site),
        credentials=pika.credentials.ExternalCredentials(),
        heartbeat=0,
        blocked_connection_timeout=300,
        client_properties=client_props,
    )


def _make_ssl_context(omd_root: Path) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=trusted_cas_file(omd_root))
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(site_cert_file(omd_root), site_key_file(omd_root))
    return context


def clear_brokers_certs_cache() -> None:
    subprocess.check_output(["rabbitmqctl", "eval", "ssl:clear_pem_cache()."])


def get_cert_info() -> dict[Path, str]:
    "Get certificates information for the certificate overview page"

    certs = {
        cacert_file(_omd_root()): "Local message broker CA",
        site_cert_file(_omd_root()): "Local message broker certificate",
    }

    certs.update(
        {
            path: f"Multisite message broker certificate for site '{path.stem.removesuffix('_cert')}'"
            for path in all_cert_files(_omd_root())
        }
    )
    certs.update(
        {
            path: f"Multisite message broker CA certificate for customer '{path.stem.removesuffix('_ca_cert')}'"
            for path in all_cme_cacert_files(_omd_root())
        }
    )

    return certs
