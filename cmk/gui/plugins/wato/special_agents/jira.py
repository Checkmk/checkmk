#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
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
from cmk.gui.wato import IndividualOrStoredPassword, RulespecGroupDatasourceProgramsApps
from cmk.gui.watolib.rulespecs import HostRulespec, Rulespec, rulespec_registry


def _factory_default_special_agents_jira():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _validate_jira_projects(value, varprefix):
    used_keys = []
    # KEY:
    # ve_p_services_p_ec2_p_choice_1_IDX_0
    # VALUES:
    # ve_p_services_p_ec2_p_choice_1_IDX_1_IDX
    for idx_project, (project_key, project_values) in enumerate(value):
        project_field = f"{varprefix}_{idx_project + 1}_0"
        if project_key not in used_keys:
            used_keys.append(project_key)
        else:
            raise MKUserError(
                project_field, _("Each project must be unique and cannot be used multiple times")
            )
        if len(project_key) > 128:
            raise MKUserError(project_field, _("The maximum key length is 128 characters."))
        if len(project_values) > 50:
            raise MKUserError(
                project_field, _("The maximum number of projects per resource is 50.")
            )

        for idx_values, v in enumerate(project_values):
            values_field = f"{varprefix}_{idx_project + 1}_1_{idx_values + 1}"
            if len(v) > 256:
                raise MKUserError(values_field, _("The maximum value length is 256 characters."))


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
        validate=_validate_jira_projects,
    )


def _valuespec_special_agents_jira():
    return Dictionary(
        title=_("Jira statistics"),
        help=_("Use Jira Query Language (JQL) to get statistics out of your Jira instance."),
        elements=[
            (
                "instance",
                TextInput(
                    title=_("Jira instance to query"),
                    help=_(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "host name here, eg. my_jira.com. If not set, the "
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
                    help=_("The username that should be used for accessing the Jira API."),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "password",
                IndividualOrStoredPassword(
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
                                    title=_("Service name: "),
                                    help=_(
                                        "The resulting service will get this entry as "
                                        "service name"
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
                                        ("count", _("Number of search results")),
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
                                            _("Average value of the following numeric field: "),
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
        name=RuleGroup.SpecialAgents("jira"),
        valuespec=_valuespec_special_agents_jira,
    )
)
