#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
import sys
from collections.abc import Callable, Mapping
from functools import partial
from pathlib import Path
from typing import Any

from cmk.ccc.version import Edition, edition

import cmk.utils.paths
from cmk.utils.sectionname import SectionName

from cmk.snmplib import (
    BackendSNMPTree,
    get_snmp_table,
    SNMPBackend,
    SNMPBackendEnum,
    SNMPHostConfig,
)

from cmk.fetchers.snmp_backend import (  # pylint: disable=cmk-module-layer-violation
    ClassicSNMPBackend,
    StoredWalkSNMPBackend,
)

if edition(cmk.utils.paths.omd_root) is not Edition.CRE:
    from cmk.fetchers.cee.snmp_backend.inline import (  # type: ignore[import,unused-ignore] # pylint: disable=cmk-module-layer-violation
        InlineSNMPBackend,
    )
else:
    InlineSNMPBackend = None  # type: ignore[assignment, misc, unused-ignore]

logger = logging.getLogger(__name__)

params: tuple[Mapping[str, Any], str, Mapping[str, Any], str] = ast.literal_eval(sys.stdin.read())
tree = BackendSNMPTree.from_json(params[0])
backend_type = SNMPBackendEnum.deserialize(params[1])
config = SNMPHostConfig.deserialize(params[2])
cmk.utils.paths.snmpwalks_dir = Path(params[3])

backend: Callable[[SNMPHostConfig, logging.Logger], SNMPBackend]
match backend_type:
    case SNMPBackendEnum.INLINE:
        backend = InlineSNMPBackend
    case SNMPBackendEnum.CLASSIC:
        backend = ClassicSNMPBackend
    case SNMPBackendEnum.STORED_WALK:
        backend = partial(
            StoredWalkSNMPBackend, path=cmk.utils.paths.snmpwalks_dir / config.hostname
        )
    case _:
        raise ValueError(backend_type)

walk_cache: dict[tuple[str, str, bool], list[tuple[str, bytes]]] = {}

sys.stdout.write(
    repr(
        (
            get_snmp_table(
                section_name=SectionName("my_Section"),
                tree=tree,
                backend=backend(config, logger),
                walk_cache=walk_cache,
                log=logger.debug,
            ),
            walk_cache,
        )
    )
    + "\n"
)
