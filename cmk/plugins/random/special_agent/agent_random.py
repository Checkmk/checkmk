#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_random

Checkmk special agent to create random monitoring data.
Testing script, that can be used as a datasource program.
It creates a number of random services with random states.
"""
# mypy: disable-error-code="no-untyped-def"

import argparse
import ast
import os
import random
import sys
import time
from collections.abc import Sequence
from pathlib import Path


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "hostname",
        required=False,
        default="unknown",
        help="Hostname for which to generate random data",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_arguments(argv or sys.argv[1:])

    state_dir = Path(os.getenv("OMD_ROOT", "/"), "tmp/check_mk/ds_random/")
    state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    state_file = state_dir / args.hostname
    try:
        history = ast.literal_eval(state_file.read_text())
    except (OSError, SyntaxError):
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

    sys.stdout.write("<<<local:sep(0)>>>\n")
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
        sys.stdout.write(
            "%d %s - %s - %s\n"
            % (new_state, service.replace(" ", "_"), state_names[new_state], state_texts[new_state])
        )

    state_file.write_text("%r\n" % history)
