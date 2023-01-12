#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys

import cmk.utils.tty as tty
from cmk.utils.log import VERBOSE
from cmk.utils.packaging import (
    cli,
    get_installed_manifest,
    get_installed_manifests,
    Manifest,
    package_num_files,
    PACKAGE_PARTS,
    PackageException,
    PackageName,
    PACKAGES_DIR,
)

logger = logging.getLogger("cmk.base.packaging")


def packaging_usage() -> None:
    sys.stdout.write(
        f"""Usage: check_mk [-v] -P|--package COMMAND [ARGS]

Available commands are:
   template NAME           ...  Collect unpackaged files into new package template NAME
   package MANIFEST_FILE   ...  Create package file from package manifest
   release NAME            ...  Drop installed package NAME, release packaged files
   find [-h] [-a] [--json] ...  Find and display unpackaged files
   inspect FILE            ...  Show manifest of an `.mkp` file.
   list                    ...  List all installed packages
   list NAME               ...  List files of installed package
   show NAME               ...  Show information about installed package
   show-all [--json]       ...  Show information about all known packages
   install PACK.mkp        ...  Install or update package from file PACK.mkp
   remove NAME VERSION     ...  Uninstall and delete package NAME
   disable NAME [VERSION]  ...  Disable package NAME
   enable NAME [VERSION]   ...  Enable previously disabled package NAME
   disable-outdated        ...  Disable outdated packages
   update-active           ...  Update the selection of active packages (according to Checkmk version)

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
        "list": package_list,
        "find": lambda args: cli.main(["find", *args], logger),
        "inspect": lambda args: cli.main(["inspect", *args], logger),
        "show-all": lambda args: cli.main(["show-all", *args], logger),
        "show": package_show,
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


def package_list(args: list[str]) -> None:
    if len(args) > 0:
        for package in (_resolve_package_argument(arg) for arg in args):
            _list_package(package)
            return

    table = [
        [
            manifest.name,
            manifest.version,
            manifest.title,
            str(package_num_files(manifest)),
        ]
        for manifest in get_installed_manifests()
    ]

    if logger.isEnabledFor(VERBOSE):
        tty.print_table(["Name", "Version", "Title", "Files"], [tty.bold, "", ""], table)
    else:
        for name, *_omitted in table:
            sys.stdout.write("%s\n" % name)


def package_show(args: list[str]) -> None:
    if len(args) == 0:
        raise PackageException("Usage: check_mk -P show NAME")

    for manifest in (_resolve_package_argument(arg) for arg in args):
        sys.stdout.write(f"{manifest.to_text()}\n")


def _list_package(package: Manifest) -> None:
    if logger.isEnabledFor(VERBOSE):
        sys.stdout.write(f"Files in package {package.name}:\n")
        for part in PACKAGE_PARTS:
            if part_files := package.files.get(part, []):
                sys.stdout.write(f"  {tty.bold}{part.ui_title}{tty.normal}:\n")
                for f in part_files:
                    sys.stdout.write("    %s\n" % f)
    else:
        for part in PACKAGE_PARTS:
            for fn in package.files.get(part, []):
                sys.stdout.write(f"{part / fn}\n")


def _resolve_package_argument(name: str) -> Manifest:
    if (package := get_installed_manifest(PackageName(name))) is None:
        raise PackageException(f"No such package: {name}")
    return package
