#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import logging
import sys
import tarfile
from typing import NamedTuple, List  # pylint: disable=unused-import
from pathlib2 import Path

# It's OK to import centralized config load logic
import cmk.ec.export  # pylint: disable=cmk-module-layer-violation
from cmk.utils.log import VERBOSE
import cmk.utils.paths
import cmk.utils.tty as tty
import cmk.utils.werks
import cmk.utils.debug
from cmk.utils.packaging import (
    PackageException,
    package_dir,
    all_package_names,
    read_package_info,
    write_package_info,
    parse_package_info,
    remove_package,
    install_package_by_path,
    release_package,
    get_package_parts,
    create_mkp_file,
    unpackaged_files_in_dir,
    get_config_parts,
    get_initial_package_info,
)

logger = logging.getLogger("cmk.base.packaging")
_pac_ext = ".mkp"


def packaging_usage():
    sys.stdout.write("""Usage: check_mk [-v] -P|--package COMMAND [ARGS]

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

   -v  enables verbose output

Package files are located in %s.
""" % package_dir())


def do_packaging(args):
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
    }
    f = commands.get(command)
    if f:
        try:
            f(args)
        except PackageException as e:
            logger.error("%s", e)
            sys.exit(1)
    else:
        allc = sorted(commands.keys())
        allc = [tty.bold + c + tty.normal for c in allc]
        logger.error("Invalid packaging command. Allowed are: %s and %s.", ", ".join(allc[:-1]),
                     allc[-1])
        sys.exit(1)


def package_list(args):
    if len(args) > 0:
        for name in args:
            show_package_contents(name)
    else:
        if logger.isEnabledFor(VERBOSE):
            table = []
            for pacname in all_package_names():
                package = read_package_info(pacname)
                table.append((pacname, package["title"], package["num_files"]))
            tty.print_table(["Name", "Title", "Files"], [tty.bold, "", ""], table)
        else:
            for pacname in all_package_names():
                sys.stdout.write("%s\n" % pacname)


def package_info(args):
    if len(args) == 0:
        raise PackageException("Usage: check_mk -P show NAME|PACKAGE.mkp")
    for name in args:
        show_package_info(name)


def show_package_contents(name):
    show_package(name, False)


def show_package_info(name):
    show_package(name, True)


def show_package(name, show_info=False):
    try:
        if name.endswith(_pac_ext):
            tar = tarfile.open(name, "r:gz")
            info = tar.extractfile("info")
            package = parse_package_info(info.read())
        else:
            package = read_package_info(name)
            if not package:
                raise PackageException("No such package %s." % name)
            if show_info:
                sys.stdout.write("Package file:                  %s%s\n" % (package_dir(), name))
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
        sys.stdout.write("Files:                         %s\n" % \
                " ".join([ "%s(%d)" % (part, len(fs)) for part, fs in package["files"].items() ]))
        sys.stdout.write("Description:\n  %s\n" % package["description"])
    else:
        if logger.isEnabledFor(VERBOSE):
            sys.stdout.write("Files in package %s:\n" % name)
            for part in get_package_parts():
                files = package["files"].get(part.ident, [])
                if len(files) > 0:
                    sys.stdout.write("  %s%s%s:\n" % (tty.bold, part.title, tty.normal))
                    for f in files:
                        sys.stdout.write("    %s\n" % f)
        else:
            for part in get_package_parts():
                for fn in package["files"].get(part.ident, []):
                    sys.stdout.write(part.path + "/" + fn + "\n")


def package_create(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P create NAME")

    pacname = args[0]
    if read_package_info(pacname):
        raise PackageException("Package %s already existing." % pacname)

    logger.log(VERBOSE, "Creating new package %s...", pacname)
    package = get_initial_package_info(pacname)
    filelists = package_info["files"]
    num_files = 0
    for part in get_package_parts():
        files = unpackaged_files_in_dir(part.ident, part.path)
        filelists[part.ident] = files
        num_files += len(files)
        if len(files) > 0:
            logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
            for f in files:
                logger.log(VERBOSE, "    %s", f)

    write_package_info(package)
    logger.log(VERBOSE, "New package %s created with %d files.", pacname, num_files)
    logger.log(VERBOSE, "Please edit package details in %s%s%s", tty.bold,
               package_dir() / pacname, tty.normal)


def package_find(_no_args):
    first = True
    for part in get_package_parts() + get_config_parts():
        files = unpackaged_files_in_dir(part.ident, part.path)
        if len(files) > 0:
            if first:
                logger.log(VERBOSE, "Unpackaged files:")
                first = False

            logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
            for f in files:
                if logger.isEnabledFor(VERBOSE):
                    logger.log(VERBOSE, "    %s", f)
                else:
                    logger.info("%s/%s", part.path, f)

    if first:
        logger.log(VERBOSE, "No unpackaged files found.")


def package_release(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P release NAME")
    pacname = args[0]
    release_package(pacname)


def package_pack(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P pack NAME")

    # Make sure, user is not in data directories of Check_MK
    abs_curdir = os.path.abspath(os.curdir)
    for directory in [cmk.utils.paths.var_dir
                     ] + [p.path for p in get_package_parts() + get_config_parts()]:
        if abs_curdir == directory or abs_curdir.startswith(directory + "/"):
            raise PackageException(
                "You are in %s!\n"
                "Please leave the directories of Check_MK before creating\n"
                "a packet file. Foreign files lying around here will mix up things." % abs_curdir)

    pacname = args[0]
    package = read_package_info(pacname)
    if not package:
        raise PackageException("Package %s not existing or corrupt." % pacname)
    tarfilename = "%s-%s%s" % (pacname, package["version"], _pac_ext)

    logger.log(VERBOSE, "Packing %s into %s...", pacname, tarfilename)
    with Path(tarfilename).open("wb") as f:
        create_mkp_file(package, f)
    logger.log(VERBOSE, "Successfully created %s", tarfilename)


def package_remove(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P remove NAME")
    pacname = args[0]
    package = read_package_info(pacname)
    if not package:
        raise PackageException("No such package %s." % pacname)

    logger.log(VERBOSE, "Removing package %s...", pacname)
    remove_package(package)
    logger.log(VERBOSE, "Successfully removed package %s.", pacname)


def package_install(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P install NAME")
    path = Path(args[0])
    if not path.exists():
        raise PackageException("No such file %s." % path)

    return install_package_by_path(path)
