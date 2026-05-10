#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<statgrab_disk>>>
# 1/md0.disk_name 1/md0
# 1/md0.read_bytes 611352576
# 1/md0.systime 1471423620
# 1/md0.write_bytes 39462400
# 1/md1.disk_name 1/md1
# 1/md1.read_bytes 611352576
# 1/md1.systime 1471423620
# 1/md1.write_bytes 39462400


from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib import diskstat


def parse_statgrab_disk(string_table: StringTable) -> diskstat.Section:
    """
    >>> import pprint
    >>> pprint.pprint(parse_statgrab_disk([
    ...     ['1/md0.disk_name', '1/md0'],
    ...     ['1/md0.read_bytes', '611352576'],
    ...     ['1/md0.systime', '1471423620'],
    ...     ['1/md0.write_bytes', '39462400'],
    ...     ['1/md1.disk_name', '1/md1'],
    ...     ['1/md1.read_bytes', '611352576'],
    ...     ['1/md1.systime', '1471423620'],
    ...     ['1/md1.write_bytes', '39462400'],
    ... ]))
    {'1/md0': {'read_throughput': 611352576,
               'timestamp': 1471423620,
               'write_throughput': 39462400},
     '1/md1': {'read_throughput': 611352576,
               'timestamp': 1471423620,
               'write_throughput': 39462400}}

    """
    raw_section: dict[str, dict[str, str]] = {}
    for (name, key), raw_value in ((w0.split("."), w1) for w0, w1 in string_table):
        raw_section.setdefault(name, {})[key] = raw_value

    return {
        raw_disk["disk_name"]: {
            "timestamp": int(raw_disk["systime"]),
            "write_throughput": int(raw_disk["write_bytes"]),
            "read_throughput": int(raw_disk["read_bytes"]),
        }
        for raw_disk in raw_section.values()
    }


agent_section_statgrab_disk = AgentSection(
    name="statgrab_disk",
    parse_function=parse_statgrab_disk,
    parsed_section_name="diskstat",
    supersedes=["ucd_diskio"],
)
