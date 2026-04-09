#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

import logging
from pathlib import Path
from types import ModuleType

from cmk.snmplib import (
    SNMPBackend,
    SNMPBackendEnum,
    SNMPHostConfig,
)

from .snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

inline: ModuleType | None
try:
    from cmk.inline_snmp import inline  # type: ignore[import,no-redef,unused-ignore]
except ImportError:
    inline = None


__all__ = ["make_backend"]


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
        return inline.InlineSNMPBackend(snmp_config, logger)

    if snmp_config.snmp_backend is SNMPBackendEnum.CLASSIC:
        return ClassicSNMPBackend(snmp_config, logger)

    raise NotImplementedError(f"Unknown SNMP backend: {snmp_config.snmp_backend}")
