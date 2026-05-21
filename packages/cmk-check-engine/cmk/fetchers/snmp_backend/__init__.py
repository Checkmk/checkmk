#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Home of our open source SNMP backends."""

import logging

from cmk.snmp_backends.classic import ClassicSNMPBackend as ClassicSNMPBackend
from cmk.snmp_backends.stored_walk import StoredWalkSNMPBackend as StoredWalkSNMPBackend
from cmk.snmplib import SNMPBackend, SNMPBackendEnum, SNMPHostConfig

InlineSNMPBackend: type[SNMPBackend] | None = None
try:
    from cmk.snmp_backends.inline import (  # type: ignore[import,no-redef,unused-ignore]
        InlineSNMPBackend,
    )
except ImportError:
    pass


def make_backend(
    snmp_config: SNMPHostConfig,
    logger: logging.Logger,
    *,
    use_cache: bool = False,
) -> SNMPBackend:
    if use_cache or snmp_config.snmp_backend is SNMPBackendEnum.STORED_WALK:
        return StoredWalkSNMPBackend(snmp_config, logger)

    if InlineSNMPBackend is not None and snmp_config.snmp_backend is SNMPBackendEnum.INLINE:
        return InlineSNMPBackend(snmp_config, logger)

    if snmp_config.snmp_backend is SNMPBackendEnum.CLASSIC:
        return ClassicSNMPBackend(snmp_config, logger)

    raise NotImplementedError(f"Unknown SNMP backend: {snmp_config.snmp_backend}")
