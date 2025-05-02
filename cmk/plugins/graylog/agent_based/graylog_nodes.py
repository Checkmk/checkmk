#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<graylog_nodes>>>
# {"a56db164-78a6-4dc8-bec9-418b9edf9067": {"inputstates": {"message_input":
# {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Syslog TCP",
# "title": "syslog test", "created_at": "2019-09-30T07:11:19.932Z", "global":
# false, "content_pack": null, "attributes": {"tls_key_file": "", "tls_enable":
# false, "store_full_message": false, "tcp_keepalive": false,
# "tls_key_password": "", "tls_cert_file": "", "allow_override_date": true,
# "recv_buffer_size": 1048576, "port": 514, "max_message_size": 2097152,
# "number_worker_threads": 8, "bind_address": "0.0.0.0",
# "expand_structured_data": false, "tls_client_auth_cert_file": "",
# "tls_client_auth": "disabled", "use_null_delimiter": false, "force_rdns":
# false, "override_source": null}, "creator_user_id": "admin", "static_fields":
# {}, "type": "org.graylog2.inputs.syslog.tcp.SyslogTCPInput", "id":
# "5d91aa97dedfc2061e233e86"}, "state": "FAILED", "started_at":
# "2019-09-30T07:11:20.720Z", "detailed_message": "bind(..) failed: Keine
# Berechtigung.", "id": "5d91aa97dedfc2061e233e86"}, "lb_status": "alive",
# "operating_system": "Linux 4.15.0-1056-oem", "version": "3.1.2+9e96b08",
# "facility": "graylog-server", "hostname": "klappclub", "node_id":
# "a56db164-78a6-4dc8-bec9-418b9edf9067", "cluster_id":
# "d19bbcf9-9aaf-4812-a829-ba7cc4672ac9", "timezone": "Europe/Berlin",
# "codename": "Quantum Dog", "started_at": "2019-09-30T05:53:17.699Z",
# "lifecycle": "running", "is_processing": true}}


# mypy: disable-error-code="var-annotated"

import json
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Sequence[Any]]


DEFAULT_CHECK_PARAMS = {
    "lb_throttled": State.CRIT.value,
    "lb_alive": State.OK.value,
    "lb_dead": State.CRIT.value,
    "lc_uninitialized": State.WARN.value,
    "lc_paused": State.WARN.value,
    "lc_running": State.OK.value,
    "lc_failed": State.CRIT.value,
    "lc_halting": State.WARN.value,
    "lc_throttled": State.CRIT.value,
    "lc_starting": State.WARN.value,
    "lc_override_lb_alive": State.OK.value,
    "lc_override_lb_dead": State.WARN.value,
    "lc_override_lb_throttled": State.WARN.value,
    "ps_true": State.OK.value,
    "ps_false": State.CRIT.value,
    "input_state": State.WARN.value,
}


def parse_graylog_nodes(string_table: StringTable) -> Section:
    parsed = {}

    for line in string_table:
        node_details = json.loads(line[0])

        for node, detail in node_details.items():
            try:
                parsed.setdefault(node, []).append(detail)
            except KeyError:
                pass

    return parsed


def inventory_graylog_nodes(section: Section) -> DiscoveryResult:
    for node in section:
        yield Service(item=node)


def check_graylog_nodes(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if section is None:
        return

    if item not in section:
        yield Result(state=State.CRIT, summary="Missing in agent output (graylog service running?)")
        return

    for node_name, details in section.items():
        if item != node_name:
            continue

        inputstates_count = 0
        inputstate_results = []

        for node_info in details:
            for key, infotext, levels in [
                ("lb_status", "Load balancer", "lb_"),
                ("lifecycle", "Lifecycle", "lc_"),
                ("is_processing", "Is processing", "ps_"),
            ]:
                value = node_info.get(key)
                if value is None:
                    continue

                state = params.get(f"{levels}{str(value).lower()}", State.WARN.value)

                yield Result(
                    state=State(state),
                    summary="{}: {}".format(
                        infotext,
                        str(value).replace("True", "yes").replace("False", "no"),
                    ),
                )

            value_inputstates = node_info.get("inputstates", [])
            inputstates_count += len(value_inputstates)
            for index, inputstate in enumerate(value_inputstates, start=1):
                long_output_str = f"Input {index}: "

                if (value_input_message := inputstate.get("message_input")) is not None:
                    if (value_title := value_input_message.get("title")) is not None:
                        long_output_str += "Title: %s, " % value_title.title()

                    if (value_name := value_input_message.get("name")) is not None:
                        long_output_str += "Type: %s, " % value_name

                if (value_input_state := inputstate.get("state")) is not None:
                    state_of_input = State.OK.value
                    if value_input_state != "RUNNING":
                        state_of_input = params["input_state"]
                    long_output_str += "Status: %s" % value_input_state
                else:
                    state_of_input = State.UNKNOWN.value
                    long_output_str += "Status: UNKNOWN"

                inputstate_results.append(
                    Result(state=State(state_of_input), notice=long_output_str)
                )

        input_nr_levels_upper = params.get("input_count_upper", ("no_levels", None))
        input_nr_levels_lower = params.get("input_count_lower", ("no_levels", None))
        yield from check_levels(
            inputstates_count,
            metric_name="num_input",
            levels_lower=input_nr_levels_lower,
            levels_upper=input_nr_levels_upper,
            render_func=lambda v: f"Inputs: {v}",
        )
        # Output the collected inputstates after returning the metric for
        # the amount of inputstates.
        yield from inputstate_results


agent_section_graylog_nodes = AgentSection(
    name="graylog_nodes",
    parse_function=parse_graylog_nodes,
)


check_plugin_graylog_nodes = CheckPlugin(
    name="graylog_nodes",
    service_name="Graylog Node %s",
    discovery_function=inventory_graylog_nodes,
    check_function=check_graylog_nodes,
    check_default_parameters=DEFAULT_CHECK_PARAMS,
    check_ruleset_name="graylog_nodes",
)
