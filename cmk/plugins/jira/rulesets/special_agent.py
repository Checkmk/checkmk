#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# from typing import
from collections.abc import Callable, Mapping, Sequence

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    Integer,
    List,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _validate_jira_projects(value: Sequence[Mapping[str, str | Sequence[str]]]) -> None:
    used_project_names = []
    for project in value:
        if project["project"] in used_project_names:
            raise validators.ValidationError(
                Message("Each project must be unique and cannot be be used multiple times.")
            )
        used_project_names.append(project["project"])


def _tuple_do_dict_with_keys(*keys: str) -> Callable[[object], Mapping[str, object]]:
    def _tuple_to_dict(
        param: object,
    ) -> Mapping[str, object]:
        match param:
            case tuple():
                return dict(zip(keys, param))
            case dict() as already_migrated:
                return already_migrated
        raise TypeError(param)

    return _tuple_to_dict


def _form_spec_jira_projects(title: Title) -> List:
    return List(
        element_template=Dictionary(
            elements={
                "project": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Project"),
                        help_text=Help(
                            "Enter the full name of the "
                            "project here. You can find "
                            "the name in Jira within "
                            '"Projects" - "View all '
                            'projects" - column: "Project". '
                            "This field is case "
                            "insensitive"
                        ),
                        custom_validate=(
                            validators.LengthInRange(
                                min_value=1,
                                max_value=128,
                                error_msg=Message("The maximum key length is 128 characters."),
                            ),
                            validators.MatchRegex(
                                regex="^[^']*$",
                                error_msg=Message("Single quotes are not allowed here."),
                            ),
                        ),
                    ),
                ),
                "workflows": DictElement(
                    required=True,
                    parameter_form=List(
                        title=Title("Workflows"),
                        help_text=Help(
                            'Enter the workflow name for the project here. E.g. "in progress".'
                        ),
                        element_template=String(
                            custom_validate=(
                                validators.LengthInRange(
                                    min_value=1,
                                    max_value=256,
                                    error_msg=Message(
                                        "The maximum value length is 256 characters."
                                    ),
                                ),
                                validators.MatchRegex(
                                    regex="^[^']*$",
                                    error_msg=Message("Single quotes are not allowed here."),
                                ),
                            ),
                        ),
                        custom_validate=(
                            validators.LengthInRange(
                                max_value=50,
                                error_msg=Message(
                                    "The maximum number of projects per resource is 50.",
                                ),
                            ),
                        ),
                    ),
                ),
            },
            migrate=_tuple_do_dict_with_keys("project", "workflows"),
        ),
        add_element_label=Label("Add new project"),
        editable_order=False,
        title=title,
        custom_validate=(_validate_jira_projects,),
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Jira statistics"),
        help_text=Help(
            "Use Jira Query Language (JQL) to get statistics out of your Jira instance."
        ),
        elements={
            "instance": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Jira instance to query"),
                    help_text=Help(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "host name here, e.g. my_jira.com. If not set, the "
                        "assigned host is used as instance."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("The username that should be used for accessing the Jira API."),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password of the user"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "protocol": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement(name="http", title=Title("HTTP")),
                        SingleChoiceElement(name="https", title=Title("HTTPS")),
                    ],
                    prefill=DefaultValue("https"),
                ),
            ),
            "project_workflows": DictElement(
                required=False,
                parameter_form=_form_spec_jira_projects(
                    Title(
                        "Monitor the number of issues for given projects and their "
                        "workflows. This results in a service for each project with "
                        "the number of issues per workflow."
                    ),
                ),
            ),
            "jql": DictElement(
                required=False,
                parameter_form=List(
                    element_template=Dictionary(
                        elements={
                            "service_description": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Service name: "),
                                    help_text=Help(
                                        "The resulting service will get this entry as service name"
                                    ),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                            ),
                            "query": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("JQL query: "),
                                    help_text=Help(
                                        "E.g. 'project = my_project and result = "
                                        '"waiting for something"\''
                                    ),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                    field_size=FieldSize.LARGE,
                                ),
                            ),
                            "result": DictElement(
                                required=True,
                                parameter_form=CascadingSingleChoice(
                                    title=Title("Type of result"),
                                    help_text=Help(
                                        "Here you can define, what search result "
                                        "should be used. You can show the number of search "
                                        "results (count) or the summed up or average values "
                                        "of a given numeric field."
                                    ),
                                    elements=[
                                        CascadingSingleChoiceElement(
                                            name="count",
                                            title=Title("Number of search results"),
                                            parameter_form=FixedValue(value="count"),
                                        ),
                                        CascadingSingleChoiceElement(
                                            name="sum",
                                            title=Title(
                                                "Summed up values of the following numeric field:"
                                            ),
                                            parameter_form=Dictionary(
                                                elements={
                                                    "field_name": DictElement(
                                                        required=True,
                                                        parameter_form=String(
                                                            title=Title("Field Name: "),
                                                            custom_validate=(
                                                                validators.LengthInRange(
                                                                    min_value=1
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                    "limit": DictElement(
                                                        required=True,
                                                        parameter_form=Integer(
                                                            title=Title(
                                                                "Limit number of processed search results"
                                                            ),
                                                            help_text=Help(
                                                                "Here you can define, how many search results "
                                                                "should be processed. The max. internal limit "
                                                                "of Jira is 1000 results. If you want to "
                                                                "ignore any limit, set -1 here. Default is 50."
                                                            ),
                                                            prefill=DefaultValue(50),
                                                        ),
                                                    ),
                                                },
                                                migrate=_tuple_do_dict_with_keys(
                                                    "field_name", "limit"
                                                ),
                                            ),
                                        ),
                                        CascadingSingleChoiceElement(
                                            name="average",
                                            title=Title(
                                                "Average value of the following numeric field: "
                                            ),
                                            parameter_form=Dictionary(
                                                elements={
                                                    "field_name": DictElement(
                                                        required=True,
                                                        parameter_form=String(
                                                            title=Title("Field Name: "),
                                                            custom_validate=(
                                                                validators.LengthInRange(
                                                                    min_value=1
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                    "limit": DictElement(
                                                        required=True,
                                                        parameter_form=Integer(
                                                            title=Title(
                                                                "Limit number of processed search results"
                                                            ),
                                                            prefill=DefaultValue(50),
                                                        ),
                                                    ),
                                                },
                                                migrate=_tuple_do_dict_with_keys(
                                                    "field_name", "limit"
                                                ),
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                        },
                    ),
                    title=Title("Custom search query"),
                ),
            ),
        },
    )


rule_spec_special_agent_jira = SpecialAgent(
    name="jira",
    title=Title("Jira statistics"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
)
