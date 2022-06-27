#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import sys
import tarfile
from pathlib import Path
from typing import AbstractSet, BinaryIO, cast, List

import cmk.utils.debug
import cmk.utils.packaging as packaging
import cmk.utils.paths
import cmk.utils.tty as tty
import cmk.utils.werks
from cmk.utils.log import VERBOSE
from cmk.utils.packaging import (
    get_config_parts,
    get_initial_package_info,
    get_package_parts,
    package_dir,
    PACKAGE_EXTENSION,
    PackageException,
    parse_package_info,
    read_package_info,
    unpackaged_files,
    unpackaged_files_in_dir,
    write_package_info,
)

logger = logging.getLogger("cmk.base.packaging")

PackageName = str


def packaging_usage() -> None:
    sys.stdout.write(
        """Usage: check_mk [-v] -P|--package COMMAND [ARGS]

Available commands are:
   create NAME      ...  Collect unpackaged files into new package NAME
   pack NAME        ...  Create package file from installed package
   release NAME     ...  Drop installed package NAME, release packaged files
   find             ...  Find and display unpackaged files
   list             ...  List all installed packages
   list NAME        ...  List files of installed package
   list PACK.mkp    ...  List files of uninstalled package file
   show NAME        ...  Show information about installed package
   show PACK.mkp    ...  Show information about uninstalled package file
   install PACK.mkp ...  Install or update package from file PACK.mkp
   remove NAME      ...  Uninstall package NAME
   disable NAME     ...  Disable package NAME
   enable NAME      ...  Enable previously disabled package NAME
   disable-outdated ...  Disable outdated packages

   -v  enables verbose output

Package files are located in %s.
"""
        % package_dir()
    )


