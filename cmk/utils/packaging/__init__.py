#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import os
import shutil
import subprocess
import tarfile
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import suppress
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, cast, Final, NamedTuple, TypedDict

import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
import cmk.utils.werks
from cmk.utils.exceptions import MKException
from cmk.utils.i18n import _
from cmk.utils.log import VERBOSE
from cmk.utils.version import parse_check_mk_version

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from ._package import (
    get_initial_package_info,
    get_optional_package_info,
    PackageInfo,
    parse_package_info,
    serialize_package_info,
)


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
PartFiles = list[str]
PackageFiles = dict[PartName, PartFiles]


class PackagePart(NamedTuple):
    ident: PartName
    title: str
    path: PartPath


Packages = dict[PackageName, PackageInfo]
PackagePartInfo = dict[PartName, Any]

package_ignored_files = {
    "lib": ["nagios/plugins/README.txt"],
}

PACKAGE_EXTENSION: Final[str] = ".mkp"


def package_dir() -> Path:
    return cmk.utils.paths.omd_root / "var/check_mk/packages"


def get_config_parts() -> list[PackagePart]:
    return [
        PackagePart("ec_rule_packs", _("Event Console rule packs"), str(ec.mkp_rule_pack_dir())),
    ]


def get_repo_ntop_parts() -> list[PackagePart]:
    # This function is meant to return the location of mkp-able ntop files within the git repository.
    # It is used for building a mkp which enables the ntop integration
    return [
        PackagePart("web", _("ntop GUI extensions"), "enterprise/cmk/gui/cee/"),
    ]


def get_package_parts() -> list[PackagePart]:
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


def create_mkp_object(
    package: PackageInfo,
    package_parts: Callable = get_package_parts,
    config_parts: Callable = get_config_parts,
) -> bytes:
    package["version.packaged"] = cmk_version.__version__

    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:

        def add_file(filename: str, data: bytes) -> None:
            info_file = BytesIO(data)
            info = _create_tar_info(filename, len(info_file.getvalue()))
            tar.addfile(info, info_file)

        # add the regular info file (Python format)
        add_file("info", serialize_package_info(package).encode())

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

    return buffer.getvalue()


def uninstall(package: PackageInfo, post_package_change_actions: bool = True) -> None:
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
                    raise Exception(f"Cannot uninstall {file_path}: {e}\n")

    (package_dir() / package["name"]).unlink()

    if post_package_change_actions:
        _execute_post_package_change_actions(package)


class PackageStore:
    def __init__(self) -> None:
        self.local_packages: Final = cmk.utils.paths.local_optional_packages_dir
        self.shipped_packages: Final = cmk.utils.paths.optional_packages_dir

    def store(self, file_content: bytes) -> PackageInfo:

        package = _get_package_info_from_package(BytesIO(file_content))

        base_name = format_file_name(name=package["name"], version=package["version"])
        local_package_path = self.local_packages / base_name
        shipped_package_path = self.shipped_packages / base_name

        if local_package_path.exists() or shipped_package_path.exists():
            raise PackageException("Package '%s' already exists on the site!" % base_name)

        local_package_path.parent.mkdir(parents=True, exist_ok=True)
        store.save_bytes_to_file(str(local_package_path), file_content)

        return package

    def remove(self, package_name: str | Path) -> None:
        """Remove a local optional package file

        If the input is a `Path` (or `str` representing a path) only the base name is considered.
        """
        (self.local_packages / Path(package_name).name).unlink()

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


def read_package(package_file_base_name: str) -> bytes:
    return _get_full_package_path(package_file_base_name).read_bytes()


def disable(package_name: PackageName) -> None:
    package_path, package_meta_info = _find_path_and_package_info(package_name)

    if package_name in installed_names():
        uninstall(package_meta_info)

    package_path.unlink()


