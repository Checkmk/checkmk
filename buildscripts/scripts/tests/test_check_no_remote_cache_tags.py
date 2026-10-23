#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from check_no_remote_cache_tags import find_problems, parse_rules, Rule

TAGGED = frozenset({"no-remote-cache"})


def _rule(
    label: str,
    rule_class: str = "pkg_tar_impl",
    *,
    stamp: int = 0,
    tags: frozenset[str] = frozenset(),
    inputs: frozenset[str] = frozenset(),
) -> Rule:
    return Rule(label=label, rule_class=rule_class, stamp=stamp, tags=tags, inputs=inputs)


def test_tagged_stamped_rule_and_consumer_pass() -> None:
    rules = [
        _rule("//a:stamped", stamp=1, tags=TAGGED),
        _rule("//a:deb", "pkg_deb", tags=TAGGED, inputs=frozenset({"//a:stamped"})),
    ]

    assert not find_problems(rules)


def test_untagged_stamped_rule_is_reported() -> None:
    problems = find_problems([_rule("//a:stamped", stamp=1)])

    assert problems == ["//a:stamped (pkg_tar_impl): stamp = 1, but is not tagged no-remote-cache"]


def test_untagged_consumer_of_stamped_output_is_reported() -> None:
    rules = [
        _rule("//a:stamped", stamp=1, tags=TAGGED),
        _rule("//a:deb", "pkg_deb", inputs=frozenset({"//a:stamped"})),
    ]

    assert find_problems(rules) == [
        "//a:deb (pkg_deb): consumes //a:stamped, but is not tagged no-remote-cache"
    ]


def test_consumer_behind_pass_through_rule_is_reported() -> None:
    rules = [
        _rule("//a:stamped", stamp=1, tags=TAGGED),
        _rule("//a:files", "pkg_files", inputs=frozenset({"//a:stamped"})),
        _rule("//a:tar", inputs=frozenset({"//a:files"})),
    ]

    assert find_problems(rules) == [
        "//a:tar (pkg_tar_impl): consumes //a:files, but is not tagged no-remote-cache"
    ]


def test_exempt_rule_reading_only_providers_is_not_reported() -> None:
    rules = [
        _rule("//a:stamped", stamp=1, tags=TAGGED),
        _rule("//a:sbom", "sbom", inputs=frozenset({"//a:stamped"})),
    ]

    assert not find_problems(rules)


def test_unstamped_rules_need_no_tag() -> None:
    rules = [
        _rule("//a:tar"),
        _rule("//a:deb", "pkg_deb", inputs=frozenset({"//a:tar"})),
    ]

    assert not find_problems(rules)


def test_query_output_is_parsed_into_rules() -> None:
    lines = [
        json.dumps(
            {
                "type": "RULE",
                "rule": {
                    "name": "//a:stamped",
                    "ruleClass": "pkg_tar_impl",
                    "attribute": [
                        {"name": "stamp", "type": "INTEGER", "intValue": 1},
                        {"name": "tags", "type": "STRING_LIST", "stringListValue": ["manual"]},
                    ],
                    "ruleInput": ["//a:files"],
                },
            }
        ),
        json.dumps({"type": "SOURCE_FILE", "sourceFile": {"name": "//a:BUILD"}}),
    ]

    assert parse_rules(lines) == [
        _rule(
            "//a:stamped",
            stamp=1,
            tags=frozenset({"manual"}),
            inputs=frozenset({"//a:files"}),
        )
    ]
