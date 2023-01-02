#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import sys
from pathlib import Path

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
import cmk.utils.werks
from cmk.utils.log import VERBOSE
from cmk.utils.packaging import (
    add_installed_manifest,
    cli,
    CONFIG_PARTS,
    create_mkp_object,
    disable,
    disable_outdated,
    format_file_name,
    get_enabled_manifests,
    get_installed_manifest,
    get_installed_manifests,
    get_unpackaged_files,
    install_optional_package,
    is_installed,
    Manifest,
    manifest_template,
    package_num_files,
    PACKAGE_PARTS,
    PackageException,
    PackageID,
    PackageName,
    PACKAGES_DIR,
    PackageStore,
    PackageVersion,
    release,
    update_active_packages,
)

logger = logging.getLogger("cmk.base.packaging")


def packaging_usage() -> None:
    sys.stdout.write(
        f"""Usage: check_mk [-v] -P|--package COMMAND [ARGS]

Available commands are:
   create NAME             ...  Collect unpackaged files into new package NAME
   pack NAME               ...  Create package file from installed package
   release NAME            ...  Drop installed package NAME, release packaged files
   find [-h] [-a] [--json] ...  Find and display unpackaged files
   inspect FILE            ...  Show manifest of an `.mkp` file.
   list                    ...  List all installed packages
   list NAME               ...  List files of installed package
   show NAME               ...  Show information about installed package
   install PACK.mkp        ...  Install or update package from file PACK.mkp
   remove NAME VERSION     ...  Uninstall and delete package NAME
   disable NAME [VERSION]  ...  Disable package NAME
   enable NAME VERSION     ...  Enable previously disabled package NAME
   disable-outdated        ...  Disable outdated packages
   update-active-packages  ...  Update the selection of active packages (according to Checkmk version)

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
        "create": package_create,
        "release": package_release,
        "list": package_list,
        "find": lambda args: cli.main(["find", *args], logger),
        "inspect": lambda args: cli.main(["inspect", *args], logger),
        "show": package_show,
        "pack": package_pack,
        "remove": package_remove,
        "disable": package_disable,
        "enable": package_enable,
        "disable-outdated": package_disable_outdated,
        "update-active-packages": package_update_active,
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


def package_create(args: list[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P create NAME")

    pacname = PackageName(args[0])
    if is_installed(pacname):
        raise PackageException(f"Package {pacname} already existing.")

    unpackaged = get_unpackaged_files()

    logger.log(VERBOSE, "Creating new package %s...", pacname)
    package = manifest_template(
        name=pacname,
        files={part: files_ for part in PACKAGE_PARTS if (files_ := unpackaged.get(part))},
    )
    for part, files in package.files.items():
        logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.ui_title, tty.normal)
        for f in files:
            logger.log(VERBOSE, "    %s", f)

    add_installed_manifest(package)
    logger.log(
        VERBOSE,
        "New package %s created with %d files.",
        pacname,
        package_num_files(package),
    )
    # TODO: why is this *vital* information only in verbose logging?!
    logger.log(
        VERBOSE,
        "Please edit package details in %s%s%s",
        tty.bold,
        PACKAGES_DIR / pacname,
        tty.normal,
    )


def package_release(args: list[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P release NAME")
    release(PackageName(args[0]))


def package_pack(args: list[str]) -> None:
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P pack NAME")

    # Make sure user is not in data directories of Checkmk
    abs_curdir = os.path.abspath(os.curdir)
    for directory in [
        cmk.utils.paths.var_dir,
        *(str(p.path) for p in PACKAGE_PARTS + CONFIG_PARTS),
    ]:
        if abs_curdir == directory or abs_curdir.startswith(directory + "/"):
            raise PackageException(
                "You are in %s!\n"
                "Please leave the directories of Check_MK before creating\n"
                "a packet file. Foreign files lying around here will mix up things." % abs_curdir
            )

    pacname = PackageName(args[0])
    if (package := get_installed_manifest(pacname)) is None:
        raise PackageException("Package %s not existing or corrupt." % pacname)

    try:
        _ = PackageVersion.parse_semver(package.version)
    except ValueError as exc:
        raise PackageException from exc

    tarfilename = format_file_name(package.id)

    logger.log(VERBOSE, "Packing %s into %s...", pacname, tarfilename)
    Path(tarfilename).write_bytes(create_mkp_object(package))
    logger.log(VERBOSE, "Successfully created %s", tarfilename)


def package_remove(args: list[str]) -> None:
    if len(args) != 2:
        raise PackageException("Usage: check_mk -P remove NAME VERSION")

    package_id = PackageID(name=PackageName(args[0]), version=PackageVersion(args[1]))
    if any(package_id == package.id for package in get_enabled_manifests().values()):
        raise PackageException("This package is enabled! Please disable it first.")

    logger.log(VERBOSE, "Removing package %s...", package_id.name)
    PackageStore().remove(package_id)
    logger.log(VERBOSE, "Successfully removed package %s.", package_id.name)


def package_disable(args: list[str]) -> None:
    if len(args) not in {1, 2}:
        raise PackageException("Usage: check_mk -P disable NAME [VERSION]")
    disable(PackageName(args[0]), PackageVersion(args[1]) if len(args) == 2 else None)


def package_enable(args: list[str]) -> None:
    if len(args) != 2:
        raise PackageException("Usage: check_mk -P enable NAME VERSION")
    package_id = PackageID(name=PackageName(args[0]), version=PackageVersion(args[1]))
    install_optional_package(PackageStore(), package_id)


def package_disable_outdated(args: list[str]) -> None:
    """Disable MKP packages that are declared to be outdated with the new version

    Since 1.6 there is the option version.usable_until available in MKP packages.
    Iterate over all installed packages, check that field and once it is set, compare
    the version with the new Checkmk version. In case it is outdated, move the
    package to the disabled packages.
    """
    if args:
        raise PackageException("Usage: check_mk -P disable-outdated")
    disable_outdated()


def package_update_active(args: list[str]) -> None:
    """Disable MKP packages that are not suitable for this version, and enable others

    Packages can declare their minimum or maximum required Checkmk versions.
    Also packages can collide with one another or fail to load for other reasons.

    This command disables all packages that are not applicable, and then enables the ones that are.
    """
    if args:
        raise PackageException("Usage: check_mk -P update-active")
    update_active_packages(logger)
