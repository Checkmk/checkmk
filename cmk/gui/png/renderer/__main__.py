#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from ._image import render_pngs
from ._wire import drawings_from_json, pngs_to_json


def main() -> None:
    sys.stdout.write(pngs_to_json(render_pngs(drawings_from_json(sys.stdin.read()))))


if __name__ == "__main__":
    main()
