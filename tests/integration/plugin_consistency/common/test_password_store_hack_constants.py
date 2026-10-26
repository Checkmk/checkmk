#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.server_side_calls_backend import load_active_checks, load_special_agents
from cmk.utils import password_store


def test_hack_apply_map_special_agents_is_complete() -> None:
    # we can't have equality, because some special agents are not present in some editions.
    assert set(password_store.hack.HACK_AGENTS) >= {
        p.name for p in load_special_agents(raise_errors=True).values()
    }


def test_hack_apply_map_active_checks_is_complete() -> None:
    assert set(password_store.hack.HACK_CHECKS) == {
        p.name for p in load_active_checks(raise_errors=True).values()
    }
