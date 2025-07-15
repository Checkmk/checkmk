#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

import pytest

from cmk.gui.views.command.commands import _acknowledgement_needs_removal
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

COMMENT_TABLE = [
    # Host comments
    {"comment_id": 11, "entry_type": 4, "is_service": 0},
    {"comment_id": 12, "entry_type": 4, "is_service": 0},
    {"comment_id": 13, "entry_type": 0, "is_service": 0},
    # Service comments
    {"comment_id": 21, "entry_type": 4, "is_service": 1},
    {"comment_id": 22, "entry_type": 4, "is_service": 1},
    {"comment_id": 23, "entry_type": 0, "is_service": 1},
]


@pytest.mark.parametrize(
    "cmdtag, comments_to_remove, removal_expected",
    [
        ("HOST", {"11"}, False),
        ("HOST", {"11", "12"}, True),
        ("HOST", {"11", "12", "13"}, True),
        ("SVC", {"21"}, False),
        ("SVC", {"21", "22"}, True),
        ("SVC", {"21", "22", "23"}, True),
    ],
)
def test_acknowledgement_needs_removal(
    request_context: None,
    mock_livestatus: MockLiveStatusConnection,
    cmdtag: Literal["HOST", "SVC"],
    comments_to_remove: set[str],
    removal_expected: bool,
) -> None:
    live = mock_livestatus
    live.add_table("comments", COMMENT_TABLE)
    live.expect_query(
        [
            "GET comments",
            "Columns: comment_id",
            "Filter: is_service = ...",
            "Filter: entry_type = 4",
            "ColumnHeaders: off",
        ],
        match_type="ellipsis",
    )
    with live():
        assert _acknowledgement_needs_removal(cmdtag, comments_to_remove) == removal_expected