def do_packaging(args: List[str]) -> None:
    if len(args) == 0:
        packaging_usage()
        sys.exit(1)
    command = args[0]
    args = args[1:]

    commands = {
        "create": package_create,
        "release": package_release,
        "list": package_list,
        "find": package_find,
        "show": package_info,
        "pack": package_pack,
        "remove": package_remove,
        "install": package_install,
        "disable": package_disable,
        "enable": package_enable,
        "disable-outdated": package_disable_outdated,
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


def package_list(args: List[str]) -> None:
    if len(args) > 0:
        for name in args:
            show_package_contents(name)
    else:
        if logger.isEnabledFor(VERBOSE):
            table = []
            for pacname in packaging.installed_names():
                package = read_package_info(pacname)
                if package is None:
                    table.append([pacname, "package info is missing or broken", "0"])
                else:
                    table.append(
                        [pacname, package["title"], str(packaging.package_num_files(package))]
                    )
            tty.print_table(["Name", "Title", "Files"], [tty.bold, "", ""], table)
        else:
            for pacname in packaging.installed_names():
                sys.stdout.write("%s\n" % pacname)


def package_info(args: List[str]) -> None:
    if len(args) == 0:
        raise PackageException("Usage: check_mk -P show NAME|PACKAGE.mkp")
    for name in args:
        show_package_info(name)


def show_package_contents(name: PackageName) -> None:
    show_package(name, False)


def show_package_info(name: PackageName) -> None:
    show_package(name, True)


def show_package(  # pylint: disable=too-many-branches
    name: PackageName,
    show_info: bool = False,
) -> None:
    try:
        if name.endswith(PACKAGE_EXTENSION):
            with tarfile.open(name, "r:gz") as tar:
                info = tar.extractfile("info")
            if info is None:
                raise PackageException('Failed to extract "info"')
            package = parse_package_info(info.read().decode())
        else:
            this_package = read_package_info(name)
            if not this_package:
                raise PackageException("No such package %s." % name)

            package = this_package
            if show_info:
                sys.stdout.write("Package file:                  %s\n" % (package_dir() / name))
    except PackageException:
        raise
    except Exception as e:
        raise PackageException("Cannot open package %s: %s" % (name, e))

    if show_info:
        sys.stdout.write("Name:                          %s\n" % package["name"])
        sys.stdout.write("Version:                       %s\n" % package["version"])
        sys.stdout.write("Packaged on Checkmk Version:   %s\n" % package["version.packaged"])
        sys.stdout.write("Required Checkmk Version:      %s\n" % package["version.min_required"])
        valid_until_text = package["version.usable_until"] or "No version limitation"
        sys.stdout.write("Valid until Checkmk version:   %s\n" % valid_until_text)
        sys.stdout.write("Title:                         %s\n" % package["title"])
        sys.stdout.write("Author:                        %s\n" % package["author"])
        sys.stdout.write("Download-URL:                  %s\n" % package["download_url"])
        files = " ".join(["%s(%d)" % (part, len(fs)) for part, fs in package["files"].items()])
        sys.stdout.write("Files:                         %s\n" % files)
        sys.stdout.write("Description:\n  %s\n" % package["description"])
    else:
        if logger.isEnabledFor(VERBOSE):
            sys.stdout.write("Files in package %s:\n" % name)
            for part in get_package_parts():
                if part_files := package["files"].get(part.ident, []):
                    sys.stdout.write("  %s%s%s:\n" % (tty.bold, part.title, tty.normal))
                    for f in part_files:
                        sys.stdout.write("    %s\n" % f)
        else:
            for part in get_package_parts():
                for fn in package["files"].get(part.ident, []):
                    sys.stdout.write(part.path + "/" + fn + "\n")


def package_create(args: List[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P create NAME")

    pacname = args[0]
    if read_package_info(pacname):
        raise PackageException("Package %s already existing." % pacname)

    logger.log(VERBOSE, "Creating new package %s...", pacname)
    package = get_initial_package_info(pacname)
    filelists = package["files"]
    for part in get_package_parts():
        files = unpackaged_files_in_dir(part.ident, part.path)
        filelists[part.ident] = files
        if len(files) > 0:
            logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
            for f in files:
                logger.log(VERBOSE, "    %s", f)

    write_package_info(package)
    logger.log(
        VERBOSE,
        "New package %s created with %d files.",
        pacname,
        packaging.package_num_files(package),
    )
    logger.log(
        VERBOSE,
        "Please edit package details in %s%s%s",
        tty.bold,
        package_dir() / pacname,
        tty.normal,
    )


def package_find(_no_args: List[str]) -> None:
    visited: AbstractSet[Path] = set()
    for part, files in unpackaged_files().items():
        if files:
            if not visited:
                logger.log(VERBOSE, "Unpackaged files:")

            found = frozenset(
                Path(part.path) / f for f in files if (Path(part.path) / f).resolve() not in visited
            )
            if found:
                logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
            for p in found:
                if logger.isEnabledFor(VERBOSE):
                    logger.log(VERBOSE, "    %s", p.relative_to(part.path))
                else:
                    logger.info("%s", p)
            visited |= {p.resolve() for p in found}

    if not visited:
        logger.log(VERBOSE, "No unpackaged files found.")


def package_release(args: List[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P release NAME")
    pacname = args[0]
    packaging.release(pacname)


def package_pack(args: List[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P pack NAME")

    # Make sure, user is not in data directories of Checkmk
    abs_curdir = os.path.abspath(os.curdir)
    for directory in [cmk.utils.paths.var_dir] + [
        p.path for p in get_package_parts() + get_config_parts()
    ]:
        if abs_curdir == directory or abs_curdir.startswith(directory + "/"):
            raise PackageException(
                "You are in %s!\n"
                "Please leave the directories of Check_MK before creating\n"
                "a packet file. Foreign files lying around here will mix up things." % abs_curdir
            )

    pacname = args[0]
    package = read_package_info(pacname)
    if not package:
        raise PackageException("Package %s not existing or corrupt." % pacname)
    tarfilename = packaging.format_file_name(name=pacname, version=package["version"])

    logger.log(VERBOSE, "Packing %s into %s...", pacname, tarfilename)
    with Path(tarfilename).open("wb") as f:
        packaging.write_file(package, cast(BinaryIO, f))
    logger.log(VERBOSE, "Successfully created %s", tarfilename)


def package_remove(args: List[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P remove NAME")
    pacname = args[0]
    package = read_package_info(pacname)
    if not package:
        raise PackageException("No such package %s." % pacname)

    logger.log(VERBOSE, "Removing package %s...", pacname)
    packaging.remove(package)
    logger.log(VERBOSE, "Successfully removed package %s.", pacname)


def package_install(args: List[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P install PACK.mkp")
    path = Path(args[0])
    if not path.exists():
        raise PackageException("No such file %s." % path)

    packaging.install_by_path(path)


def package_disable(args: List[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P disable NAME")
    package_name = args[0]
    package = read_package_info(package_name)
    if not package:
        raise PackageException("No such package %s." % package_name)

    packaging.disable(package_name, package)


def package_enable(args: List[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P enable PACK.mkp")
    packaging.enable(args[0])


def package_disable_outdated(args: List[str]) -> None:
    """Disable MKP packages that are declared to be outdated with the new version

    Since 1.6 there is the option version.usable_until available in MKP packages.
    Iterate over all installed packages, check that field and once it is set, compare
    the version with the new Checkmk version. In case it is outdated, move the
    package to the disabled packages.
    """
    if args:
        raise PackageException("Usage: check_mk -P disable-outdated")
    packaging.disable_outdated()
