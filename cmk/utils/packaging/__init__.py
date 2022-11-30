#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import shutil
import subprocess
import tarfile
import time
from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from io import BytesIO
from itertools import groupby
from pathlib import Path
from typing import Final, TypedDict

from typing_extensions import assert_never

import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
import cmk.utils.werks
from cmk.utils.i18n import _
from cmk.utils.log import VERBOSE
from cmk.utils.version import parse_check_mk_version

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from ._package import (
    extract_package_info,
    extract_package_info_optionally,
    package_info_template,
    PackageInfo,
    read_package_info_optionally,
)
from ._parts import CONFIG_PARTS, PACKAGE_PARTS, PackagePart, PartFiles, PartName, PartPath
from ._type_defs import PackageException, PackageID, PackageName, PackageVersion

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


PackageFiles = dict[PartName, PartFiles]


Packages = dict[PackageName, PackageInfo]


class PackagePartInfoElement(TypedDict):
    title: str
    permissions: Sequence[int]
    path: PartPath
    files: Sequence[str]


PackagePartInfo = dict[PartName, PackagePartInfoElement]

package_ignored_files = {
    "lib": ["nagios/plugins/README.txt"],
}

PACKAGE_EXTENSION: Final[str] = ".mkp"


def package_dir() -> Path:
    return cmk.utils.paths.omd_root / "var/check_mk/packages"


def get_installed_package_info(
    package_name: PackageName, log: logging.Logger | None = None
) -> PackageInfo | None:
    return read_package_info_optionally(
        package_dir() / package_name, logger if log is None else log
    )


def format_file_name(package_id: PackageID) -> str:
    """
    >>> package_id = PackageID(
    ...     name=PackageName("my_package"),
    ...     version=PackageVersion("1.0.2"),
    ... )

    >>> format_file_name(package_id)
    'my_package-1.0.2.mkp'

    """
    return f"{package_id.name}-{package_id.version}{PACKAGE_EXTENSION}"


def release(pacname: PackageName) -> None:
    if (package := get_installed_package_info(pacname)) is None:
        raise PackageException(f"Package {pacname} not installed or corrupt.")

    logger.log(VERBOSE, "Releasing files of package %s into freedom...", pacname)
    for part in PACKAGE_PARTS + CONFIG_PARTS:
        if not (filenames := package.files.get(part.ident, [])):
            continue

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


def create_mkp_object(package: PackageInfo) -> bytes:

    package.version_packaged = cmk_version.__version__

    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:

        def add_file(filename: str, data: bytes) -> None:
            info = _create_tar_info(filename, len(data))
            tar.addfile(info, BytesIO(data))

        # add the regular info file (Python format)
        add_file("info", package.file_content().encode())

        # add the info file a second time (JSON format) for external tools
        add_file("info.json", package.json_file_content().encode())

        # Now pack the actual files into sub tars
        for part in PACKAGE_PARTS + CONFIG_PARTS:
            if not (filenames := package.files.get(part.ident, [])):
                continue

            logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
            for f in filenames:
                logger.log(VERBOSE, "    %s", f)
            subdata = subprocess.check_output(
                ["tar", "cf", "-", "--dereference", "--force-local", "-C", part.path] + filenames
            )
            add_file(part.ident + ".tar", subdata)

    return buffer.getvalue()


def uninstall(package: PackageInfo, post_package_change_actions: bool = True) -> None:
    for part in PACKAGE_PARTS + CONFIG_PARTS:
        if not (filenames := package.files.get(part.ident, [])):
            continue

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
                raise Exception(f"Cannot uninstall {file_path}: {e}\n")

    (package_dir() / package.name).unlink()

    if post_package_change_actions:
        _execute_post_package_change_actions(package)


