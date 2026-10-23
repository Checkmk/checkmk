#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.plugins.proxmox_ve.rulesets.proxmox_ve_vm_info_params import _migrate_ruleset


@pytest.mark.parametrize(
    "old_params,new_params",
    [
        pytest.param(
            {"required_vm_status": "running"},
            {"required_vm_status": "running", "lock_duration": ("fixed", (900.0, 1800.0))},
            id="2.4.0 rule with required status -> default lock duration added",
        ),
        pytest.param(
            {"required_vm_status": None},
            {"required_vm_status": None, "lock_duration": ("fixed", (900.0, 1800.0))},
            id="2.4.0 rule with disabled status -> default lock duration added",
        ),
        pytest.param(
            {},
            {"lock_duration": ("fixed", (900.0, 1800.0))},
            id="2.4.0 empty rule -> default lock duration added",
        ),
        pytest.param(
            {"required_vm_status": "running", "lock_duration": ("fixed", (60.0, 120.0))},
            {"required_vm_status": "running", "lock_duration": ("fixed", (60.0, 120.0))},
            id="Custom lock duration levels -> no change",
        ),
        pytest.param(
            {"lock_duration": ("no_levels", None)},
            {"lock_duration": ("no_levels", None)},
            id="No lock duration levels -> no change",
        ),
    ],
)
def test_migrate_ruleset(
    old_params: dict[str, object],
    new_params: Mapping[str, object],
) -> None:
    assert _migrate_ruleset(old_params) == new_params


def test_migrate_ruleset_is_idempotent() -> None:
    once = _migrate_ruleset({"required_vm_status": "running"})
    assert _migrate_ruleset(dict(once)) == once
