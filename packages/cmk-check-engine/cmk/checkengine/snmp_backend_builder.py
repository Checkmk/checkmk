#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Home of our open source SNMP backends."""

import logging
from collections.abc import Mapping

import cmk.checkengine.snmp_backends
from cmk.checkengine.snmplib import SNMPBackend, SNMPBackendEnum, SNMPHostConfig
from cmk.checkengine.subclass_discovery import discover

logger = logging.getLogger(__name__)


def discover_backends() -> Mapping[SNMPBackendEnum, type[SNMPBackend]]:
    """Find every concrete `SNMPBackend` subclass exposed by `cmk.snmp_backends.*`.

    Backends register themselves by living in a submodule of the namespace package
    `cmk.snmp_backends` and exposing a concrete `SNMPBackend` subclass (typically
    via the submodule's `__init__.py`). Each backend identifies itself through its
    static `get_type()` method, which is also the dispatch key used by
    `make_backend`.
    """
    return discover(cmk.checkengine.snmp_backends, SNMPBackend, lambda backend: backend.get_type())


def make_backend(
    snmp_config: SNMPHostConfig,
    *,
    use_cache: bool = False,
) -> SNMPBackend:
    backend_type = SNMPBackendEnum.STORED_WALK if use_cache else snmp_config.snmp_backend
    backends = discover_backends()
    try:
        backend_cls = backends[backend_type]
    except KeyError:
        logger.exception(
            "Unknown SNMP backend: %(backend_type)s. Using CLASSIC backend as fallback",
            {"backend_type": backend_type},
        )
        backend_cls = backends[SNMPBackendEnum.CLASSIC]
    return backend_cls(snmp_config)
