#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Iterable, Mapping

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.graylog import deserialize_and_merge_json

Section = Mapping[str, Any]


def parse(string_table: StringTable) -> Section:
    return deserialize_and_merge_json(string_table)


register.agent_section(
    name="graylog_failures",
    parse_function=parse,
)


def discover(section: Section) -> DiscoveryResult:
    failure_details = section.get("failures")
    if failure_details is not None:
        yield Service()


def _failure_message_to_human_readable(message_serialized: str) -> Iterable[str]:
    try:
        message_deserialized = json.loads(message_serialized)
    except json.JSONDecodeError:
        # the graylog API does not specify the scheme of the endpoint providing this data (it only
        # says 'anyMap'), see SUP-11170
        yield f"Message: {message_serialized}"
        return
    yield from (
        f"{field.title()}: {field_value}"
        for field in [
            "type",
            "reason",
        ]
        if (field_value := message_deserialized.get(field)) is not None
    )


def check(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    failure_details = section.get("failures")
    if failure_details is None:
        return

    failure_total = section.get("total")
    if failure_total is not None:
        yield from check_levels(
            value=failure_total,
            levels_upper=params.get("failures"),
            metric_name="failures",
            render_func=lambda v: str(int(v)),
            label="Total number of failures",
        )

    failure_count = section.get("count")
    if failure_count is not None:
        yield from check_levels(
            value=failure_count,
            levels_upper=params.get("failures_last"),
            metric_name=None,
            render_func=lambda v: str(int(v)),
            label="Failures in last %s" % render.timespan(section["ds_param_since"]),
        )

        if failure_count:
            index_affected = []
            long_output = []
            for failure in sorted(
                failure_details,
                key=lambda k: (k["timestamp"], k["index"]),
            ):

                long_output_str = ""

                timestamp = failure.get("timestamp")
                if timestamp is not None:
                    long_output_str = "Timestamp: %s" % timestamp

                index = failure.get("index")
                if index is not None:
                    if index not in index_affected:
                        index_affected.append(index)
                    long_output_str += ", Index: %s" % index

                long_output.append(
                    ", ".join(
                        [
                            long_output_str,
                            *(
                                _failure_message_to_human_readable(message_serialized)
                                if (message_serialized := failure.get("message")) is not None
                                else []
                            ),
                        ]
                    )
                )

            if long_output:
                yield Result(
                    state=State.OK,
                    summary="Affected indices: %d, "
                    "See long output for further information" % len(index_affected),
                )
                yield Result(
                    state=State.OK,
                    notice="\n".join(long_output),
                )


register.check_plugin(
    name="graylog_failures",
    service_name="Graylog Index Failures",
    discovery_function=discover,
    check_function=check,
    check_default_parameters={},
    check_ruleset_name="graylog_failures",
)
