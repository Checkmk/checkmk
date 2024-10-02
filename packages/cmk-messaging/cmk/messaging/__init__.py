#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Library to connect to the message broker"""

from . import rabbitmq
from ._config import (
    all_cme_cacert_files,
    BrokerCertificates,
    ca_key_file,
    cacert_file,
    get_local_port,
    multisite_ca_key_file,
    multisite_cacert_file,
    multisite_cert_file,
    site_cert_file,
    site_key_file,
    TLS_PATH_CUSTOMERS,
    trusted_cas_file,
)
from ._connection import (
    Channel,
    check_remote_connection,
    CMKConnectionError,
    Connection,
    ConnectionFailed,
    ConnectionOK,
    ConnectionUnknown,
    DeliveryTag,
)

__all__ = [
    "all_cme_cacert_files",
    "BrokerCertificates",
    "cacert_file",
    "ca_key_file",
    "Channel",
    "check_remote_connection",
    "CMKConnectionError",
    "Connection",
    "ConnectionFailed",
    "ConnectionOK",
    "ConnectionUnknown",
    "DeliveryTag",
    "get_local_port",
    "multisite_cacert_file",
    "multisite_ca_key_file",
    "multisite_cert_file",
    "rabbitmq",
    "site_cert_file",
    "site_key_file",
    "TLS_PATH_CUSTOMERS",
    "trusted_cas_file",
]
