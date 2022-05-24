#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import logging
import os
import pprint
import subprocess
import tarfile
import time
from contextlib import suppress
from io import BytesIO
from pathlib import Path
from typing import (
    Any,
    BinaryIO,
    Callable,
    cast,
    Dict,
    Final,
    Iterable,
    List,
    NamedTuple,
    Optional,
    TypedDict,
)

import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
import cmk.utils.werks
from cmk.utils.exceptions import MKException
from cmk.utils.i18n import _
from cmk.utils.log import VERBOSE
from cmk.utils.version import parse_check_mk_version

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation


# TODO: Subclass MKGeneralException()?
class PackageException(MKException):
    pass


logger = logging.getLogger("cmk.utils.packaging")


def _get_permissions(path: str) -> int:
    """Determine permissions by the first matching beginning of 'path'"""

    # order matters! See function _get_permissions
    perm_map = (
        (cmk.utils.paths.checks_dir, 0o644),
        (str(cmk.utils.paths.local_checks_dir), 0o644),
        (str(cmk.utils.paths.notifications_dir), 0o755),
        (str(cmk.utils.paths.local_notifications_dir), 0o755),
        (cmk.utils.paths.inventory_dir, 0o644),
        (str(cmk.utils.paths.local_inventory_dir), 0o644),
        (cmk.utils.paths.check_manpages_dir, 0o644),
        (str(cmk.utils.paths.local_check_manpages_dir), 0o644),
        (cmk.utils.paths.agents_dir, 0o755),
        (str(cmk.utils.paths.local_agents_dir), 0o755),
        (cmk.utils.paths.web_dir, 0o644),
        (str(cmk.utils.paths.local_web_dir), 0o644),
        (str(cmk.utils.paths.local_gui_plugins_dir), 0o644),
        (str(cmk.utils.paths.pnp_templates_dir), 0o644),
        (str(cmk.utils.paths.local_pnp_templates_dir), 0o644),
        (str(cmk.utils.paths.doc_dir), 0o644),
        (str(cmk.utils.paths.local_doc_dir), 0o644),
        (str(cmk.utils.paths.locale_dir), 0o644),
        (str(cmk.utils.paths.local_locale_dir), 0o644),
        (str(cmk.utils.paths.local_bin_dir), 0o755),
        (str(cmk.utils.paths.local_lib_dir / "nagios" / "plugins"), 0o755),
        (str(cmk.utils.paths.local_lib_dir), 0o644),
        (str(cmk.utils.paths.local_mib_dir), 0o644),
        (os.path.join(cmk.utils.paths.share_dir, "alert_handlers"), 0o755),
        (str(cmk.utils.paths.local_share_dir / "alert_handlers"), 0o755),
        (str(ec.mkp_rule_pack_dir()), 0o644),
    )
    for path_begin, perm in perm_map:
        if path.startswith(path_begin):
            return perm
    raise PackageException("could not determine permissions for %r" % path)


PackageName = str
PartName = str
PartPath = str
PartFiles = List[str]
PackageFiles = Dict[PartName, PartFiles]


class PackagePart(NamedTuple):
    ident: PartName
    title: str
    path: PartPath


# Would like to use class declaration here, but that is not compatible with the dots in the keys
# below.
PackageInfo = TypedDict(
    "PackageInfo",
    {
        "title": str,
        "name": str,
        "description": str,
        "version": str,
        "version.packaged": str,
        "version.min_required": str,
        "version.usable_until": Optional[str],
        "author": str,
        "download_url": str,
        "files": PackageFiles,
    },
)


Packages = Dict[PackageName, PackageInfo]
PackagePartInfo = Dict[PartName, Any]

package_ignored_files = {
    "lib": ["nagios/plugins/README.txt"],
}

PACKAGE_EXTENSION: Final[str] = ".mkp"


def package_dir() -> Path:
    return cmk.utils.paths.omd_root / "var/check_mk/packages"


