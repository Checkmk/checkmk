#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.gui.png._wire import pngs_to_json, request_from_json

from ._image import render_pngs


def main() -> None:
    graphs, texts, temperature_unit = request_from_json(sys.stdin.read())
    sys.stdout.write(pngs_to_json(render_pngs(graphs, texts, temperature_unit)))


if __name__ == "__main__":
    main()
