#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<graylog_nodes:sep(0)>>>
# {"139f455e-0bb7-4db9-9b9d-bba11767a674": {"facility": "graylog-server",
# "codename": "Noir", "node_id": "139f455e-0bb7-4db9-9b9d-bba11767a674",
# "cluster_id": "292914f7-9702-48fa-be55-8e0914366a7b",
# "version": "6.1.10+a308be3", "started_at": "2025-04-29T16:07:46.860Z",
# "hostname": "5f9efb6a40de", "lifecycle": "running", "lb_status": "alive",
# "timezone": "Europe/Berlin", "operating_system": "Linux 6.8.0-58-generic",
# "is_leader": true, "is_processing": true, "journal": {"enabled": true,
# "append_events_per_second": 23, "read_events_per_second": 0,
# "uncommitted_journal_entries": 23737897, "journal_size": 15689208510,
# "journal_size_limit": 21474836480, "number_of_segments": 150,
# "oldest_segment": "2025-05-02T07:13:32.657Z", "journal_config":
# {"directory": "file:///usr/share/graylog/data/journal/",
# "segment_size": 104857600, "segment_age": 3600000, "max_size": 21474836480,
# "max_age": 43200000, "flush_interval": 1000000, "flush_age": 60000}},
# "inputstates": [{"id": "67b4c30a719a0d063158a7a1", "state": "RUNNING",
# "started_at": "2025-04-29T16:07:55.115Z", "detailed_message": null,
# "message_input": {"title": "Application Logs", "global": false,
# "name": "GELF TCP", "content_pack": null,
# "created_at": "2025-03-19T13:48:18.273Z",
# "type": "org.graylog2.inputs.gelf.tcp.GELFTCPInput",
# "creator_user_id": "niko.wenselowski", "attributes":
# {"recv_buffer_size": 1048576, "tcp_keepalive": false,
# "use_null_delimiter": true, "number_worker_threads": 4,
# "tls_client_auth_cert_file": "", "bind_address": "0.0.0.0",
# "tls_cert_file": "", "decompress_size_limit": 8388608,
# "port": 12201, "tls_key_file": "", "tls_enable": false,
# "tls_key_password": "", "max_message_size": 2097152,
# "tls_client_auth": "disabled", "override_source": null,
# "charset_name": "UTF-8"}, "static_fields": {},
# "node": "139f455e-0bb7-4db9-9b9d-bba11767a674",
# "id": "67b4c30a719a0d063158a7a1"}}]}}

import json
from collections.abc import Mapping, Sequence
from datetime import datetime, UTC
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
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
    "journal_usage_limits": ("fixed", (80.0, 90.0)),
}


def parse_graylog_nodes(string_table: StringTable) -> Section:
    parsed: dict[str, Any] = {}

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

            # Showing journal metrics
            journal_data = node_info.get("journal", {})
            if journal_data.get("enabled", False):
                journal_size = journal_data["journal_size"]
                yield from check_levels(
                    journal_size,
                    metric_name="journal_size",
                    render_func=render.bytes,
                    label="Journal size",
                    notice_only=True,
                )

                journal_size_limit = journal_data["journal_config"]["max_size"]
                yield from check_levels(
                    journal_size_limit,
                    metric_name="journal_size_limit",
                    render_func=render.bytes,
                    label="Journal size limit",
                    notice_only=True,
                )

                yield from check_levels(
                    (journal_size / journal_size_limit) * 100,
                    metric_name="journal_usage",
                    levels_upper=params["journal_usage_limits"],
                    render_func=render.percent,
                    label="Journal usage",
                )

                yield from check_levels(
                    journal_data["uncommitted_journal_entries"],
                    metric_name="journal_unprocessed_messages",
                    render_func=lambda v: f"{v:d}",
                    label="Unprocessed messages in journal",
                    notice_only=True,
                )

                # Converting the time of the oldest segment
                # The server replies with UTC.
                oldest_segment = datetime.strptime(
                    journal_data["oldest_segment"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                # Make the datetime aware of the UTC timezone
                oldest_segment = oldest_segment.replace(tzinfo=UTC)
                oldest_diff = datetime.now(UTC) - oldest_segment
                yield from check_levels(
                    oldest_diff.total_seconds(),
                    metric_name="journal_oldest_segment",
                    render_func=render.timespan,
                    label="Earliest entry in journal",
                )

                yield from check_levels(
                    int(journal_data["journal_config"]["max_age"]) / 1000,
                    metric_name="journal_age_limit",
                    # Age is returned in milliseconds
                    render_func=render.timespan,
                    label="Journal age limit",
                    notice_only=True,
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
