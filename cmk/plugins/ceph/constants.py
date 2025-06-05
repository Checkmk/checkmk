#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final

PG_STATES: Final[frozenset[str]] = frozenset(
    {
        "activating+undersized",
        "activating+undersized+degraded",
        "active+clean",
        "active+clean+inconsistent",
        "active+clean+remapped",
        "active+clean+scrubbing",
        "active+clean+scrubbing+deep",
        "active+clean+scrubbing+deep+repair",
        "active+clean+scrubbing+deep+snaptrim_wait",
        "active+clean+snaptrim",
        "active+clean+snaptrim_wait",
        "active+clean+wait",
        "active+degraded",
        "active+recovering",
        "active+recovering+degraded",
        "active+recovering+degraded+inconsistent",
        "active+recovering+degraded+remapped",
        "active+recovering+remapped",
        "active+recovering+undersized",
        "active+recovering+undersized+degraded+remapped",
        "active+recovering+undersized+remapped",
        "active+recovery_wait",
        "active+recovery_wait+degraded",
        "active+recovery_wait+degraded+inconsistent",
        "active+recovery_wait+degraded+remapped",
        "active+recovery_wait+remapped",
        "active+recovery_wait+undersized+degraded",
        "active+recovery_wait+undersized+degraded+remapped",
        "active+recovery_wait+undersized+remapped",
        "active+remapped",
        "active+remapped+backfilling",
        "active+remapped+backfill_toofull",
        "active+remapped+backfill_wait",
        "active+remapped+backfill_wait+backfill_toofull",
        "active+remapped+inconsistent+backfilling",
        "active+remapped+inconsistent+backfill_toofull",
        "active+remapped+inconsistent+backfill_wait",
        "active+undersized",
        "active+undersized+degraded",
        "active+undersized+degraded+inconsistent",
        "active+undersized+degraded+remapped+backfilling",
        "active+undersized+degraded+remapped+backfill_toofull",
        "active+undersized+degraded+remapped+backfill_wait",
        "active+undersized+degraded+remapped+backfill_wait+backfill_toofull",
        "active+undersized+degraded+remapped+inconsistent+backfilling",
        "active+undersized+degraded+remapped+inconsistent+backfill_toofull",
        "active+undersized+degraded+remapped+inconsistent+backfill_wait",
        "active+undersized+remapped",
        "active+undersized+remapped+backfilling",
        "active+undersized+remapped+backfill_toofull",
        "active+undersized+remapped+backfill_wait",
        "down",
        "incomplete",
        "peering",
        "remapped+peering",
        "stale+active+clean",
        "stale+active+undersized",
        "stale+active+undersized+degraded",
        "stale+undersized+degraded+peered",
        "stale+undersized+peered",
        "undersized+degraded+peered",
        "undersized+peered",
        "unknown",
    }
)

PG_METRICS_MAP: Final[Mapping[str, str]] = {n: n.replace("+", "_") for n in PG_STATES}

MIB: Final[float] = 1024.0**2
