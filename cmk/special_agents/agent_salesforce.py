#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.special_agents.v0_unstable.misc import AgentJSON


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
