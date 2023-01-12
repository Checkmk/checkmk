#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys

import cmk.utils.tty as tty
from cmk.utils.packaging import cli, PackageException, PACKAGES_DIR

logger = logging.getLogger("cmk.base.packaging")


def packaging_usage() -> None:
    sys.stdout.write(
        f"""Usage: check_mk [-v] -P|--package COMMAND [ARGS]

Available commands are:
   template NAME                ...  Collect unpackaged files into new package template NAME
   package MANIFEST_FILE        ...  Create package file from package manifest
   release NAME                 ...  Drop installed package NAME, release packaged files
   find [-h] [-a] [--json]      ...  Find and display unpackaged files
   inspect FILE                 ...  Show manifest of an `.mkp` file.
   list                         ...  List all installed packages
   files NAME [VERSION]         ...  List files of package
   show [--json] NAME [VERSION] ...  Show information about installed package
   show-all [--json]            ...  Show information about all known packages
   install PACK.mkp             ...  Install or update package from file PACK.mkp
   remove NAME VERSION          ...  Uninstall and delete package NAME
   disable NAME [VERSION]       ...  Disable package NAME
   enable NAME [VERSION]        ...  Enable previously disabled package NAME
   disable-outdated             ...  Disable outdated packages
   update-active                ...  Update the selection of active packages (according to Checkmk version)

   -v  enables verbose output

Package files are located in {PACKAGES_DIR}.
"""
    )


def do_packaging(args: list[str]) -> None:
    if len(args) == 0:
        packaging_usage()
        sys.exit(1)
    command = args[0]
    args = args[1:]

    commands = {
        "template": lambda args: cli.main(["template", *args], logger),
        "release": lambda args: cli.main(["release", *args], logger),
        "files": lambda args: cli.main(["files", *args], logger),
        "list": lambda args: cli.main(["list", *args], logger),
        "find": lambda args: cli.main(["find", *args], logger),
        "inspect": lambda args: cli.main(["inspect", *args], logger),
        "show-all": lambda args: cli.main(["show-all", *args], logger),
        "show": lambda args: cli.main(["show", *args], logger),
        "package": lambda args: cli.main(["package", *args], logger),
        "remove": lambda args: cli.main(["remove", *args], logger),
        "disable": lambda args: cli.main(["disable", *args], logger),
        "enable": lambda args: cli.main(["enable", *args], logger),
        "disable-outdated": lambda args: cli.main(["disable-outdated", *args], logger),
        "update-active": lambda args: cli.main(["update-active", *args], logger),
    }
    f = commands.get(command)
    if f:
        try:
            f(args)
        except PackageException as e:
            logger.error("%s", e)
            sys.exit(1)
    else:
        allc = sorted(commands)
        allc = [tty.bold + c + tty.normal for c in allc]
        logger.error(
            "Invalid packaging command. Allowed are: %s and %s.", ", ".join(allc[:-1]), allc[-1]
        )
        sys.exit(1)
