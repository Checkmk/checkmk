#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Home of our open source SNMP backends."""

import importlib
import inspect
import logging
import pkgutil
from collections.abc import Mapping

import cmk.checkengine.snmp_backends
from cmk.checkengine.snmplib import SNMPBackend, SNMPBackendEnum, SNMPHostConfig


def discover_backends() -> Mapping[SNMPBackendEnum, type[SNMPBackend]]:
    """Find every concrete `SNMPBackend` subclass exposed by `cmk.snmp_backends.*`.

    Backends register themselves by living in a submodule of the namespace package
    `cmk.snmp_backends` and exposing a concrete `SNMPBackend` subclass (typically
    via the submodule's `__init__.py`). Each backend identifies itself through its
    static `get_type()` method, which is also the dispatch key used by
    `make_backend`.
    """
    backends: dict[SNMPBackendEnum, type[SNMPBackend]] = {}
    for mod_info in pkgutil.iter_modules(
        cmk.checkengine.snmp_backends.__path__, f"{cmk.checkengine.snmp_backends.__name__}."
    ):
        if mod_info.name.rsplit(".", 1)[-1].startswith("_"):
            # Private submodules are expected to not expose a backend!
            continue
        try:
            module = importlib.import_module(mod_info.name)
        except ImportError:
            continue
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, SNMPBackend)
                and value is not SNMPBackend
                and not inspect.isabstract(value)
            ):
                backends[value.get_type()] = value
    return backends


# TODO: Remove global variable so that BackendError can be moved into this file
_BACKENDS: Mapping[SNMPBackendEnum, type[SNMPBackend]] = discover_backends()


def make_backend(
    snmp_config: SNMPHostConfig,
    logger: logging.Logger,
    *,
    use_cache: bool = False,
) -> SNMPBackend:
    # Apparently, this could be a thing.
    assert isinstance(snmp_config.snmp_backend, SNMPBackendEnum), "Unknown SNMP backend"
    backend_type = SNMPBackendEnum.STORED_WALK if use_cache else snmp_config.snmp_backend
    try:
        backend_cls = _BACKENDS[backend_type]
    except KeyError:
        logger.exception(
            "Unknown SNMP backend: %s. Using CLASSIC backend as fallback", backend_type
        )
        backend_cls = _BACKENDS[SNMPBackendEnum.CLASSIC]
    return backend_cls(snmp_config, logger)
