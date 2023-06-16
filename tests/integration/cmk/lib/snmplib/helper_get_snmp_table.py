#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import cmk.utils.paths
from cmk.utils.sectionname import SectionName
from cmk.utils.version import is_raw_edition

import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.type_defs import BackendSNMPTree, SNMPBackend, SNMPBackendEnum, SNMPHostConfig

from cmk.fetchers.snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

if not is_raw_edition():
    from cmk.fetchers.cee.snmp_backend.inline import (  # type: ignore[import] # pylint: disable=import-error,no-name-in-module
        InlineSNMPBackend,
    )
else:
    InlineSNMPBackend = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)

params: tuple[Mapping[str, Any], str, Mapping[str, Any], str] = ast.literal_eval(sys.stdin.read())
tree = BackendSNMPTree.from_json(params[0])
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

walk_cache: MutableMapping[str, tuple[bool, list[tuple[str, bytes]]]] = {}

print(
    repr(
        (
            snmp_table.get_snmp_table(
                section_name=SectionName("my_Section"),
                tree=tree,
                backend=backend(config, logger),
                walk_cache=walk_cache,
            ),
            walk_cache,
        )
    )
)