def _find_path_and_package_info(package_name: PackageName) -> tuple[Path, PackageInfo]:

    enabled_packages = get_enabled_package_infos()

    for package_path in _get_enabled_package_paths():
        if (package := enabled_packages.get(package_path.name)) is None:
            continue
        if (
            package["name"] == package_name
            or format_file_name(name=package["name"], version=package["version"]) == package_name
        ):
            return package_path, package

    raise PackageException("Package %s is not enabled" % package_name)


def create(pkg_info: PackageInfo) -> None:
    pacname = pkg_info["name"]
    if _package_exists(pacname):
        raise PackageException("Packet already exists.")

    _validate_package_files(pacname, pkg_info["files"])
    write_package_info(pkg_info)
    _create_enabled_mkp_from_installed_package(pkg_info)


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

    _create_enabled_mkp_from_installed_package(new_package_info)
    _remove_package_info(pacname)
    write_package_info(new_package_info)


def _create_enabled_mkp_from_installed_package(manifest: PackageInfo) -> None:
    """Creates an MKP, saves it on disk and enables it

    After we changed and or created an MKP, we must make sure it is present on disk as
    an MKP, just like the uploaded ones.
    """
    base_name = format_file_name(name=manifest["name"], version=manifest["version"])
    file_path = cmk.utils.paths.local_optional_packages_dir / base_name

    file_path.parent.mkdir(parents=True, exist_ok=True)

    mkp = create_mkp_object(manifest)
    file_path.write_bytes(mkp)

    mark_as_enabled(file_path)


def _get_full_package_path(package_file_name: str) -> Path:
    package_store = PackageStore()
    for package in package_store.list_local_packages() + package_store.list_shipped_packages():
        if package_file_name == package.name:
            return package
    raise PackageException("Optional package %s does not exist" % package_file_name)


def install_optional_package(package_file_base_name: str) -> PackageInfo:
    package_path = _get_full_package_path(package_file_base_name)
    try:
        with package_path.open("rb") as f:
            return install(file_object=f, allow_outdated=True)
    finally:
        # it is enabled, even if installing failed.
        mark_as_enabled(package_path)


def mark_as_enabled(package_path: Path) -> None:
    """Mark the package as one of the enabled ones

    Copying (or linking) the packages into the local hierarchy is the easiest way to get them to
    be synchronized with the remote sites.
    """
    destination = cmk.utils.paths.local_enabled_packages_dir / package_path.name

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
    base_name = format_file_name(name=package_info["name"], version=package_info["version"])
    (cmk.utils.paths.local_enabled_packages_dir / base_name).unlink(
        missing_ok=True
    )  # should never be missing, but don't crash in messed up state


def install(  # pylint: disable=too-many-branches
    file_object: BinaryIO,
    # I am not sure whether we should install outdated packages by default -- but
    #  a) this is the compatible way to go
    #  b) users cannot even modify packages without installing them
    # Reconsider!
    allow_outdated: bool = True,
    post_package_change_actions: bool = True,
) -> PackageInfo:
    package = _get_package_info_from_package(file_object)
    file_object.seek(0)

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
    else:
        logger.log(VERBOSE, "Installing %s version %s.", pacname, package["version"])

    _raise_for_installability(package, old_package, cmk_version.__version__, allow_outdated)

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
    if old_package is not None:
        for part in get_package_parts() + get_config_parts():
            new_files = set(package["files"].get(part.ident, []))
            old_files = set(old_package["files"].get(part.ident, []))
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
        _raise_for_too_new_cmk_version(package["name"], package, cmk_version.__version__)
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
    for part in get_package_parts() + get_config_parts():
        packaged = _packaged_files_in_dir(part.ident)

        old_files = set(old_package["files"].get(part.ident, [])) if old_package else set()

        for fn in package["files"].get(part.ident, []):
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


def _get_package_info_from_package(file_object: BinaryIO) -> PackageInfo:
    if (package := get_optional_package_info(file_object)) is None:
        raise PackageException("Failed to open package info file")
    return package


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
                        f"File {path} does already belong to package {other_pacname}"
                    )