class PackageStore:
    """Manage packages that are stored on the site

    This should become the single source of truth regarding package contents.
    """

    def __init__(self) -> None:
        self.local_packages: Final = cmk.utils.paths.local_optional_packages_dir
        self.shipped_packages: Final = cmk.utils.paths.optional_packages_dir

    def store(self, file_content: bytes) -> PackageInfo:

        package = extract_package_info(file_content)

        base_name = format_file_name(package.id)
        local_package_path = self.local_packages / base_name
        shipped_package_path = self.shipped_packages / base_name

        if local_package_path.exists() or shipped_package_path.exists():
            raise PackageException("Package '%s' already exists on the site!" % base_name)

        local_package_path.parent.mkdir(parents=True, exist_ok=True)
        store.save_bytes_to_file(str(local_package_path), file_content)

        return package

    def remove(self, package_id: PackageID) -> None:
        """Remove a local optional package file"""
        (self.local_packages / format_file_name(package_id)).unlink()

    def list_local_packages(self) -> list[Path]:
        try:
            return list(self.local_packages.iterdir())
        except FileNotFoundError:
            return []

    def list_shipped_packages(self) -> list[Path]:
        try:
            return list(self.shipped_packages.iterdir())
        except FileNotFoundError:
            return []


# TODO: this can go
def read_package(package_store: PackageStore, package_id: PackageID) -> bytes:
    return _get_full_package_path(package_store, package_id).read_bytes()


def disable(package_name: PackageName, package_version: PackageVersion | None) -> None:
    package_path, package_meta_info = _find_path_and_package_info(package_name, package_version)

    if (installed := get_installed_package_info(package_name)) is not None:
        if package_version is None or installed.version == package_version:
            uninstall(package_meta_info)

    package_path.unlink()


def _find_path_and_package_info(
    package_name: PackageName, package_version: PackageVersion | None
) -> tuple[Path, PackageInfo]:

    # not sure if we need this, but better safe than sorry.
    def filename_matches(package: PackageInfo, name: str) -> bool:
        return format_file_name(package.id) == name

    def package_matches(
        package: PackageInfo, package_name: PackageName, package_version: PackageVersion | None
    ) -> bool:
        return package.name == package_name and (
            package_version is None or package.version == package_version
        )

    enabled_packages = get_enabled_package_infos()

    matching_packages = [
        (package_path, package)
        for package_path in _get_enabled_package_paths()
        if (package := enabled_packages.get(package_path.name)) is not None
        and (
            package_matches(package, package_name, package_version)
            or filename_matches(package, package_name)
        )
    ]

    package_str = f"{package_name}" + ("" if package_version is None else f" {package_version}")
    if not matching_packages:
        raise PackageException(f"Package {package_str} is not enabled")
    if len(matching_packages) > 1:
        raise PackageException(f"Package not unique: {package_str}")

    return matching_packages[0]


def create(pkg_info: PackageInfo) -> None:
    if _package_exists(pkg_info.name):
        raise PackageException("Packet already exists.")

    _validate_package_files(pkg_info.name, pkg_info.files)
    write_package_info(pkg_info)
    _create_enabled_mkp_from_installed_package(pkg_info)


def edit(pacname: PackageName, new_package_info: PackageInfo) -> None:
    if not _package_exists(pacname):
        raise PackageException("No such package")

    # Renaming: check for collision
    if pacname != new_package_info.name:
        if _package_exists(new_package_info.name):
            raise PackageException(
                "Cannot rename package: a package with that name already exists."
            )

    _validate_package_files(pacname, new_package_info.files)

    _create_enabled_mkp_from_installed_package(new_package_info)
    _remove_package_info(pacname)
    write_package_info(new_package_info)


def _create_enabled_mkp_from_installed_package(manifest: PackageInfo) -> None:
    """Creates an MKP, saves it on disk and enables it

    After we changed and or created an MKP, we must make sure it is present on disk as
    an MKP, just like the uploaded ones.
    """
    base_name = format_file_name(manifest.id)
    file_path = cmk.utils.paths.local_optional_packages_dir / base_name

    file_path.parent.mkdir(parents=True, exist_ok=True)

    mkp = create_mkp_object(manifest)
    file_path.write_bytes(mkp)

    mark_as_enabled(file_path)


