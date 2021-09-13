#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import cmk.special_agents.utils as utils


def main():
    agent = utils.AgentJSON("salesforce", "Salesforce")
    content = agent.get_content()
    for section, section_content in content.items():
        sys.stdout.write("<<<%s>>>\n" % section)
        for entry in section_content:
            sys.stdout.write("%s\n" % entry)
    sys.stdout.write("\n")
