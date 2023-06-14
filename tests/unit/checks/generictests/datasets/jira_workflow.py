#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "jira_workflow"

info = [
    ['{"my_project1":', '{"in', 'progress":', "16,", '"waiting":', "56,", '"need', 'help":', "42}}"]
]

discovery = {
    "": [
        ("My_Project1/In Progress", {}),
        ("My_Project1/Need Help", {}),
        ("My_Project1/Waiting", {}),
    ]
}

checks = {
    "": [
        (
            "My_Project1/In Progress",
            {},
            [(0, "Total number of issues: 16", [("jira_count", 16, None, None, None, None)])],
        ),
        (
            "My_Project1/Need Help",
            {},
            [(0, "Total number of issues: 42", [("jira_count", 42, None, None, None, None)])],
        ),
        (
            "My_Project1/Waiting",
            {},
            [(0, "Total number of issues: 56", [("jira_count", 56, None, None, None, None)])],
        ),
    ]
}
