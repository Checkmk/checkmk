#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Home of our open source SNMP backends."""

from collections.abc import Mapping

import cmk.checkengine.snmp_backends
from cmk.checkengine.snmp_backends._utils import BackendError
from cmk.checkengine.snmplib import SNMPBackend, SNMPBackendEnum, SNMPHostConfig
from cmk.checkengine.subclass_discovery import discover

__all__ = ["BackendError", "discover_backends", "make_backend"]


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
    """Create the configured backend.

    We do not fall back to a different backend: either we monitor the way
    the user configured it, or we fail.
    """
    backend_type = SNMPBackendEnum.STORED_WALK if use_cache else snmp_config.snmp_backend
    try:
        backend_cls = discover_backends()[backend_type]
    except KeyError as exc:
        raise BackendError(
            f"The {backend_type.value!r} SNMP backend is not available in this installation"
        ) from exc
    return backend_cls(snmp_config)