def get_config_parts() -> List[PackagePart]:
    return [
        PackagePart("ec_rule_packs", _("Event Console rule packs"), str(ec.mkp_rule_pack_dir())),
    ]


def get_repo_ntop_parts() -> List[PackagePart]:
    # This function is meant to return the location of mkp-able ntop files within the git repository.
    # It is used for building a mkp which enables the ntop integration
    return [
        PackagePart("web", _("ntop GUI extensions"), "enterprise/cmk/gui/cee/"),
    ]


def get_package_parts() -> List[PackagePart]:
    return [
        PackagePart(
            "agent_based",
            _("Agent based plugins (Checks, Inventory)"),
            str(cmk.utils.paths.local_agent_based_plugins_dir),
        ),
        PackagePart("checks", _("Legacy check plugins"), str(cmk.utils.paths.local_checks_dir)),
        PackagePart(
            "inventory", _("Legacy inventory plugins"), str(cmk.utils.paths.local_inventory_dir)
        ),
        PackagePart(
            "checkman", _("Checks' man pages"), str(cmk.utils.paths.local_check_manpages_dir)
        ),
        PackagePart("agents", _("Agents"), str(cmk.utils.paths.local_agents_dir)),
        PackagePart(
            "notifications", _("Notification scripts"), str(cmk.utils.paths.local_notifications_dir)
        ),
        PackagePart("gui", _("GUI extensions"), str(cmk.utils.paths.local_gui_plugins_dir)),
        PackagePart("web", _("Legacy GUI extensions"), str(cmk.utils.paths.local_web_dir)),
        PackagePart(
            "pnp-templates",
            _("PNP4Nagios templates (deprecated)"),
            str(cmk.utils.paths.local_pnp_templates_dir),
        ),
        PackagePart("doc", _("Documentation files"), str(cmk.utils.paths.local_doc_dir)),
        PackagePart("locales", _("Localizations"), str(cmk.utils.paths.local_locale_dir)),
        PackagePart("bin", _("Binaries"), str(cmk.utils.paths.local_bin_dir)),
        PackagePart("lib", _("Libraries"), str(cmk.utils.paths.local_lib_dir)),
        PackagePart("mibs", _("SNMP MIBs"), str(cmk.utils.paths.local_mib_dir)),
        PackagePart(
            "alert_handlers",
            _("Alert handlers"),
            str(cmk.utils.paths.local_share_dir / "alert_handlers"),
        ),
    ]


def format_file_name(*, name: str, version: str) -> str:
    """
    >>> f = format_file_name

    >>> f(name="aaa", version="1.0")
    'aaa-1.0.mkp'

    >>> f(name="a-a-a", version="99.99")
    'a-a-a-99.99.mkp'

    """
    return f"{name}-{version}{PACKAGE_EXTENSION}"


def release(pacname: PackageName) -> None:
    if not pacname or not _package_exists(pacname):
        raise PackageException("Package %s not installed or corrupt." % pacname)

    package = read_package_info(pacname)
    if package is None:
        raise PackageException("Package %s not installed or corrupt." % pacname)
    logger.log(VERBOSE, "Releasing files of package %s into freedom...", pacname)
    for part in get_package_parts() + get_config_parts():
        filenames = package["files"].get(part.ident, [])
        if len(filenames) > 0:
            logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
            for f in filenames:
                logger.log(VERBOSE, "    %s", f)
            if part.ident == "ec_rule_packs":
                ec.release_packaged_rule_packs(filenames)
    _remove_package_info(pacname)


