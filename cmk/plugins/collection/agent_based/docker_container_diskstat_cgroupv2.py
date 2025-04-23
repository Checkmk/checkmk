#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib import diskstat


class ParagraphParser:
    headline: str

    def __init__(self, hp: "HeadlineParser") -> None:
        hp.register_parser(self)

    def parse(self, line: list[str]) -> None:
        pass


class HeadlineParser:
    def __init__(self) -> None:
        self._parsers: dict[str, ParagraphParser] = {}

    def register_parser(self, parser: ParagraphParser) -> None:
        self._parsers[parser.headline] = parser

    def parse(self, lines: Iterable[list[str]]) -> None:
        current_parser = None
        for line in lines:
            if len(line) == 1 and (parser := self._parsers.get(line[0])):
                current_parser = parser
                continue
            if current_parser is not None:
                current_parser.parse(line)


class TimeParagprahParser(ParagraphParser):
    headline = "[time]"

    def __init__(self, hp: HeadlineParser) -> None:
        super().__init__(hp)
        self.time: int

    def parse(self, line: list[str]) -> None:
        self.time = int(line[0])


class NamesParagprahParser(ParagraphParser):
    headline = "[names]"

    def __init__(self, hp: HeadlineParser) -> None:
        super().__init__(hp)
        self.names: dict[str, str] = {}

    def parse(self, line: list[str]) -> None:
        self.names[line[1]] = line[0]


class StatParagprahParser(ParagraphParser):
    headline = "[io.stat]"

    def __init__(self, hp: HeadlineParser) -> None:
        super().__init__(hp)
        self.stat: dict[str, dict[str, str]] = {}

    def parse(self, line: list[str]) -> None:
        stat: dict[str, str] = {}
        for kv_pair in line[1:]:
            try:
                key, value = kv_pair.split("=")
                stat[key] = value
            except ValueError:
                # sometimes we get multiple device numbers on the same line
                # e.g.: 253:0 253:1 rbytes=559349760 wbytes=334268297216 rios=3910 wios=6265888 dbytes=0 dios=0
                continue
        self.stat[line[0]] = stat


class DockerDiskstatParser(HeadlineParser):
    def __init__(self) -> None:
        super().__init__()
        self.time = TimeParagprahParser(self)
        self.names = NamesParagprahParser(self)
        self.stat = StatParagprahParser(self)


def parse_docker_container_diskstat_cgroupv2(
    string_table: StringTable,
) -> diskstat.Section:
    parser = DockerDiskstatParser()
    parser.parse(string_table)

    section: dict[str, dict[str, float]] = {}

    for device_number, stats in parser.stat.stat.items():
        if not {"rios", "wios", "rbytes", "wbytes"}.issubset(stats):
            continue

        device_name = parser.names.names[device_number]
        section[device_name] = {
            "timestamp": parser.time.time,
            "read_ios": int(stats["rios"]),
            "write_ios": int(stats["wios"]),
            "read_throughput": int(stats["rbytes"]),
            "write_throughput": int(stats["wbytes"]),
        }

    return section


agent_section_docker_container_diskstat_cgroupv2 = AgentSection(
    name="docker_container_diskstat_cgroupv2",
    parse_function=parse_docker_container_diskstat_cgroupv2,
    parsed_section_name="diskstat",
)
