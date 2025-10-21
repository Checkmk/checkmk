#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import getopt
import json
import pprint
import sys

import requests


class AgentJSON:
    def __init__(self, key: str, title: str) -> None:
        self._key = key
        self._title = title

    def usage(self) -> None:
        sys.stderr.write(
            """
Check_MK %s Agent

USAGE: agent_%s --section_url [{section_name},{url}]

    Parameters:
        --section_url   Pair of section_name and url separated by a comma
                        Can be defined multiple times
        --debug         Output json data with pprint

"""
            % (self._title, self._key)
        )

    def get_content(self) -> dict[str, list[str]] | None:
        short_options = "h"
        long_options = ["section_url=", "help", "newline_replacement=", "debug"]

        try:
            opts, _args = getopt.getopt(sys.argv[1:], short_options, long_options)
        except getopt.GetoptError as err:
            sys.stderr.write("%s\n" % err)
            sys.exit(1)

        sections = []
        newline_replacement = "\\n"
        opt_debug = False

        for o, a in opts:
            if o in ["--section_url"]:
                sections.append(a.split(",", 1))
            elif o in ["--newline_replacement"]:
                newline_replacement = a
            elif o in ["--debug"]:
                opt_debug = True
            elif o in ["-h", "--help"]:
                self.usage()
                sys.exit(0)

        if not sections:
            self.usage()
            sys.exit(0)

        content: dict[str, list[str]] = {}
        for section_name, url in sections:
            content.setdefault(section_name, [])
            c = requests.get(url, timeout=900)
            content[section_name].append(c.text.replace("\n", newline_replacement))

        if opt_debug:
            for line in content:
                try:
                    pprint.pprint(json.loads(line))
                except Exception:
                    sys.stdout.write(line + "\n")
            return None

        return content


def main() -> int:
    agent = AgentJSON("salesforce", "Salesforce")
    content = agent.get_content()
    if content is None:
        return 0
    for section, section_content in content.items():
        sys.stdout.write("<<<%s>>>\n" % section)
        for entry in section_content:
            sys.stdout.write("%s\n" % entry)
    sys.stdout.write("\n")
    return 0
