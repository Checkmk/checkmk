#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.update_config.plugins.actions.warn_invalid_bi_regexes import (
    invalid_bi_regexes,
    InvalidBIRegex,
    warn_invalid_bi_regexes,
)

_INVALID = r"*.*\(?Instance001\)?.*"


def _pack(host_regex: str, service_regex: str, host_name_pattern: str) -> dict[str, object]:
    return {
        "id": "pack",
        "rules": [
            {
                "id": "rule",
                "nodes": [
                    {
                        "search": {"type": "empty"},
                        "action": {
                            "type": "state_of_service",
                            "host_regex": host_regex,
                            "service_regex": service_regex,
                        },
                    }
                ],
            }
        ],
        "aggregations": [
            {
                "id": "aggr",
                "node": {
                    "search": {
                        "type": "host_search",
                        "conditions": {
                            "host_choice": {
                                "type": "host_name_regex",
                                "pattern": host_name_pattern,
                            },
                        },
                    },
                    "action": {"type": "call_a_rule", "rule_id": "rule"},
                },
            }
        ],
    }


def test_valid_regexes_are_not_reported() -> None:
    assert not invalid_bi_regexes([_pack("$1$", r".*\(?Instance001\)?.*", "srv.*")])


def test_invalid_regexes_are_reported() -> None:
    assert [
        (hit.element, hit.field, hit.pattern)
        for hit in invalid_bi_regexes([_pack("host", _INVALID, "(")])
    ] == [
        ("rule 'rule'", "service_regex", _INVALID),
        ("aggregation 'aggr'", "host_name_regex", "("),
    ]


def test_invalid_regex_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_invalid_bi_regexes([_pack("host", _INVALID, "srv.*")], logging.getLogger("test"))

    assert "BI pack 'pack', rule 'rule'" in caplog.text
    assert f"'{_INVALID}'" in caplog.text


def test_hit_carries_regex_error() -> None:
    assert invalid_bi_regexes([_pack("(", "svc", "srv.*")]) == [
        InvalidBIRegex(
            "pack",
            "rule 'rule'",
            "host_regex",
            "(",
            "missing ), unterminated subpattern at position 0",
        )
    ]
