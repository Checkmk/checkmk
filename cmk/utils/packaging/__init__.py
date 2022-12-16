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
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
import cmk.utils.werks
from cmk.utils.i18n import _
from cmk.utils.log import VERBOSE
from cmk.utils.version import is_daily_build_of_master, parse_check_mk_version

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from ._installed import (
    add_installed_manifest,
    get_installed_manifest,
    get_installed_manifests,
    get_packaged_files,
    is_installed,
    PACKAGES_DIR,
    remove_installed_manifest,
)
from ._manifest import extract_manifest, extract_manifest_optionally, Manifest, manifest_template
from ._parts import CONFIG_PARTS, PACKAGE_PARTS, PackagePart, PartFiles, PartName, PartPath
from ._type_defs import PackageException, PackageID, PackageName, PackageVersion

g_logger = logging.getLogger("cmk.utils.packaging")


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


Packages = dict[PackageName, Manifest]


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
    if (manifest := get_installed_manifest(pacname)) is None:
        raise PackageException(f"Package {pacname} not installed or corrupt.")

    g_logger.log(VERBOSE, "Releasing files of package %s into freedom...", pacname)
    for part in PACKAGE_PARTS + CONFIG_PARTS:
        if not (filenames := manifest.files.get(part.ident, [])):
            continue

        g_logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.ui_title, tty.normal)
        for f in filenames:
            g_logger.log(VERBOSE, "    %s", f)
        if part.ident == "ec_rule_packs":
            ec.release_packaged_rule_packs(filenames)

    remove_installed_manifest(pacname)


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


def create_mkp_object(manifest: Manifest) -> bytes:

    manifest.version_packaged = cmk_version.__version__

    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:

        def add_file(filename: str, data: bytes) -> None:
            info = _create_tar_info(filename, len(data))
            tar.addfile(info, BytesIO(data))

        # add the regular info file (Python format)
        add_file("info", manifest.file_content().encode())

        # add the info file a second time (JSON format) for external tools
        add_file("info.json", manifest.json_file_content().encode())

        # Now pack the actual files into sub tars
        for part in PACKAGE_PARTS + CONFIG_PARTS:
            if not (filenames := manifest.files.get(part.ident, [])):
                continue

            g_logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.ui_title, tty.normal)
            for f in filenames:
                g_logger.log(VERBOSE, "    %s", f)
            subdata = subprocess.check_output(
                ["tar", "cf", "-", "--dereference", "--force-local", "-C", part.path] + filenames
            )
            add_file(part.ident + ".tar", subdata)

    return buffer.getvalue()


def uninstall(manifest: Manifest, post_package_change_actions: bool = True) -> None:
    for part in PACKAGE_PARTS + CONFIG_PARTS:
        if not (filenames := manifest.files.get(part.ident, [])):
            continue

        g_logger.log(VERBOSE, "  %s%s%s", tty.bold, part.ui_title, tty.normal)
        if part.ident == "ec_rule_packs":
            _remove_packaged_rule_packs(filenames)
            continue
        for fn in filenames:
            g_logger.log(VERBOSE, "    %s", fn)
            try:
                file_path = Path(part.path) / fn
                file_path.unlink(missing_ok=True)
            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                raise Exception(f"Cannot uninstall {file_path}: {e}\n")

    remove_installed_manifest(manifest.name)

    if post_package_change_actions:
        _execute_post_package_change_actions(manifest)


class PackageStore:
    """Manage packages that are stored on the site

    This should become the single source of truth regarding package contents.
    """

    def __init__(self) -> None:
        self.local_packages: Final = cmk.utils.paths.local_optional_packages_dir
        self.shipped_packages: Final = cmk.utils.paths.optional_packages_dir

    def store(self, file_content: bytes) -> Manifest:

        package = extract_manifest(file_content)

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

    def get_existing_package_path(self, package_id: PackageID) -> Path:
        """Return the path of an existing package

        (not to confuse with the path of a package file that is to be created!)
        """
        # TODO: can we drop this, and just hand out the bytes or create the "enabled link"?
        base_name = format_file_name(package_id)
        if (local_package_path := self.local_packages / base_name).exists():
            return local_package_path
        if not (shipped_package_path := self.shipped_packages / base_name).exists():
            # yes, this is a race condition. But we want to make the intention clear.
            raise PackageException(f"no such package: {package_id.name} {package_id.version}")
        return shipped_package_path


