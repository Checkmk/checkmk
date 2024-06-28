#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.rest_api_client import ClientRegistry


def test_get_overview(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.get_overview("aws_quick_setup")
    assert resp.json == {
        "quick_setup_id": "aws_quick_setup",
        "overviews": [
            {
                "stage_id": 1,
                "title": "Prepare AWS for Checkmk",
                "sub_title": None,
            },
        ],
        "stage": {
            "stage_id": 1,
            "components": [],
        },
    }


def test_get_overview_non_existing_quicksetup_id(clients: ClientRegistry) -> None:
    clients.QuickSetup.get_overview("frodo", expect_ok=False).assert_status_code(404)
