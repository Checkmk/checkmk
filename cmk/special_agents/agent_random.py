#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Testing script, that can be used as a datasource program
# and creates a number of random services with random states.
# Call it with the hostname as the first argument.

import ast
import os
import random
import sys
import time


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    try:
        hostname = sys_argv[1]
    except IndexError:
        hostname = "unknown"

    state_dir = os.getenv("OMD_ROOT", "") + "/tmp/check_mk/ds_random/"
    if not os.path.exists(state_dir):
        os.makedirs(state_dir)
    state_file = state_dir + hostname
    try:
        history = ast.literal_eval(open(state_file).read())  # pylint:disable=consider-using-with
    except (OSError, SyntaxError, IOError):
        history = {}

    services = [
        "Gnarz Usage",
        "Fnorz Utilization",
        "Average Grumblage",
        "Snarks 011",
        "Snarks 012",
        "Snarks 022",
        "Gnogomatic Turbler",
        "Gnogomatic Murbler",
        "Gnogomatic Garglebox",
    ]

    print("<<<local:sep(0)>>>")
    state_names = ["OK", "WARN", "CRIT", "UNKNOWN"]
    state_texts = [
        "Everying is OK now",
        "The freibl might go slisk",
        "Bad luck, everything is broken",
        "Something really weird happened",
    ]

    now = time.time()
    for service in services:
        last_change, last_state = history.get(service, (now - 600, 0))
        p_state_change = ((now - last_change) / 60.0) + 1
        if last_state == 0:
            p_state_change += 10
        if int(random.random() * p_state_change) == 0:
            if last_state != 0 and random.random() < 0.7:
                new_state = 0
            else:
                new_state = 1 + int(random.random() * 3)
            if new_state != last_state:
                history[service] = (now, new_state)
        else:
            new_state = last_state
        print(
            "%d %s - %s - %s"
            % (new_state, service.replace(" ", "_"), state_names[new_state], state_texts[new_state])
        )

    open(state_file, "w").write("%r\n" % history)  # pylint:disable=consider-using-with
