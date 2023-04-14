#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import glob
import logging
import subprocess
from collections.abc import Iterable, Iterator, Mapping
from itertools import groupby
from pathlib import Path
from stat import filemode
from typing import Final

from pydantic import BaseModel

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.i18n import _  # noqa: F401
from cmk.utils.version import is_daily_build_of_master, parse_check_mk_version

from ..setup_search_index import request_index_rebuild
from ._installed import Installer
from ._mkp import (  # noqa: F401
    create_mkp,
    extract_manifest,
    extract_manifest_optionally,
    extract_manifests,
    extract_mkp,
    Manifest,
    manifest_template,
    PackagePart,
    read_manifest_optionally,
)
from ._parts import (  # noqa: F401
    CONFIG_PARTS,
    PackageOperationCallbacks,
    PathConfig,
    permissions,
    ui_title,
)
from ._reporter import all_local_files, all_rule_pack_files
from ._type_defs import PackageError, PackageID, PackageName, PackageVersion

_logger = logging.getLogger(__name__)


def _get_permissions(part: PackagePart, rel_path: Path) -> int:
    """Determine permissions by the first matching beginning of 'path'"""

    # I guess this shows that nagios plugins ought to be their own package part.
    # For now I prefer to stay compatible.
    if part is PackagePart.LIB and rel_path.parts[:2] == ("nagios", "plugins"):
        return 0o755
    return permissions(part)


def format_file_name(package_id: PackageID) -> str:
    """
    >>> package_id = PackageID(
    ...     name=PackageName("my_package"),
    ...     version=PackageVersion("1.0.2"),
    ... )

    >>> format_file_name(package_id)
    'my_package-1.0.2.mkp'

    """
    return f"{package_id.name}-{package_id.version}.mkp"


def release(
    installer: Installer,
    pacname: PackageName,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
) -> None:
    if (manifest := installer.get_installed_manifest(pacname)) is None:
        raise PackageError(f"Package {pacname} not installed or corrupt.")

    _logger.info("Releasing files of package %s into freedom...", pacname)
    for part, files in manifest.files.items():
        _logger.info("  Part '%s':", part.ident)
        for f in files:
            _logger.info("    %s", f)

    for part in set(manifest.files) & set(callbacks):
        callbacks[part].release(manifest.files[part])

    installer.remove_installed_manifest(pacname)


def create_mkp_object(manifest: Manifest, path_config: PathConfig) -> bytes:
    return create_mkp(manifest, cmk_version.__version__, path_config.get_path)


def uninstall(
    installer: Installer,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    manifest: Manifest,
    post_package_change_actions: bool = True,
) -> None:
    if err := list(_remove_files(manifest, keep_files={}, path_config=path_config)):
        raise PackageError(", ".join(err))

    for part in set(manifest.files) & set(callbacks):
        callbacks[part].uninstall(manifest.files[part])

    installer.remove_installed_manifest(manifest.name)

    if post_package_change_actions:
        _execute_post_package_change_actions(manifest)