def _raise_for_too_old_cmk_version(package: PackageInfo, site_version: str) -> None:
    """Checks whether or not the minimum required Check_MK version is older than the
    current Check_MK version. Raises an exception if not. When the Check_MK version
    can not be parsed or is a daily build, the check is simply passing without error."""

    min_version = _normalize_daily_version(package["version.min_required"])
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


def get_installed_package_infos() -> dict[PackageName, PackageInfo | None]:
    return {name: read_package_info(name) for name in installed_names()}


def get_optional_package_infos() -> Mapping[str, tuple[PackageInfo, bool]]:
    package_store = PackageStore()
    local_packages = package_store.list_local_packages()
    local_names = {p.name for p in local_packages}
    shipped_packages = (
        p for p in package_store.list_shipped_packages() if p.name not in local_names
    )
    return {
        **{k: (v, True) for k, v in _get_package_infos(local_packages).items()},
        **{k: (v, False) for k, v in _get_package_infos(shipped_packages).items()},
    }


def get_enabled_package_infos() -> Mapping[str, PackageInfo]:
    return _get_package_infos(_get_enabled_package_paths())


def _get_package_infos(paths: Iterable[Path]) -> Mapping[str, PackageInfo]:
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


def _get_enabled_package_paths():
    try:
        return list(cmk.utils.paths.local_enabled_packages_dir.iterdir())
    except FileNotFoundError:
        return []


def unpackaged_files() -> dict[PackagePart, list[str]]:
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


def read_package_info(pacname: PackageName) -> PackageInfo | None:
    pkg_info_path = package_dir() / pacname
    try:
        package = parse_package_info(pkg_info_path.read_text())
        package["name"] = pacname  # do not trust package content
        return package
    except OSError:
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
    return sum(len(fl) for fl in package["files"].values())


def _files_in_dir(part: str, directory: str, prefix: str = "") -> list[str]:
    if directory is None or not os.path.exists(directory):
        return []

    # Handle case where one part-directory lies below another
    taboo_dirs = {p.path for p in get_package_parts() + get_config_parts() if p.ident != part}
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
    for pacname in installed_names():
        package = read_package_info(pacname)
        if package:
            result += package["files"].get(part, [])
    return result


def installed_names() -> list[PackageName]:
    return sorted([p.name for p in package_dir().iterdir()])


def _package_exists(pacname: PackageName) -> bool:
    return (package_dir() / pacname).exists()


def write_package_info(package: PackageInfo) -> None:
    pkg_info_path = package_dir() / package["name"]
    pkg_info_path.write_text(serialize_package_info(package))


def _remove_package_info(pacname: PackageName) -> None:
    (package_dir() / pacname).unlink()


def rule_pack_id_to_mkp() -> dict[str, Any]:
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


def update_active_packages(log: logging.Logger) -> None:
    """Update which of the enabled packages are actually active (installed)"""
    _deinstall_inapplicable_active_packages(log, post_package_change_actions=False)
    _install_applicable_inactive_packages(log, post_package_change_actions=False)
    _execute_post_package_change_actions(None)


def _deinstall_inapplicable_active_packages(
    log: logging.Logger, *, post_package_change_actions: bool
) -> None:
    for package_name in sorted(installed_names()):
        package_info = read_package_info(package_name)
        if package_info is None:
            log.log(VERBOSE, "[%s]: Skipping (failed to read package info)", package_name)
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
    for package_path in _sort_enabled_packages_for_installation(log):

        try:
            with package_path.open("rb") as f:
                install(
                    file_object=f,
                    allow_outdated=False,
                    post_package_change_actions=post_package_change_actions,
                )
        except PackageException as exc:
            logger.log(VERBOSE, "[%s]: Not installed (%s)", package_path.name, exc)
        else:
            logger.log(VERBOSE, "[%s]: Installed", package_path.name)