# TODO: this belongs to PackageStore.
def _get_full_package_path(package_store: PackageStore, package_id: PackageID) -> Path:
    package_file_name = format_file_name(package_id)
    for package in package_store.list_local_packages() + package_store.list_shipped_packages():
        if package_file_name == package.name:
            return package
    raise PackageException("Optional package %s does not exist" % package_file_name)


def install_optional_package(package_store: PackageStore, package_id: PackageID) -> PackageInfo:
    return install(
        _get_full_package_path(package_store, package_id),
        allow_outdated=True,
    )


def mark_as_enabled(package_path: Path) -> None:
    """Mark the package as one of the enabled ones

    Copying (or linking) the packages into the local hierarchy is the easiest way to get them to
    be synchronized with the remote sites.
    """
    destination = cmk.utils.paths.local_enabled_packages_dir / package_path.name

    # hack: we might be installing from the path to an already enabled package :-(
    if destination == package_path:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)

    # linking fails if the destination exists
    destination.unlink(missing_ok=True)

    try:
        os.link(str(package_path), str(destination))
    except OSError:
        # if the source belongs to root (as the shipped packages do) we may not be allowed
        # to hardlink them. We fall back to copying.
        shutil.copy(str(package_path), str(destination))


def remove_enabled_mark(package_info: PackageInfo) -> None:
    base_name = format_file_name(package_info.id)
    (cmk.utils.paths.local_enabled_packages_dir / base_name).unlink(
        missing_ok=True
    )  # should never be missing, but don't crash in messed up state


def install(
    package_path: Path,
    allow_outdated: bool = True,
    post_package_change_actions: bool = True,
) -> PackageInfo:
    try:
        return _install(
            package_path.read_bytes(),
            allow_outdated=allow_outdated,
            post_package_change_actions=post_package_change_actions,
        )
    finally:
        # it is enabled, even if installing failed
        mark_as_enabled(package_path)


def _install(  # pylint: disable=too-many-branches
    mkp: bytes,
    # I am not sure whether we should install outdated packages by default -- but
    #  a) this is the compatible way to go
    #  b) users cannot even modify packages without installing them
    # Reconsider!
    *,
    allow_outdated: bool,
    post_package_change_actions: bool,
) -> PackageInfo:
    package = extract_package_info(mkp)

    if old_package := get_installed_package_info(package.name):
        logger.log(
            VERBOSE,
            "Updating %s from version %s to %s.",
            package.name,
            old_package.version,
            package.version,
        )
    else:
        logger.log(VERBOSE, "Installing %s version %s.", package.name, package.version)

    _raise_for_installability(package, old_package, cmk_version.__version__, allow_outdated)

    with tarfile.open(fileobj=BytesIO(mkp), mode="r:gz") as tar:
        # Now install files, but only unpack files explicitely listed
        for part in PACKAGE_PARTS + CONFIG_PARTS:
            if not (filenames := package.files.get(part.ident, [])):
                continue

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
    if old_package is not None:
        for part in PACKAGE_PARTS + CONFIG_PARTS:
            new_files = set(package.files.get(part.ident, []))
            old_files = set(old_package.files.get(part.ident, []))
            remove_files = old_files - new_files
            for fn in remove_files:
                path = os.path.join(part.path, fn)
                logger.log(VERBOSE, "Removing outdated file %s.", path)
                try:
                    with suppress(FileNotFoundError):
                        os.remove(path)
                except Exception as e:
                    logger.error("Error removing %s: %s", path, e)

            if part.ident == "ec_rule_packs":
                _remove_packaged_rule_packs(list(remove_files), delete_export=False)

        remove_enabled_mark(old_package)

    # Last but not least install package file
    write_package_info(package)

    if post_package_change_actions:
        _execute_post_package_change_actions(package)

    return package


