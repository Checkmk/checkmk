#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Generate Windows and Linux dumps from Jinja2 templates.

This script processes a Jinja2 template file and renders it with dynamic values.
The template is rendered with a current Unix timestamp, allowing for generation
of time-stamped agent dumps.

It will replace {{ timestamp }} template variable by current timestamp.

Usage:
    python generate_windows_and_linux_dumps.py <agent_dump_template_file>

Raises:
    NotFileProvidedError: If no agent dump template file is provided as an argument.
"""

import sys
import time

import jinja2


class NotFileProvidedError(Exception):
    pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise NotFileProvidedError("Agent dump template file should be provided")

    with open(sys.argv[1]) as file:
        template = jinja2.Template(file.read())

    print(template.render(timestamp=int(time.time())))