def _sort_enabled_packages_for_installation(log: logging.Logger) -> Iterable[Path]:
    packages_by_name: dict[str, dict[str, Path]] = {}
    for pkg_path in _get_enabled_package_paths():
        with pkg_path.open("rb") as pkg:
            try:
                package_info = _get_package_info_from_package(pkg)
            except Exception:
                # Do not make broken files / packages fail the whole mechanism
                log.error(
                    "[%s]: Skipping (failed to read package info)",
                    pkg_path.name,
                    exc_info=True,
                )
                continue

        packages_by_name.setdefault(package_info["name"], {})[package_info["version"]] = pkg_path

    return _sort_by_name_then_newest_version(packages_by_name)


def _sort_by_name_then_newest_version(
    packages_by_name: Mapping[str, Mapping[str, Path]]
) -> Iterable[Path]:
    """
    >>> _sort_by_name_then_newest_version({
    ...    "boo_package": {"1.2": "old_boo", "1.3": "new_boo"},
    ...    "argl_extension": {"canoo": "lexically_first", "dling": "lexically_later"},
    ... })
    ['lexically_later', 'lexically_first', 'new_boo', 'old_boo']
    """
    return [
        paths_by_version[version]
        for name, paths_by_version in sorted(packages_by_name.items())
        for version in sorted(paths_by_version, key=_version_sort_key, reverse=True)
    ]


def _version_sort_key(raw: str) -> tuple[tuple[float, str], ...]:
    """Try our best to sort version strings

    They should only consist of dots and digits, but we try not to ever crash.
    This does the right thing for reasonable versions:

    >>> _version_sort_key("12.3")
    ((12, ''), (3, ''))
    >>> _version_sort_key("2022.09.03") < _version_sort_key("2022.8.21")
    False

    And it does not crash for nonsense values (which our GUI does not allow).
    Obviously that's not a meaningful result.

    >>> _version_sort_key("12.0-alpha")
    ((12, ''), (-inf, '0-alpha'))
    >>> _version_sort_key("12.0-alpha") >= _version_sort_key("käsebrot 3.0")
    True

    Reasonable ones are "newer":

    >>> _version_sort_key("wurstsalat") < _version_sort_key("0.1")
    True
    """
    key_elements: list[tuple[float, str]] = []
    for s in raw.split("."):
        try:
            key_elements.append((int(s), ""))
        except ValueError:
            key_elements.append((float("-Inf"), s))

    return tuple(key_elements)


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

        try:
            _raise_for_too_new_cmk_version(package_name, package_info, cmk_version.__version__)
        except PackageException as exc:
            logger.log(VERBOSE, "[%s]: Disable outdated package: %s", package_name, exc)
            disable(package_name)
        else:
            logger.log(VERBOSE, "[%s]: Not disabling", package_name)


def _raise_for_too_new_cmk_version(
    package_name: PackageName, package_info: PackageInfo, version: str
) -> None:
    """Raise an exception if a package is considered outated for the Checmk version

    >>> def i(*args):
    ...     try:
    ...         _raise_for_too_new_cmk_version(*args)
    ...     except:
    ...         return True
    ...     return False

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
        msg = "Outdated 1.6 feature pack package"
        logger.log(VERBOSE, "[%s]: %s", package_name, msg)
        raise PackageException(msg)

    if until_version is None:
        logger.log(VERBOSE, '[%s]: "Until version" is not set', package_name)
        return

    # Normalize daily versions to branch version
    version = _normalize_daily_version(version)
    if version == "master":
        logger.log(
            VERBOSE, "[%s]: This is a daily build of master branch, can not decide", package_name
        )
        return

    until_version = _normalize_daily_version(until_version)
    if until_version == "master":
        logger.log(
            VERBOSE, "[%s]: Until daily build of master branch, can not decide", package_name
        )
        return

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
        return

    msg = "Package is {}: {} >= {}".format(
        "outdated" if is_outdated else "not outdated",
        version,
        until_version,
    )
    logger.log(VERBOSE, "[%s]: %s", package_name, msg)
    if is_outdated:
        raise PackageException(msg)


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
