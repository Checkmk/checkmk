#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
import sys
from typing import Any, Mapping

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.version import edition, Edition

from cmk.snmplib import snmp_modes
from cmk.snmplib.type_defs import OID, SNMPBackend, SNMPBackendEnum, SNMPHostConfig

from cmk.fetchers.snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

if edition() is not Edition.CRE:
    from cmk.fetchers.cee.snmp_backend.inline import (  # type: ignore[import] # pylint: disable=import-error,no-name-in-module
        InlineSNMPBackend,
    )
else:
    InlineSNMPBackend = None  # type: ignore[assignment, misc]

cmk.utils.debug.enable()

logger = logging.getLogger(__name__)

params: tuple[OID, str, Mapping[str, Any], str] = ast.literal_eval(sys.stdin.read())
oid = params[0]
backend_type = SNMPBackendEnum.deserialize(params[1])
config = SNMPHostConfig.deserialize(params[2])
cmk.utils.paths.snmpwalks_dir = params[3]

backend: type[SNMPBackend]
match backend_type:
    case SNMPBackendEnum.INLINE:
        backend = InlineSNMPBackend
    case SNMPBackendEnum.CLASSIC:
        backend = ClassicSNMPBackend
    case SNMPBackendEnum.STORED_WALK:
        backend = StoredWalkSNMPBackend
    case _:
        raise ValueError(backend_type)

print(repr(snmp_modes.walk_for_export(oid, backend=backend(config, logger))))
