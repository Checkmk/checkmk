#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
import sys


def write_header() -> None:
    print("#!/usr/bin/env python3")
    year = datetime.datetime.now().year
    print(f"# Copyright (C) {year} Checkmk GmbH - License: GNU General Public License v2")
    print("# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and")
    print("# conditions defined in the file COPYING, which is part of this source code package.")
    print()


def main() -> None:
    kubectl_output = sys.stdin.read()
    obj = json.loads(kubectl_output)
    write_header()
    print(f"DATA = {obj}")


if __name__ == "__main__":
    main()
