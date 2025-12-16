#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping

import pytest

from cmk.gui.plugins.wato.check_parameters.mq_queues import _migrate_mq_queue_consumer_count_levels


@pytest.mark.parametrize(
    "inp, expected",
    [
        # upper levels
        (
            {"consumerCount": (10, 20), "size": (5, 6)},
            {
                "consumer_count_levels_upper": (10, 20),
                "size": (5, 6),
            },
        ),
        # lower levels
        (
            {"consumerCount": (10, 5), "size": (5, 6)},
            {
                "consumer_count_levels_lower": (10, 5),
                "size": (5, 6),
            },
        ),
        # equal values → lower (current behavior)
        (
            {"consumerCount": (10, 10), "size": (5, 6)},
            {
                "consumer_count_levels_lower": (10, 10),
                "size": (5, 6),
            },
        ),
        # no consumerCount → passthrough
        (
            {"size": (5, 6)},
            {"size": (5, 6)},
        ),
        # already migrated
        (
            {
                "size": (0, 0),
                "consumer_count_levels_upper": (10, 20),
                "consumer_count_levels_lower": (10, 5),
            },
            {
                "size": (0, 0),
                "consumer_count_levels_upper": (10, 20),
                "consumer_count_levels_lower": (10, 5),
            },
        ),
        (
            {"consumerCount": (1, 2)},
            {
                "consumer_count_levels_upper": (1, 2),
            },
        ),
    ],
)
def test_migrate_mq_queue_consumer_count_levels(
    inp: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate_mq_queue_consumer_count_levels(inp) == expected