def _raise_for_installability(
    package: PackageInfo,
    old_package: PackageInfo | None,
    site_version: str,
    allow_outdated: bool,
) -> None:
    """Raise a `PackageException` if we should not install this package.

    Note: this currently ignores the packages "max version".
    """
    _raise_for_too_old_cmk_version(package, site_version)
    if not allow_outdated:
        _raise_for_too_new_cmk_version(package, cmk_version.__version__)
    _raise_for_conflicts(package, old_package)


def _raise_for_conflicts(
    package: PackageInfo,
    old_package: PackageInfo | None,
) -> None:
    for file_path, type_of_collision in _conflicting_files(package, old_package):
        raise PackageException(f"File conflict: {file_path} ({type_of_collision})")


def _conflicting_files(
    package: PackageInfo,
    old_package: PackageInfo | None,
) -> Iterable[tuple[str, str]]:
    # Before installing check for conflicts
    for part in PACKAGE_PARTS + CONFIG_PARTS:
        packaged = _packaged_files_in_dir(part.ident)

        old_files = set(old_package.files.get(part.ident, [])) if old_package else set()

        for fn in package.files.get(part.ident, []):
            if fn in old_files:
                continue
            path = os.path.join(part.path, fn)
            if fn in packaged:
                yield path, "part of another package"
            elif os.path.exists(path):
                yield path, "already existing"


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


def _validate_package_files(pacname: PackageName, files: PackageFiles) -> None:
    """Packaged files must either be unpackaged or already belong to that package"""
    packages = {
        package_name: package_info
        for package_name in installed_names()
        if (package_info := get_installed_package_info(package_name)) is not None
    }

    for part in PACKAGE_PARTS:
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
            for other_rel_path in other_package_info.files.get(part, []):
                if other_rel_path == rel_path and other_pacname != pacname:
                    raise PackageException(
                        f"File {path} does already belong to package {other_pacname}"
                    )


def _raise_for_too_old_cmk_version(package: PackageInfo, site_version: str) -> None:
    """Checks whether or not the minimum required Check_MK version is older than the
    current Check_MK version. Raises an exception if not. When the Check_MK version
    can not be parsed or is a daily build, the check is simply passing without error."""

    min_version = _normalize_daily_version(package.version_min_required)
    if min_version == "master":
        return  # can not check exact version

    version = _normalize_daily_version(site_version)
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


def get_unpackaged_files() -> dict[str, list[str]]:
    return {part.ident: files for part, files in unpackaged_files().items()}


def get_installed_package_infos() -> Mapping[PackageID, PackageInfo]:
    return {
        manifest.id: manifest
        for name in installed_names()
        if (manifest := get_installed_package_info(name)) is not None
    }


def get_optional_package_infos(
    package_store: PackageStore,
) -> Mapping[PackageID, tuple[PackageInfo, bool]]:
    local_packages = package_store.list_local_packages()
    local_names = {p.name for p in local_packages}
    shipped_packages = (
        p for p in package_store.list_shipped_packages() if p.name not in local_names
    )
    return {
        **{k: (v, True) for k, v in _get_package_infos(local_packages).items()},
        **{k: (v, False) for k, v in _get_package_infos(shipped_packages).items()},
    }


def get_enabled_package_infos() -> Mapping[PackageID, PackageInfo]:
    return _get_package_infos(_get_enabled_package_paths())


def _get_package_infos(paths: Iterable[Path]) -> Mapping[PackageID, PackageInfo]:
    return {
        package_info.id: package_info
        for pkg_path in paths
        if (package_info := extract_package_info_optionally(pkg_path, logger)) is not None
    }


def _get_enabled_package_paths():
    try:
        return list(cmk.utils.paths.local_enabled_packages_dir.iterdir())
    except FileNotFoundError:
        return []


