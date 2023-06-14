#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "jira_workflow"

info = [
    [
        '{"support',
        'and":',
        '{"error":',
        '"Jira',
        "error",
        "400:",
        "The",
        "value",
        "'support",
        "and'",
        "does",
        "not",
        "exist",
        "for",
        "the",
        "field",
        "'project'.\"}}",
    ],
    ['{"checkmk":', '{"in', 'review":', "16}}"],
]

discovery = {"": [("Checkmk/In Review", {}), ("Support And/Error", {})]}

checks = {
    "": [
        (
            "Checkmk/In Review",
            {},
            [(0, "Total number of issues: 16", [("jira_count", 16, None, None, None, None)])],
        ),
        (
            "Support And/Error",
            {},
            [
                (
                    2,
                    "Jira error while searching (see long output for details)\nJira error 400: The value 'support and' does not exist for the field 'project'.",
                    [],
                )
            ],
        ),
    ]
}
