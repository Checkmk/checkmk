#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    RulespecGroupDatasourceProgramsApps,
    validate_aws_tags,
)
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    Integer,
    ListOf,
    ListOfStrings,
    TextInput,
    Tuple,
)


def _factory_default_special_agents_jira():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _vs_jira_projects(title):
    return ListOf(
        valuespec=Tuple(
            orientation="horizontal",
            elements=[
                TextInput(
                    title=_("Project"),
                    help=_(
                        "Enter the full name of the "
                        "project here. You can find "
                        "the name in Jira within "
                        '"Projects" - "View all '
                        'projects" - column: "Project". '
                        "This field is case "
                        "insensitive"
                    ),
                    allow_empty=False,
                    regex="^[^']*$",
                    regex_error=_("Single quotes are not allowed here."),
                ),
                ListOfStrings(
                    title=_("Workflows"),
                    help=_('Enter the workflow name for the project here. E.g. "in progress".'),
                    valuespec=TextInput(
                        allow_empty=False,
                        regex="^[^']*$",
                        regex_error=_("Single quotes are not allowed here."),
                    ),
                    orientation="horizontal",
                ),
            ],
        ),
        add_label=_("Add new project"),
        movable=False,
        title=title,
        validate=validate_aws_tags,
    )


def _valuespec_special_agents_jira():
    return Dictionary(
        title=_("Jira statistics"),
        help=_("Use Jira Query Language (JQL) to get statistics out of your " "Jira instance."),
        elements=[
            (
                "instance",
                TextInput(
                    title=_("Jira instance to query"),
                    help=_(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_jira.com. If not set, the "
                        "assigned host is used as instance."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "user",
                TextInput(
                    title=_("Username"),
                    help=_("The username that should be used for accessing the " "Jira API."),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "password",
                PasswordFromStore(
                    title=_("Password of the user"),
                    allow_empty=False,
                ),
            ),
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                    default_value="https",
                ),
            ),
            (
                "project_workflows",
                _vs_jira_projects(
                    _(
                        "Monitor the number of issues for given projects and their "
                        "workflows. This results in a service for each project with "
                        "the number of issues per workflow."
                    ),
                ),
            ),
            (
                "jql",
                ListOf(
                    valuespec=Dictionary(
                        elements=[
                            (
                                "service_description",
                                TextInput(
                                    title=_("Service description: "),
                                    help=_(
                                        "The resulting service will get this entry as "
                                        "service description"
                                    ),
                                    allow_empty=False,
                                ),
                            ),
                            (
                                "query",
                                TextInput(
                                    title=_("JQL query: "),
                                    help=_(
                                        "E.g. 'project = my_project and result = "
                                        '"waiting for something"\''
                                    ),
                                    allow_empty=False,
                                    size=80,
                                ),
                            ),
                            (
                                "result",
                                CascadingDropdown(
                                    title=_("Type of result"),
                                    help=_(
                                        "Here you can define, what search result "
                                        "should be used. You can show the number of search "
                                        "results (count) or the summed up or average values "
                                        "of a given numeric field."
                                    ),
                                    choices=[
                                        ("count", _("Number of " "search results")),
                                        (
                                            "sum",
                                            _(
                                                "Summed up values of "
                                                "the following numeric field:"
                                            ),
                                            Tuple(
                                                elements=[
                                                    TextInput(
                                                        title=_("Field Name: "),
                                                        allow_empty=False,
                                                    ),
                                                    Integer(
                                                        title=_(
                                                            "Limit number of processed search results"
                                                        ),
                                                        help=_(
                                                            "Here you can define, how many search results "
                                                            "should be processed. The max. internal limit "
                                                            "of Jira is 1000 results. If you want to "
                                                            "ignore any limit, set -1 here. Default is 50."
                                                        ),
                                                        default_value=50,
                                                    ),
                                                ],
                                            ),
                                        ),
                                        (
                                            "average",
                                            _("Average value " "of the following numeric field: "),
                                            Tuple(
                                                elements=[
                                                    TextInput(
                                                        title=_("Field Name: "),
                                                        allow_empty=False,
                                                    ),
                                                    Integer(
                                                        title=_(
                                                            "Limit number of processed search results"
                                                        ),
                                                        default_value=50,
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ],
                                    sorted=False,
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                    title=_("Custom search query"),
                ),
            ),
        ],
        optional_keys=[
            "jql",
            "project_workflows",
            "instance",
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_jira(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:jira",
        valuespec=_valuespec_special_agents_jira,
    )
)