def unpackaged_files() -> dict[PackagePart, list[str]]:
    unpackaged = {}
    for part in PACKAGE_PARTS + CONFIG_PARTS:
        unpackaged[part] = unpackaged_files_in_dir(part.ident, part.path)
    return unpackaged


def package_part_info() -> PackagePartInfo:
    part_info: PackagePartInfo = {}
    for part in PACKAGE_PARTS + CONFIG_PARTS:
        try:
            files = os.listdir(part.path)
        except OSError:
            files = []

        part_info[part.ident] = {
            "title": part.title,
            "permissions": [_get_permissions(os.path.join(part.path, f)) for f in files],
            "path": part.path,
            "files": files,
        }

    return part_info


def package_num_files(package: PackageInfo) -> int:
    return sum(len(fl) for fl in package.files.values())


def _files_in_dir(part: str, directory: str, prefix: str = "") -> list[str]:
    if directory is None or not os.path.exists(directory):
        return []

    # Handle case where one part-directory lies below another
    taboo_dirs = {p.path for p in PACKAGE_PARTS + CONFIG_PARTS if p.ident != part}
    # os.path.realpath would resolve /omd to /opt/omd ...
    taboo_dirs |= {p.replace("lib/check_mk", "lib/python3/cmk") for p in taboo_dirs}
    if directory in taboo_dirs:
        return []

    result: list[str] = []
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


def unpackaged_files_in_dir(part: PartName, directory: str) -> list[str]:
    packaged = set(_packaged_files_in_dir(part))
    return [f for f in _files_in_dir(part, directory) if f not in packaged]


def _packaged_files_in_dir(part: PartName) -> list[str]:
    result: list[str] = []
    for package_name in installed_names():
        if (package := get_installed_package_info(package_name)) is not None:
            result += package.files.get(part, [])
    return result


def installed_names() -> list[PackageName]:
    return sorted(PackageName(p.name) for p in package_dir().iterdir())


def _package_exists(pacname: PackageName) -> bool:
    return (package_dir() / pacname).exists()


def write_package_info(package: PackageInfo) -> None:
    pkg_info_path = package_dir() / package.name
    pkg_info_path.write_text(package.file_content())


def _remove_package_info(pacname: PackageName) -> None:
    (package_dir() / pacname).unlink()


def rule_pack_id_to_mkp() -> dict[str, PackageName | None]:
    """
    Returns a dictionary of rule pack ID to MKP package for a given package_info.
    Every rule pack is contained exactly once in this mapping. If no corresponding
    MKP exists, the value of that mapping is None.
    """

    def mkp_of(rule_pack_file: str) -> PackageName | None:
        """Find the MKP for the given file"""
        for package_id, package_info in get_installed_package_infos().items():
            if rule_pack_file in package_info.files.get("ec_rule_packs", []):
                return package_id.name
        return None

    exported_rule_packs = package_part_info()["ec_rule_packs"]["files"]

    return {os.path.splitext(file_)[0]: mkp_of(file_) for file_ in exported_rule_packs}


def update_active_packages(log: logging.Logger) -> None:
    """Update which of the enabled packages are actually active (installed)"""
    _deinstall_inapplicable_active_packages(log, post_package_change_actions=False)
    _install_applicable_inactive_packages(log, post_package_change_actions=False)
    _execute_post_package_change_actions(None)


def _deinstall_inapplicable_active_packages(
    log: logging.Logger, *, post_package_change_actions: bool
) -> None:
    for package_name in sorted(installed_names()):
        if (package_info := get_installed_package_info(package_name, log)) is None:
            continue  # leave broken/corrupt packages alone.

        try:
            _raise_for_installability(
                package_info,
                package_info,
                cmk_version.__version__,
                allow_outdated=False,
            )
        except PackageException as exc:
            log.log(VERBOSE, "[%s]: Uninstalling (%s)", package_name, exc)
            uninstall(package_info, post_package_change_actions=post_package_change_actions)
        else:
            log.log(VERBOSE, "[%s]: Kept", package_name)


