#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow
from cmk.plugins.ibm.lib_mq import parse_ibm_mq

Section = Mapping[str, Mapping[str, str]]


def parse_ibm_mq_queues(string_table: StringTable) -> Section:
    queue_status = parse_ibm_mq(string_table, "QSTATUS")
    queue = parse_ibm_mq(string_table, "QUEUE")
    return _merge_sections(queue, queue_status)


def _merge_sections(
    priority_section: Mapping[str, Mapping[str, str]],
    additional_section: Mapping[str, Mapping[str, str]],
) -> Mapping[str, Mapping[str, str]]:
    """Merge two queue-attribute mappings; priority_section wins on key conflicts."""
    result: dict[str, dict[str, str]] = {k: dict(v) for k, v in additional_section.items()}
    for key, value in priority_section.items():
        if key in result:
            result[key] = {**result[key], **value}
        else:
            result[key] = dict(value)
    return result


agent_section_ibm_mq_queues = AgentSection(
    name="ibm_mq_queues",
    parse_function=parse_ibm_mq_queues,
)


def inventorize_ibm_mq_queues(section: Section) -> InventoryResult:
    for item, attrs in sorted(section.items(), key=lambda t: t[0]):
        if ":" not in item:
            # Do not show queue manager in inventory
            continue

        qmname, qname = item.split(":")
        yield TableRow(
            path=["software", "applications", "ibm_mq", "queues"],
            key_columns={
                "qmgr": qmname,
                "name": qname,
            },
            inventory_columns={
                "maxdepth": attrs["MAXDEPTH"],
                "maxmsgl": attrs.get("MAXMSGL", "n/a"),
                "created": (
                    "{} {}".format(
                        attrs.get("CRDATE", "n/a"), attrs.get("CRTIME", "").replace(".", ":")
                    )
                ).strip(),
                "altered": (
                    "{} {}".format(
                        attrs.get("ALTDATE", "n/a"), attrs.get("ALTTIME", "").replace(".", ":")
                    )
                ).strip(),
                "monq": attrs.get("MONQ", "n/a"),
            },
            status_columns={},
        )


inventory_plugin_ibm_mq_queues = InventoryPlugin(
    name="ibm_mq_queues",
    inventory_function=inventorize_ibm_mq_queues,
)