def _create_tar_info(filename: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo()
    info.mtime = int(time.time())
    info.uid = 0
    info.gid = 0
    info.size = size
    info.mode = 0o644
    info.type = tarfile.REGTYPE
    info.name = filename
    return info


def write_file(
    package: PackageInfo,
    file_object: Optional[BinaryIO] = None,
    package_parts: Callable = get_package_parts,
    config_parts: Callable = get_config_parts,
) -> None:
    package["version.packaged"] = cmk_version.__version__

    with tarfile.open(fileobj=file_object, mode="w:gz") as tar:

        def add_file(filename: str, data: bytes) -> None:
            info_file = BytesIO(data)
            info = _create_tar_info(filename, len(info_file.getvalue()))
            tar.addfile(info, info_file)

        # add the regular info file (Python format)
        add_file("info", pprint.pformat(package).encode())

        # add the info file a second time (JSON format) for external tools
        add_file("info.json", json.dumps(package).encode())

        # Now pack the actual files into sub tars
        for part in package_parts() + config_parts():
            filenames = package["files"].get(part.ident, [])
            if len(filenames) > 0:
                logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
                for f in filenames:
                    logger.log(VERBOSE, "    %s", f)
                subdata = subprocess.check_output(
                    ["tar", "cf", "-", "--dereference", "--force-local", "-C", part.path]
                    + filenames
                )
                add_file(part.ident + ".tar", subdata)


def get_initial_package_info(pacname: str) -> PackageInfo:
    return {
        "title": "Title of %s" % pacname,
        "name": pacname,
        "description": "Please add a description here",
        "version": "1.0",
        "version.packaged": cmk_version.__version__,
        "version.min_required": cmk_version.__version__,
        "version.usable_until": None,
        "author": "Add your name here",
        "download_url": "http://example.com/%s/" % pacname,
        "files": {},
    }


def remove(package: PackageInfo) -> None:
    for part in get_package_parts() + get_config_parts():
        filenames = package["files"].get(part.ident, [])
        if len(filenames) > 0:
            logger.log(VERBOSE, "  %s%s%s", tty.bold, part.title, tty.normal)
            if part.ident == "ec_rule_packs":
                _remove_packaged_rule_packs(filenames)
                continue
            for fn in filenames:
                logger.log(VERBOSE, "    %s", fn)
                try:
                    file_path = Path(part.path) / fn
                    file_path.unlink(missing_ok=True)
                except Exception as e:
                    if cmk.utils.debug.enabled():
                        raise
                    raise Exception("Cannot remove %s: %s\n" % (file_path, e))

    (package_dir() / package["name"]).unlink()

    _execute_post_package_change_actions(package)


def disable(package_name: PackageName, package_info: PackageInfo) -> None:
    """Moves a package to the "disabled packages" path

    It packs the installed files together, places the package in the
    disabled packages path and then removes the files from the site
    """
    logger.log(VERBOSE, "[%s]: Disable outdated package", package_name)

    base_dir = cmk.utils.paths.disabled_packages_dir
    base_dir.mkdir(parents=True, exist_ok=True)

    file_path = base_dir / format_file_name(name=package_name, version=package_info["version"])

    logger.log(VERBOSE, "[%s] Packing to %s...", package_name, file_path)
    with Path(file_path).open("wb") as f:
        write_file(package_info, f)

    logger.log(VERBOSE, "[%s] Removing packed files...", package_name)
    remove(package_info)

    logger.log(VERBOSE, "[%s] Successfully disabled", package_name)


def enable(file_name: str) -> None:
    """Installs a previously disabled package

    Installs the package from the disabled packages path and then removes
    that package file.

    Unlinke `disable` you have to provide the package file name
    (e.g. abc-1.2.3.mkp) of the
    package. This is required because there may be multiple versions of the
    same package name disabled at the same time.
    """
    file_path = cmk.utils.paths.disabled_packages_dir / file_name
    if not file_path.exists():
        raise PackageException("Package '%s' does not exist." % file_path)

    logger.log(VERBOSE, "[%s] Installing package", file_name)
    install_by_path(file_path)

    remove_disabled(file_name)

    logger.log(VERBOSE, "[%s] Successfully enabled", file_name)


def remove_disabled(file_name: str) -> None:
    logger.log(VERBOSE, "[%s] Removing package", file_name)
    (cmk.utils.paths.disabled_packages_dir / file_name).unlink()


def is_disabled(file_name: str) -> bool:
    return (cmk.utils.paths.disabled_packages_dir / file_name).exists()


def create(pkg_info: PackageInfo) -> None:
    pacname = pkg_info["name"]
    if _package_exists(pacname):
        raise PackageException("Packet already exists.")

    _validate_package_files(pacname, pkg_info["files"])
    write_package_info(pkg_info)


def edit(pacname: PackageName, new_package_info: PackageInfo) -> None:
    if not _package_exists(pacname):
        raise PackageException("No such package")

    # Renaming: check for collision
    if pacname != new_package_info["name"]:
        if _package_exists(new_package_info["name"]):
            raise PackageException(
                "Cannot rename package: a package with that name already exists."
            )

    _validate_package_files(pacname, new_package_info["files"])

    _remove_package_info(pacname)
    write_package_info(new_package_info)


def install_optional_package(package_file_name: Path) -> PackageInfo:
    if package_file_name not in [Path(p.name) for p in _get_optional_package_paths()]:
        raise PackageException("Optional package %s does not exist" % package_file_name)
    return install_by_path(cmk.utils.paths.optional_packages_dir / package_file_name)


def install_by_path(package_path: Path) -> PackageInfo:
    with package_path.open("rb") as f:
        return install(file_object=cast(BinaryIO, f))


def install(file_object: BinaryIO) -> PackageInfo:
    package = _get_package_info_from_package(file_object)
    file_object.seek(0)

    _verify_check_mk_version(package)

    pacname = package["name"]
    old_package = read_package_info(pacname)
    if old_package:
        logger.log(
            VERBOSE,
            "Updating %s from version %s to %s.",
            pacname,
            old_package["version"],
            package["version"],
        )
        update = True
    else:
        logger.log(VERBOSE, "Installing %s version %s.", pacname, package["version"])
        update = False

    # Before installing check for conflicts
    keep_files = {}
    for part in get_package_parts() + get_config_parts():
        packaged = _packaged_files_in_dir(part.ident)
        keep: List[str] = []
        keep_files[part.ident] = keep

        if update and old_package is not None:
            old_files = old_package["files"].get(part.ident, [])

        for fn in package["files"].get(part.ident, []):
            path = os.path.join(part.path, fn)
            if update and fn in old_files:
                keep.append(fn)
            elif fn in packaged:
                raise PackageException("File conflict: %s is part of another package." % path)
            elif os.path.exists(path):
                raise PackageException("File conflict: %s already existing." % path)

    with tarfile.open(fileobj=file_object, mode="r:gz") as tar:
        # Now install files, but only unpack files explicitely listed
        for part in get_package_parts() + get_config_parts():
            filenames = package["files"].get(part.ident, [])
            if len(filenames) > 0:
                logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
                for fn in filenames:
                    logger.log(VERBOSE, "    %s", fn)

                # make sure target directory exists
                if not os.path.exists(part.path):
                    logger.log(VERBOSE, "    Creating directory %s", part.path)
                    os.makedirs(part.path)

                tarsource = tar.extractfile(part.ident + ".tar")
                if tarsource is None:
                    raise PackageException("Failed to open %s.tar" % part.ident)

                # Important: Do not preserve the tared timestamp. Checkmk needs to know when the files
                # been installed for cache invalidation.
                with subprocess.Popen(
                    ["tar", "xf", "-", "--touch", "-C", part.path] + filenames,
                    stdin=subprocess.PIPE,
                    shell=False,
                    close_fds=True,
                ) as tardest:
                    if tardest.stdin is None:
                        raise PackageException("Failed to open stdin")

                    while True:
                        data = tarsource.read(4096)
                        if not data:
                            break
                        tardest.stdin.write(data)

                # Fix permissions of extracted files
                for filename in filenames:
                    path = os.path.join(part.path, filename)
                    desired_perm = _get_permissions(path)
                    has_perm = os.stat(path).st_mode & 0o7777
                    if has_perm != desired_perm:
                        logger.log(
                            VERBOSE,
                            "    Fixing permissions of %s: %04o -> %04o",
                            path,
                            has_perm,
                            desired_perm,
                        )
                        os.chmod(path, desired_perm)

                if part.ident == "ec_rule_packs":
                    ec.add_rule_pack_proxies(filenames)

    # In case of an update remove files from old_package not present in new one
    if update and old_package is not None:
        for part in get_package_parts() + get_config_parts():
            filenames = old_package["files"].get(part.ident, [])
            keep = keep_files.get(part.ident, [])
            for fn in filenames:
                if fn not in keep:
                    path = os.path.join(part.path, fn)
                    logger.log(VERBOSE, "Removing outdated file %s.", path)
                    try:
                        with suppress(FileNotFoundError):
                            os.remove(path)
                    except Exception as e:
                        logger.error("Error removing %s: %s", path, e)

            if part.ident == "ec_rule_packs":
                to_remove = [fn for fn in filenames if fn not in keep]
                _remove_packaged_rule_packs(to_remove, delete_export=False)

    # Last but not least install package file
    write_package_info(package)

    _execute_post_package_change_actions(package)

    return package


def _remove_packaged_rule_packs(file_names: Iterable[str], delete_export: bool = True) -> None:
    """
    This function synchronizes the rule packs in rules.mk and the packaged rule packs
    of a MKP upon deletion of that MKP. When a modified or an unmodified MKP is
    deleted the exported rule pack and the rule pack in rules.mk are both deleted.
    """
    if not file_names:
        return

    rule_packs = list(ec.load_rule_packs())
    rule_pack_ids = [rp["id"] for rp in rule_packs]
    affected_ids = [os.path.splitext(fn)[0] for fn in file_names]

    for id_ in affected_ids:
        index = rule_pack_ids.index(id_)
        del rule_packs[index]
        if delete_export:
            ec.remove_exported_rule_pack(id_)
        rule_pack_ids.remove(id_)

    ec.save_rule_packs(rule_packs)


def _get_package_info_from_package(file_object: BinaryIO) -> PackageInfo:
    with tarfile.open(fileobj=file_object, mode="r:gz") as tar:
        package_info_file = tar.extractfile("info")
        if package_info_file is None:
            raise PackageException("Failed to open package info file")
        return parse_package_info(package_info_file.read().decode())


def _validate_package_files(pacname: PackageName, files: PackageFiles) -> None:
    """Packaged files must either be unpackaged or already belong to that package"""
    packages: Packages = {}
    for package_name in installed_names():
        package_info = read_package_info(package_name)
        if package_info is not None:
            packages[package_name] = package_info

    for part in get_package_parts():
        _validate_package_files_part(
            packages, pacname, part.ident, part.path, files.get(part.ident, [])
        )


def _validate_package_files_part(
    packages: Packages,
    pacname: PackageName,
    part: PartName,
    directory: PartPath,
    rel_paths: PartFiles,
) -> None:
    for rel_path in rel_paths:
        path = os.path.join(directory, rel_path)
        if not os.path.exists(path):
            raise PackageException("File %s does not exist." % path)

        for other_pacname, other_package_info in packages.items():
            for other_rel_path in other_package_info["files"].get(part, []):
                if other_rel_path == rel_path and other_pacname != pacname:
                    raise PackageException(
                        "File %s does already belong to package %s" % (path, other_pacname)
                    )


def _verify_check_mk_version(package: PackageInfo) -> None:
    """Checks whether or not the minimum required Check_MK version is older than the
    current Check_MK version. Raises an exception if not. When the Check_MK version
    can not be parsed or is a daily build, the check is simply passing without error."""

    min_version = _normalize_daily_version(package["version.min_required"])
    if min_version == "master":
        return  # can not check exact version

    version = _normalize_daily_version(str(cmk_version.__version__))
    if version == "master":
        return  # can not check exact version

    compatible = True
    try:
        compatible = parse_check_mk_version(min_version) <= parse_check_mk_version(version)
    except Exception:
        # Be compatible: When a version can not be parsed, then skip this check
        if cmk.utils.debug.enabled():
            raise
        return

    if not compatible:
        raise PackageException(
            "The package requires Check_MK version %s, "
            "but you have %s installed." % (min_version, version)
        )


def _normalize_daily_version(version: str) -> str:
    """Convert daily build versions to their branch name

    >>> n = _normalize_daily_version
    >>> n("2019.10.10")
    'master'

    >>> n("2019.10.10")
    'master'

    >>> n("1.2.4p1")
    '1.2.4p1'

    >>> n("1.5.0-2010.02.01")
    '1.5.0'

    >>> n("2.5.0-2010.02.01")
    '2.5.0'
    """
    if cmk.utils.misc.is_daily_build_version(version):
        return cmk.utils.misc.branch_of_daily_build(version)
    return version


def get_unpackaged_files() -> Dict[str, List[str]]:
    return {part.ident: files for part, files in unpackaged_files().items()}


def get_installed_package_infos() -> Dict[PackageName, Optional[PackageInfo]]:
    return {name: read_package_info(name) for name in installed_names()}


def get_optional_package_infos() -> Dict[str, PackageInfo]:
    return _get_package_infos(_get_optional_package_paths())


def _get_optional_package_paths() -> List[Path]:
    if not cmk.utils.paths.optional_packages_dir.exists():
        return []
    return list(cmk.utils.paths.optional_packages_dir.iterdir())


def get_disabled_package_infos() -> Dict[str, PackageInfo]:
    return _get_package_infos(_get_disabled_package_paths())


def _get_package_infos(paths: List[Path]) -> Dict[str, PackageInfo]:
    optional = {}
    for pkg_path in paths:
        with pkg_path.open("rb") as pkg:
            try:
                package_info = _get_package_info_from_package(cast(BinaryIO, pkg))
            except Exception:
                # Do not make broken files / packages fail the whole mechanism
                logger.error("[%s]: Failed to read package info, skipping", pkg_path, exc_info=True)
                continue
            optional[pkg_path.name] = package_info

    return optional


def _get_disabled_package_paths() -> List[Path]:
    if not cmk.utils.paths.disabled_packages_dir.exists():
        return []
    return list(cmk.utils.paths.disabled_packages_dir.iterdir())


def unpackaged_files() -> Dict[PackagePart, List[str]]:
    unpackaged = {}
    for part in get_package_parts() + get_config_parts():
        unpackaged[part] = unpackaged_files_in_dir(part.ident, part.path)
    return unpackaged


def package_part_info() -> PackagePartInfo:
    part_info: PackagePartInfo = {}
    for part in get_package_parts() + get_config_parts():
        try:
            files = os.listdir(part.path)
        except OSError:
            files = []

        part_info[part.ident] = {
            "title": part.title,
            "permissions": list(map(_get_permissions, [os.path.join(part.path, f) for f in files])),
            "path": part.path,
            "files": files,
        }

    return part_info


def read_package_info(pacname: PackageName) -> Optional[PackageInfo]:
    pkg_info_path = package_dir() / pacname
    try:
        with pkg_info_path.open("r", encoding="utf-8") as f:
            package = parse_package_info(f.read())
        package["name"] = pacname  # do not trust package content
        return package
    except IOError:
        return None
    except Exception as e:
        logger.log(
            VERBOSE,
            "Ignoring invalid package file '%s'. Please remove it from %s! Error: %s",
            pkg_info_path,
            package_dir(),
            e,
        )
        return None


def package_num_files(package: PackageInfo) -> int:
    return sum([len(fl) for fl in package["files"].values()])


def _files_in_dir(part: str, directory: str, prefix: str = "") -> List[str]:
    if directory is None or not os.path.exists(directory):
        return []

    # Handle case where one part-directory lies below another
    taboo_dirs = {p.path for p in get_package_parts() + get_config_parts() if p.ident != part}
    # os.path.realpath would resolve /omd to /opt/omd ...
    taboo_dirs |= {p.replace("lib/check_mk", "lib/python3/cmk") for p in taboo_dirs}
    if directory in taboo_dirs:
        return []

    result: List[str] = []
    files = os.listdir(directory)
    for f in files:
        if f in [".", ".."] or f.startswith(".") or f.endswith("~") or f.endswith(".pyc"):
            continue

        ignored = package_ignored_files.get(part, [])
        if prefix + f in ignored:
            continue

        path = directory + "/" + f
        if os.path.isdir(path):
            result += _files_in_dir(part, path, prefix + f + "/")
        else:
            result.append(prefix + f)
    result.sort()
    return result


def unpackaged_files_in_dir(part: PartName, directory: str) -> List[str]:
    packaged = set(_packaged_files_in_dir(part))
    return [f for f in _files_in_dir(part, directory) if f not in packaged]


def _packaged_files_in_dir(part: PartName) -> List[str]:
    result: List[str] = []
    for pacname in installed_names():
        package = read_package_info(pacname)
        if package:
            result += package["files"].get(part, [])
    return result


def installed_names() -> List[PackageName]:
    return sorted([p.name for p in package_dir().iterdir()])


def _package_exists(pacname: PackageName) -> bool:
    return (package_dir() / pacname).exists()


def write_package_info(package: PackageInfo) -> None:
    pkg_info_path = package_dir() / package["name"]
    with pkg_info_path.open("w", encoding="utf-8") as f:
        f.write(pprint.pformat(package) + "\n")


def _remove_package_info(pacname: PackageName) -> None:
    (package_dir() / pacname).unlink()


def parse_package_info(python_string: str) -> PackageInfo:
    package_info = ast.literal_eval(python_string)
    package_info.setdefault("version.usable_until", None)
    return package_info


def rule_pack_id_to_mkp() -> Dict[str, Any]:
    """
    Returns a dictionary of rule pack ID to MKP package for a given package_info.
    Every rule pack is contained exactly once in this mapping. If no corresponding
    MKP exists, the value of that mapping is None.
    """

    def mkp_of(rule_pack_file: str) -> Any:
        """Find the MKP for the given file"""
        for package_name, package in get_installed_package_infos().items():
            if package and rule_pack_file in package.get("files", {}).get("ec_rule_packs", []):
                return package_name
        return None

    exported_rule_packs = package_part_info()["ec_rule_packs"]["files"]

    return {os.path.splitext(file_)[0]: mkp_of(file_) for file_ in exported_rule_packs}


def disable_outdated() -> None:
    """Check installed packages and disables the outdated ones

    Packages that contain a valid version number in the "version.usable_until" field can be disabled
    using this function. Others are not disabled.
    """
    for package_name in installed_names():
        logger.log(VERBOSE, "[%s]: Is it outdated?", package_name)
        package_info = read_package_info(package_name)
        if package_info is None:
            logger.log(VERBOSE, "[%s]: Failed to read package info, skipping", package_name)
            continue

        if not _is_outdated(package_name, package_info, cmk_version.__version__):
            logger.log(VERBOSE, "[%s]: Not disabling", package_name)
            continue

        logger.log(VERBOSE, "[%s]: Disable outdated package", package_name)
        disable(package_name, package_info)


def _is_outdated(package_name: PackageName, package_info: PackageInfo, version: str) -> bool:
    """Whether or not the given package is considered outated for the given Checkmk version

    >>> i = _is_outdated

    >>> i('a', {'version.usable_until': None}, '1.7.0i1')
    False

    >>> i('a', {'version.usable_until': '1.6.0'}, '1.7.0i1')
    True

    >>> i('a', {'version.usable_until': '1.7.0'}, '1.7.0i1')
    False

    >>> i('a', {'version.usable_until': '1.7.0i1'}, '1.7.0i1')
    True

    >>> i('a', {'version.usable_until': '1.7.0i1'}, '1.7.0i2')
    True

    >>> i('a', {'version.usable_until': '1.7.0'}, '1.7.0')
    True

    >>> i('a', {'version.usable_until': '2010.02.01'}, '1.7.0')
    False

    >>> i('a', {'version.usable_until': '1.7.0'}, '2010.02.01')
    False

    >>> i('a', {'version.usable_until': '1.6.0'}, '1.6.0-2010.02.01')
    True

    >>> i('a', {'version.usable_until': '1.6.0-2010.02.01'}, '1.6.0')
    True

    >>> i('a', {'version.usable_until': ''}, '1.6.0')
    False

    >>> i('a', {'version.usable_until': '1.6.0'}, '')
    False

    # Checkmk 1.6 shipped the first feature pack MKPs which sadly had no
    # "version.usable_until" attribute set. To be able to disable them automatically
    # we use a hard coded list of package names below. All of these packages start
    # with the version number "1.". To ensure the known and possible future packages
    # are removed, we consider the known packages to be outdated.

    >>> i('azure_ad', {'version': '1.0', 'version.usable_until': ''}, '1.7.0i1')
    True

    >>> i('prometheus', {'version': '1.3', 'version.usable_until': ''}, '1.7.0i1')
    True

    >>> i('prometheus', {'version': '2.0', 'version.usable_until': ''}, '1.7.0i1')
    False
    """
    until_version = package_info["version.usable_until"]

    if _is_16_feature_pack_package(package_name, package_info):
        logger.log(
            VERBOSE, "[%s]: This is a 1.6 feature pack package: It is outdated. ", package_name
        )
        return True

    if until_version is None:
        logger.log(VERBOSE, '[%s]: "Until version" is not set', package_name)
        return False

    # Normalize daily versions to branch version
    version = _normalize_daily_version(version)
    if version == "master":
        logger.log(
            VERBOSE, "[%s]: This is a daily build of master branch, can not decide", package_name
        )
        return False

    until_version = _normalize_daily_version(until_version)
    if until_version == "master":
        logger.log(
            VERBOSE, "[%s]: Until daily build of master branch, can not decide", package_name
        )
        return False

    try:
        is_outdated = parse_check_mk_version(version) >= parse_check_mk_version(until_version)
    except Exception:
        logger.log(
            VERBOSE,
            "[%s]: Could not compare until version %r with current version %r",
            package_name,
            until_version,
            version,
            exc_info=True,
        )
        return False

    logger.log(VERBOSE, "[%s]: %s > %s = %s", package_name, version, until_version, is_outdated)
    return is_outdated


def _is_16_feature_pack_package(package_name: PackageName, package_info: PackageInfo) -> bool:
    if package_name not in {
        "agent_rabbitmq",
        "azure_ad",
        "cisco_asa_sessions",
        "cisco_webex_teams_notifications",
        "couchbase",
        "fortigate_sslvpn",
        "graylog_special_agent",
        "huawei_switches",
        "jenkins_special_agent",
        "jira_special_agent",
        "k8s_extensions",
        "mongodb",
        "prometheus",
        "pulse_secure",
        "redis",
        "tplink_checks",
    }:
        return False

    return package_info.get("version", "").startswith("1.")


def _execute_post_package_change_actions(package: PackageInfo) -> None:
    _build_setup_search_index_background()

    if _package_contains_gui_files(package):
        _reload_apache()


def _build_setup_search_index_background() -> None:
    subprocess.run(
        ["init-redis"],
        check=False,
    )


def _package_contains_gui_files(package: PackageInfo) -> bool:
    return "gui" in package["files"] or "web" in package["files"]


def _reload_apache() -> None:
    try:
        subprocess.run(
            ["omd", "reload", "apache"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        logger.error("Error reloading apache", exc_info=True)
