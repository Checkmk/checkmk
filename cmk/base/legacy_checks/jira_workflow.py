#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<jira_workflow>>>
# {'my_project': {'in progress': 29}}


# mypy: disable-error-code="var-annotated"

import json

from cmk.base.check_api import check_levels, discover, get_parsed_item_data
from cmk.base.config import check_info


def parse_jira_workflow(info):
    parsed = {}

    for line in info:
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
                    parsed.setdefault("%s/%s" % (project.title(), workflow.title()), {}).update(
                        {workflow: issue_count}
                    )
                except KeyError:
                    pass

    return parsed


@get_parsed_item_data
def check_jira_workflow(item, params, item_data):
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


check_info["jira_workflow"] = {
    "parse_function": parse_jira_workflow,
    "check_function": check_jira_workflow,
    "discovery_function": discover(),
    "service_name": "Jira Workflow %s",
    "check_ruleset_name": "jira_workflow",
}
