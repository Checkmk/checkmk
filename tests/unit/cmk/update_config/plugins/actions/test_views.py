#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from unittest.mock import patch

from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.views import UpdateViews

type SimplifiedViewSpecs = dict[tuple[str, str], dict[str, object]]


def test_update_views_migrates_column_headers() -> None:
    builtin_user_id = ""
    all_views: SimplifiedViewSpecs = {
        (builtin_user_id, "builtin_view"): {"column_headers": "pergroup", "other": 0},
        ("user1", "viewA"): {"column_headers": "repeat", "other": 1},
        ("user1", "viewB"): {"column_headers": "pergroup", "other": 2},
        ("user2", "viewC"): {"column_headers": "repeat", "other": 3},
        ("user3", "viewD"): {"column_headers": "pergroup", "other": 4},
        ("user4", "viewE"): {"column_headers": "off", "other": 5},
        ("user5", "viewF"): {"other": 6},
    }
    save_calls: list[tuple[str, SimplifiedViewSpecs, str | None]] = []

    def mock_save(
        kind: str,
        views: SimplifiedViewSpecs,
        user_id: str | None = None,
    ) -> None:
        save_calls.append((kind, views, user_id))

    with (
        patch("cmk.update_config.plugins.actions.views.get_all_views", return_value=all_views),
        patch("cmk.update_config.plugins.actions.views.save", side_effect=mock_save),
        patch(
            "cmk.update_config.plugins.actions.views.UserId.builtin", return_value=builtin_user_id
        ),
    ):
        logger = logging.getLogger()
        action = UpdateViews(
            name="migrate_view_column_headers",
            title="Migrate view column_headers 'repeat' to 'pergroup'",
            sort_index=130,
            expiry_version=ExpiryVersion.CMK_300,
            continue_on_failure=True,
        )
        action(logger)

    expected_save_calls = [
        (
            "views",
            {
                ("user1", "viewA"): {"column_headers": "pergroup", "other": 1},
                ("user1", "viewB"): {"column_headers": "pergroup", "other": 2},
            },
            "user1",
        ),
        (
            "views",
            {("user2", "viewC"): {"column_headers": "pergroup", "other": 3}},
            "user2",
        ),
    ]
    assert len(save_calls) == len(expected_save_calls)

    def calls_match(
        call1: tuple[str, SimplifiedViewSpecs, str | None],
        call2: tuple[str, SimplifiedViewSpecs, str | None],
    ) -> bool:
        kind1, views1, user_id1 = call1
        kind2, views2, user_id2 = call2
        return kind1 == kind2 and user_id1 == user_id2 and views1 == views2

    for expected in expected_save_calls:
        assert any(calls_match(actual, expected) for actual in save_calls)