class PackageStore:
    """Manage packages that are stored on the site

    This should become the single source of truth regarding package contents.
    """

    def __init__(self, *, shipped_dir: Path, local_dir: Path, enabled_dir: Path) -> None:
        self.shipped_packages: Final = shipped_dir
        self.local_packages: Final = local_dir
        self.enabled_packages: Final = enabled_dir

    def store(self, file_content: bytes, overwrite: bool = False) -> Manifest:
        package = extract_manifest(file_content)

        base_name = format_file_name(package.id)
        local_package_path = self.local_packages / base_name
        shipped_package_path = self.shipped_packages / base_name

        if shipped_package_path.exists() or (not overwrite and local_package_path.exists()):
            raise PackageError(f"Package {package.name} {package.version} exists on the site!")

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

    def read_bytes(self, package_id: PackageID) -> bytes:
        return self._get_existing_package_path(package_id).read_bytes()

    def _get_existing_package_path(self, package_id: PackageID) -> Path:
        """Return the path of an existing package

        (not to confuse with the path of a package file that is to be created!)
        """
        base_name = format_file_name(package_id)
        if (local_package_path := self.local_packages / base_name).exists():
            return local_package_path
        if not (shipped_package_path := self.shipped_packages / base_name).exists():
            # yes, this is a race condition. But we want to make the intention clear.
            raise PackageError(f"no such package: {package_id.name} {package_id.version}")
        return shipped_package_path

    def _enabled_path(self, package_id: PackageID) -> Path:
        return self.enabled_packages / format_file_name(package_id)

    def mark_as_enabled(self, package_id: PackageID) -> None:
        """Mark the package as one of the enabled ones

        Copying the packages into the local hierarchy is the easiest way to get them to
        be synchronized with the remote sites.
        """
        package_path = self._get_existing_package_path(package_id)
        destination = self._enabled_path(package_id)

        destination.parent.mkdir(parents=True, exist_ok=True)
        # We create a copy of the file in the local directory.
        # That way it'll be synced to the remote sites.
        # This creates redundant data on the system, but what are our options?
        #  a) extend the syncing mechanism: complex and makes the code more entangled
        #  b) move the file: also requires adjustments in a lot of places
        #  c) softlink: depends on the syncing mechanisms idea of how to handle a symlink -> see a)
        #  d) hardlink: *should* not work, see the linux kernel doc on "/proc/sys/fs/protect_hardlinks"
        destination.write_bytes(package_path.read_bytes())

    def remove_enabled_mark(self, package_id: PackageID) -> None:
        # should never be missing, but don't crash in messed up state
        self._enabled_path(package_id).unlink(missing_ok=True)

    def get_enabled_manifests(self) -> Mapping[PackageID, Manifest]:
        try:
            enabled_paths = list(self.enabled_packages.iterdir())
        except FileNotFoundError:
            return {}
        return {m.id: m for m in extract_manifests(enabled_paths)}


def disable(
    installer: Installer,
    package_store: PackageStore,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    package_id: PackageID,
) -> None:
    if (
        installed := installer.get_installed_manifest(package_id.name)
    ) is not None and installed.version == package_id.version:
        uninstall(installer, path_config, callbacks, installed)
    package_store.remove_enabled_mark(package_id)


def create(installer: Installer, manifest: Manifest, path_config: PathConfig) -> None:
    if installer.is_installed(manifest.name):
        raise PackageError("Packet already exists.")

    package_store = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    )

    _raise_for_nonexisting_files(manifest, path_config)
    _validate_package_files(manifest, installer)
    installer.add_installed_manifest(manifest)
    _create_enabled_mkp_from_installed_package(package_store, manifest, path_config)


def edit(
    installer: Installer, pacname: PackageName, new_manifest: Manifest, path_config: PathConfig
) -> None:
    if not installer.is_installed(pacname):
        raise PackageError("No such package")

    # Renaming: check for collision
    if pacname != new_manifest.name:
        if installer.is_installed(new_manifest.name):
            raise PackageError("Cannot rename package: a package with that name already exists.")
    package_store = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    )

    _raise_for_nonexisting_files(new_manifest, path_config)
    _validate_package_files(new_manifest, installer)

    _create_enabled_mkp_from_installed_package(package_store, new_manifest, path_config)
    installer.remove_installed_manifest(pacname)
    installer.add_installed_manifest(new_manifest)


def _raise_for_nonexisting_files(manifest: Manifest, path_config: PathConfig) -> None:
    for part, rel_path in manifest.files.items():
        for rp in rel_path:
            if not (fp := (path_config.get_path(part) / rp).exists()):
                raise PackageError(f"File {fp} does not exist.")


