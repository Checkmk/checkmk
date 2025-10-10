#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Service,
    StringTable,
)

DEFAULT_ITEM_NAME: str = "default"


@dataclass
class PostfixMailQueue:
    name: str | None = None
    size: int = 0  # in bytes
    length: int = 0


Section = Mapping[str, list[PostfixMailQueue]]


def postfix_mailq_to_bytes(value: float, uom: str) -> int:
    uom = uom.lower()
    if uom == "kbytes":
        return int(value * 1024)
    if uom == "mbytes":
        return int(value * 1024 * 1024)
    if uom == "gbytes":
        return int(value * 1024 * 1024 * 1024)
    return 0


def parse_postfix_mailq(string_table: StringTable) -> Section:
    result: dict[str, list[PostfixMailQueue]] = {}
    instance_name: str = DEFAULT_ITEM_NAME
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            # deal with the pre 2.3 agent output that will send an empty instance
            # name for the "default" queue.
            instance_name = line[0][3:-3] or DEFAULT_ITEM_NAME

        postfix_mail_queue: PostfixMailQueue = PostfixMailQueue()
        # single and old output formats
        if line[0].startswith("QUEUE_"):
            # Deal with old agent (pre 1.2.8) which did not send size
            # infos in case of different error cases
            if len(line) == 2:
                postfix_mail_queue.size = 0
                postfix_mail_queue.length = int(line[1])  # number of mails
            else:
                postfix_mail_queue.size = int(line[1])  # in bytes
                postfix_mail_queue.length = int(line[2])  # number of mails

            postfix_mail_queue.name = line[0].split("_")[1]

        elif " ".join(line[-2:]) == "is empty":
            postfix_mail_queue.name = "empty"
            postfix_mail_queue.size = 0
            postfix_mail_queue.length = 0

        elif line[0] == "--" or line[0:2] == ["Total", "requests:"]:
            if line[0] == "--":
                postfix_mail_queue.size = postfix_mailq_to_bytes(float(line[1]), line[2])
                postfix_mail_queue.length = int(line[4])
            else:
                postfix_mail_queue.size = 0
                postfix_mail_queue.length = int(line[2])

            postfix_mail_queue.name = "mail"

        if postfix_mail_queue.name is not None:
            result.setdefault(instance_name, [])
            result[instance_name].append(postfix_mail_queue)

    return result


def discovery_postfix_mailq(section: Section) -> DiscoveryResult:
    for instance in section:
        yield Service(item=instance)


def check_postfix_mailq(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    # If the user disabled the "Use new service description" option, we arrive
    # at this function with item being None. In this case we still need to
    # lookup the data in parsed under the default item name.
    if item is None:
        item = DEFAULT_ITEM_NAME

    if item not in section:
        return

    if not isinstance(params, dict) and isinstance(params, tuple):
        params = {"deferred": params}

    for mail_queue in section[item]:
        _queue_name = mail_queue.name if mail_queue.name else ""
        warn, crit = params.get(_queue_name if _queue_name != "mail" else "deferred", (None, None))
        length_limit: LevelsT = ("no_levels", None)
        if warn is not None and crit is not None:
            length_limit = ("fixed", (warn, crit))

        # Metric names differ for active mailqueue
        length_metric_name: str = "length"
        size_metric_name: str = "size"
        if mail_queue.name == "active":
            length_metric_name = "mail_queue_active_length"
            size_metric_name = "mail_queue_active_size"

        # Label differs for empty mailqueue
        length_label: str = f"{_queue_name} queue length"
        size_label: str = f"{_queue_name} queue size"
        if mail_queue.name == "empty":
            length_label = "The mailqueue is empty"
            size_label = "The mailqueue is empty"

        yield from check_levels(
            mail_queue.length,
            metric_name=length_metric_name,
            levels_upper=length_limit,
            render_func=str,
            label=length_label,
        )
        yield from check_levels(
            mail_queue.size,
            metric_name=size_metric_name,
            render_func=render.bytes,
            label=size_label,
        )


agent_section_postfix_mailq = AgentSection(
    name="postfix_mailq",
    parse_function=parse_postfix_mailq,
)

check_plugin_postfix_mailq = CheckPlugin(
    name="postfix_mailq",
    service_name="Postfix Queue %s",
    discovery_function=discovery_postfix_mailq,
    check_function=check_postfix_mailq,
    check_ruleset_name="mail_queue_length",
    check_default_parameters={
        "deferred": (10, 20),
        "active": (200, 300),  # may become large for big mailservers
    },
)
