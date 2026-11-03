#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.server_side_programs.v1 import AgentMessages


def test_render_without_messages_is_empty() -> None:
    assert AgentMessages().render() == ""


def test_render_writes_one_row_per_message() -> None:
    messages = AgentMessages()
    messages.add_info("first")
    messages.add_warning("second")
    assert messages.render() == (
        "<<<<>>>>\n<<<cmk_agent_messages:sep(0)>>>\n"
        '{"level": "info", "message": "first"}\n'
        '{"level": "warning", "message": "second"}\n'
    )


def test_messages_keep_their_order_across_levels() -> None:
    messages = AgentMessages()
    messages.add_warning("first")
    messages.add_info("second")
    messages.add_warning("third")
    assert list(messages) == [("warning", "first"), ("info", "second"), ("warning", "third")]


@pytest.mark.parametrize("level", ["info", "warning"])
@pytest.mark.parametrize(
    "message",
    [
        "",
        "line one\nline two",
        "<<<not_a_section>>>",
        "with NUL \0 byte",
        "umlauts äöü",
    ],
)
def test_message_stays_one_row_and_round_trips(level: str, message: str) -> None:
    messages = AgentMessages()
    if level == "info":
        messages.add_info(message)
    else:
        messages.add_warning(message)
    *header, row, _ = messages.render().split("\n")
    assert len(header) == 2
    assert list(AgentMessages.from_string_table([[row]])) == [(level, message)]


@pytest.mark.parametrize(
    "row", [{"message": "first"}, {"level": "debug", "message": "first"}], ids=["none", "unknown"]
)
def test_message_without_known_level_is_a_warning(row: dict[str, str]) -> None:
    assert list(AgentMessages.from_string_table([[json.dumps(row)]])) == [("warning", "first")]


def test_from_string_table_ignores_unknown_keys() -> None:
    assert list(
        AgentMessages.from_string_table(
            [[json.dumps({"level": "info", "message": "first", "source": "api"})]]
        )
    ) == [("info", "first")]


@pytest.mark.parametrize("raw", ["not json", "[]", json.dumps({"msg": 1})])
def test_from_string_table_keeps_malformed_row_as_unreadable_warning(raw: str) -> None:
    assert list(AgentMessages.from_string_table([[raw]])) == [
        ("warning", f"Unreadable message: {raw}")
    ]


def test_unreadable_row_is_truncated() -> None:
    raw = "x" * 300
    assert list(AgentMessages.from_string_table([[raw]])) == [
        ("warning", f"Unreadable message: {raw[:200]}")
    ]
