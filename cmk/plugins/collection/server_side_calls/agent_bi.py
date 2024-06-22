#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping, Sequence

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig

#  { "agent_bi_options" :
#  [{'credentials': 'automation', 'site': 'local'},
#   {'assignments': {'affected_hosts': 'affected_hosts',
#                    'querying_host': 'querying_host',
#                    'regex': []},
#    'credentials': ('configured', ('tata', ('password', 'tete'))),
#    'filter': {'aggr_group_prefix': ['Hosts'], 'aggr_name': ['aggrB']},
#    'options': {'state_acknowledged': 1, 'state_scheduled_downtime': 2},
#    'site': ('url', 'http://localhost/someforeignsite')}]
#  }

_AgentBIOptions = Sequence[Mapping[str, object]]


def _agent_bi_parser(params: Mapping[str, object]) -> _AgentBIOptions:
    bi_options = params["options"]
    assert isinstance(bi_options, list)

    # Note: does inline replacement instead of creating new params
    for param_set in bi_options:
        # There is an inconsistency between the WATO rule and the webapi.
        # WATO <-> API
        #  aggr_groups / aggr_group_prefix -> groups
        #  aggr_name_regex / aggr_name -> names
        # Note: In 1.6 aggr_name_regex never worked as regex, it always was an exact match
        filter_ = param_set.get("filter", {})
        for replacement, name in (
            ("groups", "aggr_groups"),  # 1.6 (deprecated)
            ("names", "aggr_name_regex"),  # 1.6 (deprecated)
            ("groups", "aggr_group_prefix"),
            ("names", "aggr_name"),
        ):
            if name in filter_:
                filter_[replacement] = filter_.pop(name)
    return bi_options


def _agent_bi_arguments(
    params: _AgentBIOptions,
    _hostconfig: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    yield SpecialAgentCommand(command_arguments=[], stdin=repr(params))


special_agent_bi = SpecialAgentConfig(
    name="bi",
    parameter_parser=_agent_bi_parser,
    commands_function=_agent_bi_arguments,
)