def disable(package_name: PackageName, package_version: PackageVersion | None) -> None:
    package_path, manifest = _find_path_and_package_info(package_name, package_version)

    if (installed := get_installed_manifest(package_name)) is not None:
        if package_version is None or installed.version == package_version:
            uninstall(manifest)

    package_path.unlink()


def _find_path_and_package_info(
    package_name: PackageName, package_version: PackageVersion | None
) -> tuple[Path, Manifest]:

    # not sure if we need this, but better safe than sorry.
    def filename_matches(manifest: Manifest, name: str) -> bool:
        return format_file_name(manifest.id) == name

    def package_matches(
        manifest: Manifest, package_name: PackageName, package_version: PackageVersion | None
    ) -> bool:
        return manifest.name == package_name and (
            package_version is None or manifest.version == package_version
        )

    enabled_packages = get_enabled_manifests()

    matching_packages = [
        (package_path, manifest)
        for package_path in _get_enabled_package_paths()
        if (manifest := enabled_packages.get(package_path.name)) is not None
        and (
            package_matches(manifest, package_name, package_version)
            or filename_matches(manifest, package_name)
        )
    ]

    package_str = f"{package_name}" + ("" if package_version is None else f" {package_version}")
    if not matching_packages:
        raise PackageException(f"Package {package_str} is not enabled")
    if len(matching_packages) > 1:
        raise PackageException(f"Package not unique: {package_str}")

    return matching_packages[0]


def create(manifest: Manifest) -> None:
    if is_installed(manifest.name):
        raise PackageException("Packet already exists.")

    package_store = PackageStore()

    _validate_package_files(manifest.name, manifest.files)
    add_installed_manifest(manifest)
    _create_enabled_mkp_from_installed_package(package_store, manifest)


def edit(pacname: PackageName, new_manifest: Manifest) -> None:
    if not is_installed(pacname):
        raise PackageException("No such package")

    # Renaming: check for collision
    if pacname != new_manifest.name:
        if is_installed(new_manifest.name):
            raise PackageException(
                "Cannot rename package: a package with that name already exists."
            )
    package_store = PackageStore()

    _validate_package_files(pacname, new_manifest.files)

    _create_enabled_mkp_from_installed_package(package_store, new_manifest)
    remove_installed_manifest(pacname)
    add_installed_manifest(new_manifest)


def _create_enabled_mkp_from_installed_package(
    package_store: PackageStore, manifest: Manifest
) -> None:
    """Creates an MKP, saves it on disk and enables it

    After we changed and or created an MKP, we must make sure it is present on disk as
    an MKP, just like the uploaded ones.
    """
    base_name = format_file_name(manifest.id)
    file_path = cmk.utils.paths.local_optional_packages_dir / base_name

    file_path.parent.mkdir(parents=True, exist_ok=True)

    mkp = create_mkp_object(manifest)
    file_path.write_bytes(mkp)

    mark_as_enabled(package_store, manifest.id)


def install_optional_package(package_store: PackageStore, package_id: PackageID) -> Manifest:
    return install(
        package_store,
        package_id,
        allow_outdated=True,
    )


def mark_as_enabled(package_store: PackageStore, package_id: PackageID) -> None:
    """Mark the package as one of the enabled ones

    Copying (or linking) the packages into the local hierarchy is the easiest way to get them to
    be synchronized with the remote sites.
    """
    package_path = package_store.get_existing_package_path(package_id)
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


def remove_enabled_mark(manifest: Manifest) -> None:
    base_name = format_file_name(manifest.id)
    (cmk.utils.paths.local_enabled_packages_dir / base_name).unlink(
        missing_ok=True
    )  # should never be missing, but don't crash in messed up state


def install(
    package_store: PackageStore,
    package_id: PackageID,
    allow_outdated: bool = True,
    post_package_change_actions: bool = True,
) -> Manifest:
    try:
        return _install(
            package_store.get_existing_package_path(package_id).read_bytes(),
            allow_outdated=allow_outdated,
            post_package_change_actions=post_package_change_actions,
        )
    finally:
        # it is enabled, even if installing failed
        mark_as_enabled(package_store, package_id)