def _create_enabled_mkp_from_installed_package(
    package_store: PackageStore, manifest: Manifest, path_config: PathConfig
) -> None:
    """Creates an MKP, saves it on disk and enables it

    After we changed and or created an MKP, we must make sure it is present on disk as
    an MKP, just like the uploaded ones.
    """
    mkp = create_mkp_object(manifest, path_config)
    package_store.store(mkp, overwrite=True)
    package_store.mark_as_enabled(manifest.id)


def install(
    installer: Installer,
    package_store: PackageStore,
    package_id: PackageID,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    allow_outdated: bool = True,
    post_package_change_actions: bool = True,
) -> Manifest:
    try:
        return _install(
            installer,
            package_store,
            package_store.read_bytes(package_id),
            path_config,
            callbacks,
            allow_outdated=allow_outdated,
            post_package_change_actions=post_package_change_actions,
        )
    finally:
        # it is enabled, even if installing failed
        package_store.mark_as_enabled(package_id)


def _install(
    installer: Installer,
    package_store: PackageStore,
    mkp: bytes,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    # I am not sure whether we should install outdated packages by default -- but
    #  a) this is the compatible way to go
    #  b) users cannot even modify packages without installing them
    # Reconsider!
    *,
    allow_outdated: bool,
    post_package_change_actions: bool,
) -> Manifest:
    manifest = extract_manifest(mkp)

    if old_manifest := installer.get_installed_manifest(manifest.name):
        _logger.info(
            "[%s %s]: Updating from %s",
            manifest.name,
            manifest.version,
            old_manifest.version,
        )
    else:
        _logger.info("[%s %s]: Installing", manifest.name, manifest.version)

    _raise_for_installability(
        installer, path_config, manifest, old_manifest, cmk_version.__version__, allow_outdated
    )

    extract_mkp(manifest, mkp, path_config.get_path)

    _fix_files_permissions(manifest, path_config)

    for part in set(manifest.files) & set(callbacks):
        callbacks[part].install(manifest.files[part])

    # In case of an update remove files from old_package not present in new one
    if old_manifest is not None:
        for err in _remove_files(old_manifest, keep_files=manifest.files, path_config=path_config):
            _logger.error(err)

        for part in set(old_manifest.files) & set(callbacks):
            new_files = set(manifest.files.get(part, []))
            callbacks[part].uninstall([f for f in old_manifest.files[part] if f not in new_files])

        package_store.remove_enabled_mark(old_manifest.id)

    # Last but not least install package file
    installer.add_installed_manifest(manifest)

    if post_package_change_actions:
        _execute_post_package_change_actions(manifest)

    return manifest


def _remove_files(
    manifest: Manifest, keep_files: Mapping[PackagePart, Iterable[Path]], path_config: PathConfig
) -> Iterator[str]:
    for part, files in manifest.files.items():
        _logger.debug("  Part '%s':", part.ident)
        remove_files = set(files) - set(keep_files.get(part, []))
        for fn in remove_files:
            path = path_config.get_path(part) / fn
            try:
                path.unlink(missing_ok=True)
            except OSError as e:
                yield f"[{manifest.name} {manifest.version}]: Error removing {path}: {e}"
            else:
                _logger.info("[%s %s]: Removed %s", manifest.name, manifest.version, path)