def _install_applicable_inactive_packages(
    log: logging.Logger, *, post_package_change_actions: bool
) -> None:
    for name, package_paths in _sort_enabled_packages_for_installation(log):
        for package_info, path in package_paths:
            try:
                install(
                    path,
                    allow_outdated=False,
                    post_package_change_actions=post_package_change_actions,
                )
            except PackageException as exc:
                log.log(
                    VERBOSE, "[%s]: Version %s not installed (%s)", name, package_info.version, exc
                )
            else:
                log.log(VERBOSE, "[%s]: Version %s installed", name, package_info.version)
                # We're done with this package.
                # Do not try to install older versions, or the installation function will
                # silently downgrade the package.
                break


def _sort_enabled_packages_for_installation(
    log: logging.Logger,
) -> Iterable[tuple[PackageName, Iterable[tuple[PackageInfo, Path]]]]:
    packages = [
        (package_info, package_path)
        for package_path in _get_enabled_package_paths()
        if (package_info := extract_package_info_optionally(package_path, log)) is not None
    ]
    return groupby(
        sorted(
            sorted(packages, key=lambda x: x[0].version.sort_key, reverse=True),
            key=lambda x: x[0].name,
        ),
        key=lambda x: x[0].name,
    )


def disable_outdated() -> None:
    """Check installed packages and disables the outdated ones

    Packages that contain a valid version number in the "version.usable_until" field can be disabled
    using this function. Others are not disabled.
    """
    for package_name in installed_names():
        logger.log(VERBOSE, "[%s]: Is it outdated?", package_name)
        if (package_info := get_installed_package_info(package_name)) is None:
            continue

        try:
            _raise_for_too_new_cmk_version(package_info, cmk_version.__version__)
        except PackageException as exc:
            logger.log(VERBOSE, "[%s]: Disable outdated package: %s", package_name, exc)
            disable(package_name, package_info.version)
        else:
            logger.log(VERBOSE, "[%s]: Not disabling", package_name)


def _raise_for_too_new_cmk_version(package_info: PackageInfo, version: str) -> None:
    """Raise an exception if a package is considered outated for the Checmk version"""
    until_version = package_info.version_usable_until

    if until_version is None:
        logger.log(VERBOSE, '[%s]: "Until version" is not set', package_info.name)
        return

    # Normalize daily versions to branch version
    version = _normalize_daily_version(version)
    if version == "master":
        logger.log(
            VERBOSE,
            "[%s]: This is a daily build of master branch, can not decide",
            package_info.name,
        )
        return

    until_version = _normalize_daily_version(until_version)
    if until_version == "master":
        logger.log(
            VERBOSE, "[%s]: Until daily build of master branch, can not decide", package_info.name
        )
        return

    try:
        is_outdated = parse_check_mk_version(version) >= parse_check_mk_version(until_version)
    except Exception:
        logger.log(
            VERBOSE,
            "[%s]: Could not compare until version %r with current version %r",
            package_info.name,
            until_version,
            version,
            exc_info=True,
        )
        return

    msg = "Package is {}: {} >= {}".format(
        "outdated" if is_outdated else "not outdated",
        version,
        until_version,
    )
    logger.log(VERBOSE, "[%s]: %s", package_info.name, msg)
    if is_outdated:
        raise PackageException(msg)


def _execute_post_package_change_actions(package: PackageInfo | None) -> None:
    _build_setup_search_index_background()

    if package is None or _package_contains_gui_files(package):
        _reload_apache()


def _build_setup_search_index_background() -> None:
    subprocess.run(
        ["init-redis"],
        check=False,
    )


def _package_contains_gui_files(package: PackageInfo) -> bool:
    return "gui" in package.files or "web" in package.files


def _reload_apache() -> None:
    try:
        subprocess.run(
            ["omd", "reload", "apache"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        logger.error("Error reloading apache", exc_info=True)
