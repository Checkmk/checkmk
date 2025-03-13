#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret

JQLResult = tuple[str, str | Mapping[str, str | int]]


class _Params(BaseModel, frozen=True):
    instance: str | None = None
    user: str
    password: Secret
    protocol: str
    project_workflows: Sequence[Mapping[str, str | Sequence[str]]] | None = None
    jql: Sequence[Mapping[str, str | JQLResult]] | None = None


def _get_project_workflow(
    project_values: Sequence[Mapping[str, str | Sequence[str]]],
    prefix: str,
) -> list[str]:
    options = []
    for project in project_values:
        options.append("--%s-key" % prefix)
        assert isinstance(project["project"], str)
        options.append(project["project"])
        options.append("--%s-values" % prefix)
        options += project["workflows"]
    return options


def _get_custom_query(
    jql_values: Sequence[Mapping[str, str | JQLResult]],
    prefix: str,
) -> list[str]:
    options = []
    for values in jql_values:
        options.append("--%s-desc" % prefix)
        assert isinstance(values["service_description"], str)
        options.append(values["service_description"])

        options.append("--%s-query" % prefix)
        assert isinstance(values["query"], str)
        options.append(values["query"])

        options.append("--%s-result" % prefix)
        match values["result"]:
            case ("count", _):
                options.append(values["result"][0])
                options.append("--%s-field" % prefix)
                options.append("None")
                options.append("--%s-limit" % prefix)
                options.append("0")
            case (
                "average"
                | "sum",
                {"field_name": field, "limit": limit},
            ):
                options.append(values["result"][0])
                options.append("--%s-field" % prefix)
                assert isinstance(field, str)
                options.append(field)
                options.append("--%s-limit" % prefix)
                options.append("%d" % int(limit))
            case _:
                raise ValueError("Invalid result type")
    return options


def command_function(params: _Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    command_arguments: list[str | Secret] = [
        "-P",
        params.protocol,
        "-u",
        params.user,
        "-s",
        params.password.unsafe(),
    ]

    if params.jql is not None:
        command_arguments += _get_custom_query(params.jql, "jql")

    if params.project_workflows is not None:
        command_arguments += _get_project_workflow(
            params.project_workflows,
            "project-workflows",
        )
    hostname = host_config.name
    if params.instance:
        hostname = params.instance

    command_arguments += [
        "--hostname",
        hostname,
    ]

    yield SpecialAgentCommand(command_arguments=command_arguments)


special_agent_jira = SpecialAgentConfig(
    name="jira",
    parameter_parser=_Params.model_validate,
    commands_function=command_function,
)
