#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<jira_workflow>>>
# {'my_project': {'in progress': 29}}


# mypy: disable-error-code="var-annotated"

import json

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

check_info = {}


def parse_jira_workflow(string_table):
    parsed = {}

    for line in string_table:
        projects = json.loads(" ".join(line))

        for project in projects:
            workflows = projects.get(project)
            if workflows is None:
                continue

            for workflow in workflows:
                issue_count = workflows.get(workflow)
                if issue_count is None:
                    continue

                try:
                    parsed.setdefault(f"{project.title()}/{workflow.title()}", {}).update(
                        {workflow: issue_count}
                    )
                except KeyError:
                    pass

    return parsed


def check_jira_workflow(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return
    if not item_data:
        return

    msg_error = item_data.get("error")
    if msg_error is not None:
        yield 2, "Jira error while searching (see long output for details)\n%s" % msg_error
        return

    for _workflow, issue_count in item_data.items():
        issue_nr_levels = params.get("workflow_count_upper", (None, None))
        issue_nr_levels_lower = params.get("workflow_count_lower", (None, None))
        yield check_levels(
            issue_count,
            "jira_count",
            issue_nr_levels + issue_nr_levels_lower,
            human_readable_func=int,
            infoname="Total number of issues",
        )


def discover_jira_workflow(section):
    yield from ((item, {}) for item in section)


check_info["jira_workflow"] = LegacyCheckDefinition(
    name="jira_workflow",
    parse_function=parse_jira_workflow,
    service_name="Jira Workflow %s",
    discovery_function=discover_jira_workflow,
    check_function=check_jira_workflow,
    check_ruleset_name="jira_workflow",
)
