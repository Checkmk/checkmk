#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.f5_bigip.agent_based.f5_bigip_cluster import CONFIG_SYNC_DEFAULT_PARAMETERS
from cmk.plugins.f5_bigip.rulesets.f5_bigip_cluster_v11 import rule_spec_f5_bigip_cluster_v11


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def _register_form_spec_visitors() -> None:
    registration.register()


def _migrate(rule: Mapping[str, object]) -> object:
    # Migrate the rule the same way it happens during runtime.
    visitor = get_visitor(
        rule_spec_f5_bigip_cluster_v11.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    return visitor.to_disk(RawDiskData(rule))


@pytest.mark.parametrize(
    "rule, expected",
    [
        pytest.param(
            {"0": 3, "1": 0, "2": 1, "3": 0, "4": 2, "5": 2, "6": 2, "7": 1, "8": 2, "9": 2},
            {
                "unknown": 3,
                "syncing": 0,
                "need_manual_sync": 1,
                "in_sync": 0,
                "sync_failed": 2,
                "sync_disconnected": 2,
                "standalone": 2,
                "awaiting_initial_sync": 1,
                "incompatible_version": 2,
                "partial_sync": 2,
            },
            id="status codes are renamed to the status they stand for",
        ),
        pytest.param(
            {"4": 1},
            {"sync_failed": 1},
            id="a rule configuring a single status",
        ),
        pytest.param(
            {"sync_failed": 1},
            {"sync_failed": 1},
            id="migrated rule stays unchanged",
        ),
    ],
)
def test_rule_spec_f5_bigip_cluster_v11_migration(
    rule: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate(rule) == expected


def test_rule_spec_f5_bigip_cluster_v11_covers_the_check_defaults() -> None:
    """Every parameter the check reads has to be configurable."""
    assert set(rule_spec_f5_bigip_cluster_v11.parameter_form().elements) == set(
        CONFIG_SYNC_DEFAULT_PARAMETERS
    )
