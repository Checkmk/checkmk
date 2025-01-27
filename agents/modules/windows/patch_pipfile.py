#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# simple script to patch linux Pipfile to Windows pipfile
# Deprecated now

import sys

from colorama import (  # type: ignore[import-untyped]
    Fore,
    init,
    Style,
)

init()

error_c = Style.BRIGHT + Fore.RED
ok_c = Style.BRIGHT + Fore.GREEN
info_c = Style.BRIGHT + Fore.CYAN

if len(sys.argv) < 2:
    print(error_c + "Missing arguments")
    sys.exit(1)

try:
    # Read in the file
    print(info_c + f"Opening '{sys.argv[1]}'...")
    with open(sys.argv[1]) as f:
        lines = f.readlines()

    # Replace the target string
    with open(sys.argv[1], "w") as f:
        for l in lines:
            if l.find("psycopg2 = ") == 0:
                f.write('psycopg2 = "*" # windows need new version \n')
            elif l.find("pymssql = ") == 0:
                f.write("# " + l)
            elif l.find("mysqlclient = ") == 0:
                f.write("# " + l)
            else:
                f.write(l)

    print(ok_c + "Finished")
except Exception as e:
    print(error_c + f"Exception is {e}")