def _raise_for_installability(
    installer: Installer,
    path_config: PathConfig,
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
    _raise_for_conflicts(package, old_package, installer, path_config)


def _raise_for_conflicts(
    package: Manifest,
    old_package: Manifest | None,
    installer: Installer,
    path_config: PathConfig,
) -> None:
    for file_path, type_of_collision in _conflicting_files(
        package, old_package, installer, path_config
    ):
        raise PackageError(f"File conflict: {file_path} ({type_of_collision})")


def _conflicting_files(
    package: Manifest,
    old_package: Manifest | None,
    installer: Installer,
    path_config: PathConfig,
) -> Iterable[tuple[Path, str]]:
    packaged_files = installer.get_packaged_files()
    # Before installing check for conflicts
    for part, files in package.files.items():
        packaged = packaged_files.get(part, {})

        old_files = set(old_package.files.get(part, [])) if old_package else set()

        for fn in files:
            if fn in old_files:
                continue
            path = path_config.get_path(part) / fn
            if (collision := packaged.get(fn)) is not None:
                yield path, f"already part of {collision.name} {collision.version}"
            elif path.exists():
                yield path, "already existing"


def _fix_files_permissions(manifest: Manifest, path_config: PathConfig) -> None:
    for part, filenames in manifest.files.items():
        for filename in filenames:
            path = path_config.get_path(part) / filename
            desired_perm = _get_permissions(part, filename)
            has_perm = path.stat().st_mode & 0o7777
            if has_perm != desired_perm:
                _logger.debug(
                    "Fixing %s: %s -> %s", path, filemode(has_perm), filemode(desired_perm)
                )
                path.chmod(desired_perm)


def _validate_package_files(manifest: Manifest, installer: Installer) -> None:
    """Packaged files must not already belong to another package"""
    for other_manifest in installer.get_installed_manifests():
        if manifest.name == other_manifest.name:
            continue
        _raise_for_collision(manifest, other_manifest)


def _raise_for_collision(manifest: Manifest, other_manifest: Manifest) -> None:
    """Packaged files must not already belong to another package"""
    if collisions := {
        (part, fn)
        for part in PackagePart
        for fn in (set(manifest.files.get(part, ())) & set(other_manifest.files.get(part, ())))
    }:
        raise PackageError(
            "Files already belong to %s %s: %s"
            % (
                other_manifest.name,
                other_manifest.version,
                ", ".join(f"{fn} ({part})" for part, fn in collisions),
            )
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
        raise PackageError(
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
        raise PackageError(
            f"Package requires Checkmk version below {until_version} (this is {site_version})"
        )


class StoredManifests(BaseModel):
    local: list[Manifest]
    shipped: list[Manifest]


def get_stored_manifests(
    package_store: PackageStore,
) -> StoredManifests:
    return StoredManifests(
        local=extract_manifests(package_store.list_local_packages()),
        shipped=extract_manifests(package_store.list_shipped_packages()),
    )


class ClassifiedManifests(BaseModel):
    stored: StoredManifests
    installed: list[Manifest]
    inactive: list[Manifest]

    @property
    def enabled(self) -> list[Manifest]:
        return [*self.installed, *self.inactive]


def get_classified_manifests(
    package_store: PackageStore, installer: Installer
) -> ClassifiedManifests:
    installed = installer.get_installed_manifests()
    installed_ids = {m.id for m in installed}
    return ClassifiedManifests(
        stored=get_stored_manifests(package_store),
        installed=list(installed),
        inactive=[
            m
            for id_, m in package_store.get_enabled_manifests().items()
            if id_ not in installed_ids
        ],
    )


def get_unpackaged_files(
    installer: Installer, path_config: PathConfig
) -> dict[PackagePart, list[Path]]:
    packaged = installer.get_packaged_files()
    present: dict[PackagePart | None, set[Path]] = {
        **all_local_files(path_config),
        PackagePart.EC_RULE_PACKS: all_rule_pack_files(
            path_config.get_path(PackagePart.EC_RULE_PACKS)
        ),
    }
    return {
        part: sorted(set(present.get(part, ())) - set(packaged.get(part, ())))
        for part in PackagePart
    }


def id_to_mkp(
    installer: Installer,
    rule_pack_files: Iterable[Path],
    package_part: PackagePart,
) -> dict[str, PackageName | None]:
    """
    Returns a dictionary of ID to MKP package for a given manifest.
    Every ID is contained exactly once in this mapping. If no corresponding
    MKP exists, the value of that mapping is None.
    """
    package_map = installer.get_packaged_files()[package_part]
    return {
        f.stem: package_id.name
        for f in rule_pack_files
        if (package_id := package_map.get(f)) is not None
    }


def update_active_packages(
    installer: Installer,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
) -> None:
    """Update which of the enabled packages are actually active (installed)"""
    package_store = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    )
    _deinstall_inapplicable_active_packages(
        installer, path_config, callbacks, post_package_change_actions=False
    )
    _install_applicable_inactive_packages(
        package_store, installer, path_config, callbacks, post_package_change_actions=False
    )
    _execute_post_package_change_actions(None)


def _deinstall_inapplicable_active_packages(
    installer: Installer,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    *,
    post_package_change_actions: bool,
) -> None:
    for manifest in installer.get_installed_manifests():
        try:
            _raise_for_installability(
                installer,
                path_config,
                manifest,
                manifest,
                cmk_version.__version__,
                allow_outdated=False,
            )
        except PackageError as exc:
            _logger.info("[%s %s]: Uninstalling: %s", manifest.name, manifest.version, exc)
            uninstall(
                installer,
                path_config,
                callbacks,
                manifest,
                post_package_change_actions=post_package_change_actions,
            )
        else:
            _logger.info("[%s %s]: Not uninstalling", manifest.name, manifest.version)


def _install_applicable_inactive_packages(
    package_store: PackageStore,
    installer: Installer,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    *,
    post_package_change_actions: bool,
) -> None:
    for name, manifests in _sort_enabled_packages_for_installation(package_store):
        for manifest in manifests:
            try:
                install(
                    installer,
                    package_store,
                    manifest.id,
                    path_config,
                    callbacks,
                    allow_outdated=False,
                    post_package_change_actions=post_package_change_actions,
                )
            except PackageError as exc:
                _logger.info("[%s %s]: Not installed: %s", name, manifest.version, exc)
            else:
                _logger.info("[%s %s]: Installed", name, manifest.version)
                # We're done with this package.
                # Do not try to install older versions, or the installation function will
                # silently downgrade the package.
                break


def _sort_enabled_packages_for_installation(
    package_store: PackageStore,
) -> Iterable[tuple[PackageName, Iterable[Manifest]]]:
    return groupby(
        sorted(
            sorted(
                package_store.get_enabled_manifests().values(),
                key=lambda m: m.version.sort_key,
                reverse=True,
            ),
            key=lambda m: m.name,
        ),
        key=lambda m: m.name,
    )


def disable_outdated(
    installer: Installer,
    package_store: PackageStore,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
) -> None:
    """Check installed packages and disables the outdated ones

    Packages that contain a valid version number in the "version.usable_until" field can be disabled
    using this function. Others are not disabled.
    """
    for manifest in installer.get_installed_manifests():
        try:
            _raise_for_too_new_cmk_version(manifest.version_usable_until, cmk_version.__version__)
        except PackageError as exc:
            _logger.info(
                "[%s %s]: Disabling: %s",
                manifest.name,
                manifest.version,
                exc,
            )
            disable(installer, package_store, path_config, callbacks, manifest.id)
        else:
            _logger.info("[%s %s]: Not disabling", manifest.name, manifest.version)


def _execute_post_package_change_actions(package: Manifest | None) -> None:
    if package is None or _package_contains_gui_files(package):
        _invalidate_visuals_cache()
        _reload_apache()
    request_index_rebuild()


def _invalidate_visuals_cache():
    """Invalidate visuals cache to use the current data"""
    for file in cmk.utils.paths.visuals_cache_dir.glob("last*"):
        file.unlink(missing_ok=True)


def _package_contains_gui_files(package: Manifest) -> bool:
    return "gui" in package.files or "web" in package.files


def _reload_apache() -> None:
    try:
        subprocess.run(["omd", "status", "apache"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        return

    try:
        subprocess.run(["omd", "reload", "apache"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        _logger.error("Error reloading apache", exc_info=True)
