#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Library to connect to the message broker"""

from . import rabbitmq
from ._config import (
    BrokerCertificates,
    ca_key_file,
    cacert_file,
    get_local_port,
    multisite_ca_key_file,
    multisite_cacert_file,
    multisite_cert_file,
    multisite_key_file,
    site_cert_file,
    site_key_file,
    TLS_PATH_CUSTOMERS,
)
from ._connection import (
    Channel,
    check_remote_connection,
    Connection,
    ConnectionFailed,
    ConnectionOK,
    ConnectionUnknown,
)

__all__ = [
    "BrokerCertificates",
    "cacert_file",
    "ca_key_file",
    "site_cert_file",
    "get_local_port",
    "site_key_file",
    "Channel",
    "Connection",
    "multisite_ca_key_file",
    "multisite_cacert_file",
    "multisite_cert_file",
    "multisite_key_file",
    "TLS_PATH_CUSTOMERS",
    "rabbitmq",
    "check_remote_connection",
    "ConnectionOK",
    "ConnectionFailed",
    "ConnectionUnknown",
]
