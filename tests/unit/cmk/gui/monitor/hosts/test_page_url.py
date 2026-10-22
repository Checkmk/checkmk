#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import ValidationError
from werkzeug.test import create_environ

from cmk.gui.http import Request
from cmk.gui.monitor.hosts._api._filters import AndNode, StringCondition
from cmk.gui.monitor.hosts.page_url import all_hosts_url


def test_without_filter_or_search_is_the_plain_page() -> None:
    assert all_hosts_url(Request(create_environ())) == "monitor_all_hosts.py"


def test_search_text_goes_to_the_search_box() -> None:
    url = all_hosts_url(Request(create_environ()), search="web*")
    assert url == "monitor_all_hosts.py?q=web%2A"


def test_filter_is_the_json_tree_the_frontend_codec_parses() -> None:
    # filterState/codec.ts decodes the variable with JSON.parse and expects the tree's own shape.
    node = AndNode(
        type="and",
        children=[
            StringCondition(type="condition", field="name", op="contains", value="web"),
            StringCondition(type="condition", field="address", op="contains", value="10."),
        ],
    )

    parts = urlsplit(all_hosts_url(Request(create_environ()), filter_node=node))

    assert parts.path == "monitor_all_hosts.py"
    assert {name: json.loads(value) for name, [value] in parse_qs(parts.query).items()} == {
        "filter": {
            "type": "and",
            "children": [
                {"type": "condition", "field": "name", "op": "contains", "value": "web"},
                {"type": "condition", "field": "address", "op": "contains", "value": "10."},
            ],
        }
    }


def test_filter_the_page_would_reject_is_refused() -> None:
    node = StringCondition(type="condition", field="name", op="contains", value="web\nserver")

    with pytest.raises(ValidationError):
        all_hosts_url(Request(create_environ()), filter_node=node)
