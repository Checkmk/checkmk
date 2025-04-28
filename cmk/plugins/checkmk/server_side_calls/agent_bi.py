#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Iterable, Mapping
from typing import Literal, NotRequired, TypedDict

from cmk.plugins.checkmk.special_agents.agent_bi import (
    AgentBiAdditionalOptions,
    AgentBiAssignments,
    AgentBiAutomationUserAuthentication,
    AgentBiConfig,
    AgentBiFilter,
    AgentBiUserAuthentication,
)
from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class _Regex(TypedDict):
    regular_expression: str
    replacement: str


class _Assignments(TypedDict):
    querying_host: NotRequired[Literal["querying_host"]]
    affected_hosts: NotRequired[Literal["affected_hosts"]]
    regex: NotRequired[list[_Regex]]


class _Password(TypedDict):
    username: str
    password: Secret


_Credentials = tuple[Literal["automation"], str] | tuple[Literal["configured"], _Password]


class _Filter(TypedDict):
    aggr_name: NotRequired[list[str]]
    aggr_name_regex: NotRequired[list[str]]
    aggr_group_prefix: NotRequired[list[str]]
    aggr_groups: NotRequired[list[str]]


class _RemoteConfig(TypedDict):
    url: str
    credentials: _Credentials


class _SiteConfig(TypedDict):
    """This is comming from the formspec"""

    site: tuple[Literal["local"], None] | tuple[Literal["remote"], _RemoteConfig]
    filter: NotRequired[_Filter]
    options: NotRequired[AgentBiAdditionalOptions]
    assignments: NotRequired[_Assignments]


def _transform_authentication(
    site_config: tuple[Literal["local"], None] | tuple[Literal["remote"], _RemoteConfig],
) -> (
    tuple[None, None]
    | tuple[AgentBiAutomationUserAuthentication, None]
    | tuple[AgentBiUserAuthentication, Secret]
):
    # Internal user as local site will be None
    if site_config[0] == "local":
        return None, None
    remote_config = site_config[1]
    if remote_config["credentials"][0] == "automation":
        return (
            AgentBiAutomationUserAuthentication(
                username=remote_config["credentials"][1],
            ),
            None,
        )
    return (
        AgentBiUserAuthentication(
            username=remote_config["credentials"][1]["username"],
            password_store_path=None,
            password_store_identifier=None,
        ),
        remote_config["credentials"][1]["password"],
    )


def _transform_assignments(assignments_config: _Assignments | None) -> AgentBiAssignments | None:
    if not assignments_config:
        return None
    return AgentBiAssignments(
        querying_host="querying_host" in assignments_config,
        affected_hosts="affected_hosts" in assignments_config,
        regex=[
            (r["regular_expression"], r["replacement"]) for r in assignments_config.get("regex", [])
        ],
    )


def _transform_filter(filter_dict: _Filter | None) -> AgentBiFilter:
    # There is an inconsistency between the WATO rule and the webapi.
    # WATO <-> API
    #  aggr_groups / aggr_group_prefix -> groups
    #  aggr_name_regex / aggr_name -> names
    # Note: In 1.6 aggr_name_regex never worked as regex, it always was an exact match

    # Apparently "aggr_groups" and "aggr_name_regex" were deprecated with/since 1.6
    if not filter_dict:
        return AgentBiFilter()

    return AgentBiFilter(
        names=filter_dict.get("aggr_name", filter_dict.get("aggr_name_regex", [])),
        groups=[
            x for x in filter_dict.get("aggr_group_prefix", filter_dict.get("aggr_groups", []))
        ],
    )


def _site_config_to_agent_config(
    site_config: _SiteConfig,
) -> tuple[Secret | None, AgentBiConfig]:
    """transform the params to AgentBiConfig

    This is a bit awkward. The server-side-calls API does not provide a way to translate
    the secrets to something actionable if not transported via commandline. So we need to
    transport the secrets (if we have some) over the commandline...
    """
    creds, secret = _transform_authentication(site_config["site"])
    return secret, AgentBiConfig(
        filter=_transform_filter(site_config.get("filter")),
        site_url=None if site_config["site"][0] == "local" else site_config["site"][1]["url"],
        authentication=creds,
        options=site_config.get("options", {}),
        assignments=_transform_assignments(site_config.get("assignments")),
    )


def _agent_bi_parser(params: Mapping[str, object]) -> list[tuple[Secret | None, AgentBiConfig]]:
    options = params["options"]
    assert isinstance(options, list)
    return [_site_config_to_agent_config(config) for config in options]


def _agent_bi_arguments(
    params: list[tuple[Secret | None, AgentBiConfig]],
    _hostconfig: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    cli_args: list[Secret | str] = ["--secrets"]
    configs: list[str] = ["--configs"]

    for secret, config in params:
        cli_args.append("nosecret" if secret is None else secret)
        configs.append(config.model_dump_json())

    yield SpecialAgentCommand(command_arguments=cli_args, stdin=json.dumps(configs))


special_agent_bi = SpecialAgentConfig(
    name="bi",
    parameter_parser=_agent_bi_parser,
    commands_function=_agent_bi_arguments,
)
