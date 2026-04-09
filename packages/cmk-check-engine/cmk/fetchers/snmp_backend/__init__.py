#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Home of our open source SNMP backends."""

import logging
from pathlib import Path
from types import ModuleType

from cmk.snmplib import SNMPBackend, SNMPBackendEnum, SNMPHostConfig

from .classic import ClassicSNMPBackend as ClassicSNMPBackend
from .stored_walk import StoredWalkSNMPBackend as StoredWalkSNMPBackend

inline: ModuleType | None = None
try:
    from cmk.inline_snmp import inline  # type: ignore[import,no-redef,unused-ignore]
except ImportError:
    pass


def make_backend(
    snmp_config: SNMPHostConfig,
    logger: logging.Logger,
    *,
    use_cache: bool = False,
    stored_walk_path: Path,
) -> SNMPBackend:
    if use_cache or snmp_config.snmp_backend is SNMPBackendEnum.STORED_WALK:
        return StoredWalkSNMPBackend(
            snmp_config, logger, path=stored_walk_path / snmp_config.hostname
        )

    if inline and snmp_config.snmp_backend is SNMPBackendEnum.INLINE:
        return inline.InlineSNMPBackend(snmp_config, logger)  # type: ignore[no-any-return]  # TODO: CMK-32980

    if snmp_config.snmp_backend is SNMPBackendEnum.CLASSIC:
        return ClassicSNMPBackend(snmp_config, logger)

    raise NotImplementedError(f"Unknown SNMP backend: {snmp_config.snmp_backend}")
