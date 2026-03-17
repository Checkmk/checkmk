#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.autocompleters import monitored_service_description_autocompleter
from cmk.gui.config import Config
from cmk.livestatus_client.testing import MockLiveStatusConnection


def test_literal_search_escapes_special_regex_chars(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    """Service names with special regex chars must be escaped when literal_search=True.

    Without escaping, "Errors (HTTP)" produces the ERE pattern "Errors (HTTP)" where
    "(HTTP)" is a capture group, matching "Errors HTTP" but not "Errors (HTTP)".
    With literal_search=True the value is re.escaped so parentheses are treated literally.
    """
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.expect_query(
        "GET services\nColumns: service_description\n"
        r"Filter: service_description ~~ Errors\ \(HTTP\)"
        "\nColumnHeaders: off\nLimit: 201\n"
    )

    with mock_livestatus(expect_status_query=True):
        monitored_service_description_autocompleter(
            load_config,
            "Errors (HTTP)",
            {"strict": True, "literal_search": True, "context": {}},
        )


def test_without_literal_search_value_is_used_as_regex(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    """Without literal_search the value is forwarded as-is, preserving regex search behaviour."""
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.expect_query(
        "GET services\nColumns: service_description\n"
        "Filter: service_description ~~ http.*err"
        "\nColumnHeaders: off\nLimit: 201\n"
    )

    with mock_livestatus(expect_status_query=True):
        monitored_service_description_autocompleter(
            load_config,
            "http.*err",
            {"strict": True, "context": {}},
        )
