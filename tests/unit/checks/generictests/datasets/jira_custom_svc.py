#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "jira_custom_svc"

info = [
    [
        '{"Custom',
        'Service":',
        '{"error":',
        '"Jira',
        "error",
        "400:",
        "Error",
        "in",
        "the",
        "JQL",
        "Query:",
        "'for'",
        "is",
        "a",
        "reserved",
        "JQL",
        "word.",
        "You",
        "must",
        "surround",
        "it",
        "in",
        "quotation",
        "marks",
        "to",
        "use",
        "it",
        "in",
        "a",
        "query.",
        "(line",
        "1,",
        "character",
        '40)"}}',
    ],
    [
        '{"Custom',
        'error":',
        '{"error":',
        '"Jira',
        "error",
        "400:",
        "Error",
        "in",
        "the",
        "JQL",
        "Query:",
        "Expecting",
        "operator",
        "but",
        "got",
        "'closed'.",
        "The",
        "valid",
        "operators",
        "are",
        "'=',",
        "'!=',",
        "'<',",
        "'>',",
        "'<=',",
        "'>=',",
        "'~',",
        "'!~',",
        "'IN',",
        "'NOT",
        "IN',",
        "'IS'",
        "and",
        "'IS",
        "NOT'.",
        "(line",
        "1,",
        "character",
        '30)"}}',
    ],
    [
        '{"Jira',
        "custom",
        '2":',
        '{"count":',
        "414},",
        '"Custom',
        'avg":',
        '{"avg_sum":',
        "37.0,",
        '"avg_total":',
        "50,",
        '"avg":',
        '"0.74"},',
        '"Custom',
        'sum":',
        '{"sum":',
        "37.0}}",
    ],
]

discovery = {
    "": [
        ("Custom Avg", {}),
        ("Custom Error", {}),
        ("Custom Service", {}),
        ("Custom Sum", {}),
        ("Jira Custom 2", {}),
    ]
}

checks = {
    "": [
        (
            "Custom Avg",
            {},
            [
                (0, "Average value: 0.74", [("jira_avg", 0.74, None, None, None, None)]),
                (0, "(Summed up values: 37.0 / Total search results: 50)", []),
            ],
        ),
        (
            "Custom Error",
            {},
            [
                (
                    2,
                    "Jira error while searching (see long output for details)\nJira error 400: Error in the JQL Query: Expecting operator but got 'closed'. The valid operators are '=', '!=', '<', '>', '<=', '>=', '~', '!~', 'IN', 'NOT IN', 'IS' and 'IS NOT'. (line 1, character 30)",
                    [],
                )
            ],
        ),
        (
            "Custom Service",
            {},
            [
                (
                    2,
                    "Jira error while searching (see long output for details)\nJira error 400: Error in the JQL Query: 'for' is a reserved JQL word. You must surround it in quotation marks to use it in a query. (line 1, character 40)",
                    [],
                )
            ],
        ),
        (
            "Custom Sum",
            {},
            [
                (0, "Result of summed up values: 37", [("jira_sum", 37.0, None, None, None, None)]),
                (
                    0,
                    "Difference last 7 days 0 hours: 0.00",
                    [("jira_diff", 0, None, None, None, None)],
                ),
            ],
        ),
        (
            "Jira Custom 2",
            {},
            [
                (0, "Total number of issues: 414", [("jira_count", 414, None, None, None, None)]),
                (
                    0,
                    "Difference last 7 days 0 hours: 0.00",
                    [("jira_diff", 0, None, None, None, None)],
                ),
            ],
        ),
    ]
}
