#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from tests.testlib.unit.rest_api_client import ClientRegistry


def test_list_pagetype_topics(clients: ClientRegistry) -> None:
    resp = clients.PagetypeTopicClient.get_all()
    assert resp.status_code == 200
    all_topics = resp.json["value"]
    # there must be exactly one default topic, this also ensures we have at least one topic
    assert sum(topic["extensions"]["is_default"] for topic in all_topics) == 1
