#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#!/usr/bin/env python3
"""
This tool extracts the OS dependencies form our *.mk distros files and writes them into a file
readable by deb / rpm packaging tools.
"""

import re
import sys


def strip_comment(s: str) -> str:
    # Everything after '#' is comment in our mk files
    return s.split("#", 1)[0].strip()


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: extract_os_packages.py <input.mk> <output.txt> <separator>", file=sys.stderr)
        return 2

    in_path, out_path, sep = sys.argv[1], sys.argv[2], sys.argv[3]

    # Match:
    #   OS_PACKAGES =
    #   OS_PACKAGES += libcap # comment
    rx = re.compile(r"^\s*OS_PACKAGES\s*(\+=|=)\s*(.*)\s*$")

    pkgs = []
    with open(in_path, encoding="utf-8") as f:
        for line in f:
            m = rx.match(line)
            if not m:
                continue
            op, rhs = m.group(1), strip_comment(m.group(2))
            tokens = rhs.split() if rhs else []

            if op == "=":
                pkgs = tokens
            else:  # "+="
                pkgs.extend(tokens)

    out = sep.join(pkgs) + "\n"
    with open(out_path, "w", encoding="utf-8") as out_f:
        out_f.write(out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