def _install(  # pylint: disable=too-many-branches
    mkp: bytes,
    # I am not sure whether we should install outdated packages by default -- but
    #  a) this is the compatible way to go
    #  b) users cannot even modify packages without installing them
    # Reconsider!
    *,
    allow_outdated: bool,
    post_package_change_actions: bool,
) -> Manifest:
    manifest = extract_manifest(mkp)

    if old_manifest := get_installed_manifest(manifest.name):
        g_logger.log(
            VERBOSE,
            "Updating %s from version %s to %s.",
            manifest.name,
            old_manifest.version,
            manifest.version,
        )
    else:
        g_logger.log(VERBOSE, "Installing %s version %s.", manifest.name, manifest.version)

    _raise_for_installability(manifest, old_manifest, cmk_version.__version__, allow_outdated)

    with tarfile.open(fileobj=BytesIO(mkp), mode="r:gz") as tar:
        # Now install files, but only unpack files explicitely listed
        for part in PACKAGE_PARTS + CONFIG_PARTS:
            if not (filenames := manifest.files.get(part.ident, [])):
                continue

            g_logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.ui_title, tty.normal)
            for fn in filenames:
                g_logger.log(VERBOSE, "    %s", fn)

            # make sure target directory exists
            if not os.path.exists(part.path):
                g_logger.log(VERBOSE, "    Creating directory %s", part.path)
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
                    g_logger.log(
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
    if old_manifest is not None:
        for part in PACKAGE_PARTS + CONFIG_PARTS:
            new_files = set(manifest.files.get(part.ident, []))
            old_files = set(old_manifest.files.get(part.ident, []))
            remove_files = old_files - new_files
            for fn in remove_files:
                path = os.path.join(part.path, fn)
                g_logger.log(VERBOSE, "Removing outdated file %s.", path)
                try:
                    with suppress(FileNotFoundError):
                        os.remove(path)
                except Exception as e:
                    g_logger.error("Error removing %s: %s", path, e)

            if part.ident == "ec_rule_packs":
                _remove_packaged_rule_packs(list(remove_files), delete_export=False)

        remove_enabled_mark(old_manifest)

    # Last but not least install package file
    add_installed_manifest(manifest)

    if post_package_change_actions:
        _execute_post_package_change_actions(manifest)

    return manifest


def _raise_for_installability(
    package: Manifest,
    old_package: Manifest | None,
    site_version: str,
    allow_outdated: bool,
) -> None:
    """Raise a `PackageException` if we should not install this package.

    Note: this currently ignores the packages "max version".
    """
    _raise_for_too_old_cmk_version(package.version_min_required, site_version)
    if not allow_outdated:
        _raise_for_too_new_cmk_version(package.version_usable_until, site_version)
    _raise_for_conflicts(package, old_package)


def _raise_for_conflicts(
    package: Manifest,
    old_package: Manifest | None,
) -> None:
    for file_path, type_of_collision in _conflicting_files(package, old_package):
        raise PackageException(f"File conflict: {file_path} ({type_of_collision})")


def _conflicting_files(
    package: Manifest,
    old_package: Manifest | None,
) -> Iterable[tuple[str, str]]:
    packaged_files = get_packaged_files()
    # Before installing check for conflicts
    for part in PACKAGE_PARTS + CONFIG_PARTS:
        packaged = packaged_files.get(part, ())

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
    packages = {manifest.name: manifest for manifest in get_installed_manifests()}

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

        for other_pacname, other_manifest in packages.items():
            for other_rel_path in other_manifest.files.get(part, []):
                if other_rel_path == rel_path and other_pacname != pacname:
                    raise PackageException(
                        f"File {path} does already belong to package {other_pacname}"
                    )


def _raise_for_too_old_cmk_version(min_version: str, site_version: str) -> None:
    """Raise PackageException if the site is too old for this package

    If the sites version can not be parsed or is a daily build, the check is simply passing without error.
    """
    if is_daily_build_of_master(min_version) or is_daily_build_of_master(site_version):
        return  # can not check exact version

    try:
        too_old = parse_check_mk_version(site_version) < parse_check_mk_version(min_version)
    except Exception:
        # Be compatible: When a version can not be parsed, then skip this check
        return

    if too_old:
        raise PackageException(
            f"Package requires Checkmk version {min_version} (this is {site_version})"
        )


def _raise_for_too_new_cmk_version(until_version: str | None, site_version: str) -> None:
    """Raise PackageException if the site is too new for this package

    If the sites version can not be parsed or is a daily build, the check is simply passing without error.
    """
    if (
        until_version is None
        or is_daily_build_of_master(site_version)
        or is_daily_build_of_master(until_version)
    ):
        return  # can not check exact version

    try:
        too_new = parse_check_mk_version(site_version) >= parse_check_mk_version(until_version)
    except Exception:
        # Be compatible: When a version can not be parsed, then skip this check
        return

    if too_new:
        raise PackageException(
            f"Package requires Checkmk version below {until_version} (this is {site_version})"
        )


def get_optional_manifests(
    package_store: PackageStore,
) -> Mapping[PackageID, tuple[Manifest, bool]]:
    local_packages = package_store.list_local_packages()
    local_names = {p.name for p in local_packages}
    shipped_packages = (
        p for p in package_store.list_shipped_packages() if p.name not in local_names
    )
    return {
        **{k: (v, True) for k, v in _get_manifests(local_packages).items()},
        **{k: (v, False) for k, v in _get_manifests(shipped_packages).items()},
    }


def get_enabled_manifests(log: logging.Logger | None = None) -> Mapping[PackageID, Manifest]:
    return _get_manifests(_get_enabled_package_paths(), log)


def _get_manifests(
    paths: Iterable[Path], log: logging.Logger | None = None
) -> Mapping[PackageID, Manifest]:
    return {
        manifest.id: manifest
        for pkg_path in paths
        if (manifest := extract_manifest_optionally(pkg_path, g_logger if log is None else log))
        is not None
    }


def _get_enabled_package_paths():
    try:
        return list(cmk.utils.paths.local_enabled_packages_dir.iterdir())
    except FileNotFoundError:
        return []


def get_unpackaged_files() -> dict[PackagePart, list[str]]:
    packaged = get_packaged_files()
    present = get_local_files_by_part()
    return {part: sorted(present[part] - (packaged.get(part) or set())) for part in present}


def package_part_info() -> PackagePartInfo:
    part_info: PackagePartInfo = {}
    for part in PACKAGE_PARTS + CONFIG_PARTS:
        try:
            files = os.listdir(part.path)
        except OSError:
            files = []

        part_info[part.ident] = {
            "title": part.ui_title,
            "permissions": [_get_permissions(os.path.join(part.path, f)) for f in files],
            "path": part.path,
            "files": files,
        }

    return part_info


def package_num_files(package: Manifest) -> int:
    return sum(len(fl) for fl in package.files.values())


def get_local_files_by_part() -> Mapping[PackagePart, set[str]]:
    return {part: _files_in_dir(part.ident, part.path) for part in PackagePart}


def _files_in_dir(part: str, directory: str, prefix: str = "") -> set[str]:
    if not os.path.exists(directory):
        return set()

    # Handle case where one part-directory lies below another
    taboo_dirs = {p.path for p in PACKAGE_PARTS + CONFIG_PARTS if p.ident != part}
    # os.path.realpath would resolve /omd to /opt/omd ...
    taboo_dirs |= {p.replace("lib/check_mk", "lib/python3/cmk") for p in taboo_dirs}
    if directory in taboo_dirs:
        return set()

    result: set[str] = set()
    files = os.listdir(directory)
    for f in files:
        if f in [".", ".."] or f.startswith(".") or f.endswith("~") or f.endswith(".pyc"):
            continue

        ignored = package_ignored_files.get(part, [])
        if prefix + f in ignored:
            continue

        path = directory + "/" + f
        if os.path.isdir(path):
            result.update(_files_in_dir(part, path, prefix + f + "/"))
        else:
            result.add(prefix + f)
    return result


def rule_pack_id_to_mkp() -> dict[str, PackageName | None]:
    """
    Returns a dictionary of rule pack ID to MKP package for a given manifest.
    Every rule pack is contained exactly once in this mapping. If no corresponding
    MKP exists, the value of that mapping is None.
    """

    def mkp_of(rule_pack_file: str) -> PackageName | None:
        """Find the MKP for the given file"""
        return next(
            (
                manifest.name
                for manifest in get_installed_manifests()
                if rule_pack_file in manifest.files.get("ec_rule_packs", [])
            ),
            None,
        )

    exported_rule_packs = package_part_info()["ec_rule_packs"]["files"]

    return {os.path.splitext(file_)[0]: mkp_of(file_) for file_ in exported_rule_packs}


def update_active_packages(log: logging.Logger) -> None:
    """Update which of the enabled packages are actually active (installed)"""
    package_store = PackageStore()
    _deinstall_inapplicable_active_packages(log, post_package_change_actions=False)
    _install_applicable_inactive_packages(package_store, log, post_package_change_actions=False)
    _execute_post_package_change_actions(None)


def _deinstall_inapplicable_active_packages(
    log: logging.Logger, *, post_package_change_actions: bool
) -> None:
    for manifest in get_installed_manifests(log):
        try:
            _raise_for_installability(
                manifest,
                manifest,
                cmk_version.__version__,
                allow_outdated=False,
            )
        except PackageException as exc:
            log.log(VERBOSE, "[%s %s]: Uninstalling (%s)", manifest.name, manifest.version, exc)
            uninstall(manifest, post_package_change_actions=post_package_change_actions)
        else:
            log.log(VERBOSE, "[%s %s]: Kept", manifest.name, manifest.version)


def _install_applicable_inactive_packages(
    package_store: PackageStore, log: logging.Logger, *, post_package_change_actions: bool
) -> None:
    for name, manifests in _sort_enabled_packages_for_installation(log):
        for manifest in manifests:
            try:
                install(
                    package_store,
                    manifest.id,
                    allow_outdated=False,
                    post_package_change_actions=post_package_change_actions,
                )
            except PackageException as exc:
                log.log(VERBOSE, "[%s]: Version %s not installed (%s)", name, manifest.version, exc)
            else:
                log.log(VERBOSE, "[%s]: Version %s installed", name, manifest.version)
                # We're done with this package.
                # Do not try to install older versions, or the installation function will
                # silently downgrade the package.
                break


def _sort_enabled_packages_for_installation(
    log: logging.Logger,
) -> Iterable[tuple[PackageName, Iterable[Manifest]]]:
    return groupby(
        sorted(
            sorted(
                get_enabled_manifests(log).values(), key=lambda m: m.version.sort_key, reverse=True
            ),
            key=lambda m: m.name,
        ),
        key=lambda m: m.name,
    )


def disable_outdated() -> None:
    """Check installed packages and disables the outdated ones

    Packages that contain a valid version number in the "version.usable_until" field can be disabled
    using this function. Others are not disabled.
    """
    for manifest in get_installed_manifests(g_logger):
        g_logger.log(VERBOSE, "[%s %s]: Is it outdated?", manifest.name, manifest.version)

        try:
            _raise_for_too_new_cmk_version(manifest.version_usable_until, cmk_version.__version__)
        except PackageException as exc:
            g_logger.log(
                VERBOSE,
                "[%s %s]: Disable outdated package: %s",
                manifest.name,
                manifest.version,
                exc,
            )
            disable(manifest.name, manifest.version)
        else:
            g_logger.log(VERBOSE, "[%s %s]: Not disabling", manifest.name, manifest.version)


def _execute_post_package_change_actions(package: Manifest | None) -> None:
    _build_setup_search_index_background()

    if package is None or _package_contains_gui_files(package):
        _reload_apache()


def _build_setup_search_index_background() -> None:
    subprocess.run(
        ["init-redis"],
        check=False,
    )


def _package_contains_gui_files(package: Manifest) -> bool:
    return "gui" in package.files or "web" in package.files


def _reload_apache() -> None:
    try:
        subprocess.run(
            ["omd", "reload", "apache"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        g_logger.error("Error reloading apache", exc_info=True)
