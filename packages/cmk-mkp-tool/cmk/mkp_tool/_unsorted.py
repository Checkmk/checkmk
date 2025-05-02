#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Everything from the packaging module that is not yet properly sorted.
Don't add new stuff here!
"""

import logging
import shutil
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from itertools import groupby
from pathlib import Path
from stat import filemode
from typing import Final, Protocol, Self

from pydantic import BaseModel

from ._installed import (
    cleanup_legacy_linked_lib_check_mk_path,
    Installer,
    replace_legacy_linked_lib_check_mk_path,
)
from ._mkp import (
    create_mkp,
    extract_manifest,
    extract_manifests,
    extract_mkp,
    Manifest,
    PackagePart,
)
from ._parts import PackageOperationCallbacks, PathConfig, permissions
from ._reporter import all_packable_files
from ._type_defs import PackageError, PackageID, PackageName

_logger = logging.getLogger(__name__)


class ComparableVersion(Protocol):
    def __ge__(self, other: Self) -> bool: ...

    def __lt__(self, other: Self) -> bool: ...


def format_file_name(package_id: PackageID) -> str:
    return f"{package_id.name}-{package_id.version}.mkp"


@contextmanager
def _log_exception(m: Manifest, name: str) -> Iterator[None]:
    try:
        yield
    except Exception as e:
        _logger.error("[%s %s]: Error in post %s hook: %s", m.name, m.version, name, e)


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
        with _log_exception(manifest, "release"):
            callbacks[part].release(manifest.files[part])

    installer.remove_installed_manifest(pacname)


def _uninstall(
    installer: Installer,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    manifest: Manifest,
) -> None:
    if err := remove_files(manifest, keep_files={}, path_config=path_config):
        raise PackageError(", ".join(err))

    for part in set(manifest.files) & set(callbacks):
        with _log_exception(manifest, "uninstall"):
            callbacks[part].uninstall(manifest.files[part])

    installer.remove_installed_manifest(manifest.name)


class PackageStore:
    """Manage packages that are stored on the site

    This should become the single source of truth regarding package contents.
    """

    def __init__(self, *, shipped_dir: Path, local_dir: Path, enabled_dir: Path) -> None:
        self.shipped_packages: Final = shipped_dir
        self.local_packages: Final = local_dir
        self.enabled_packages: Final = enabled_dir

    def store(
        self,
        file_content: bytes,
        persisting_function: Callable[[Path, bytes], object],
        overwrite: bool = False,
    ) -> Manifest:
        package = extract_manifest(file_content)

        base_name = format_file_name(package.id)
        local_package_path = self.local_packages / base_name
        shipped_package_path = self.shipped_packages / base_name

        if shipped_package_path.exists() or (not overwrite and local_package_path.exists()):
            raise PackageError(f"Package {package.name} {package.version} exists on the site!")

        local_package_path.parent.mkdir(parents=True, exist_ok=True)
        persisting_function(local_package_path, file_content)

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

        # if we're on the remote site, we have to consider this one:
        if (enabled_package_path := self.enabled_packages / base_name).exists():
            return enabled_package_path

        if (shipped_package_path := self.shipped_packages / base_name).exists():
            return shipped_package_path

        raise PackageError(f"No such package: {package_id.name} {package_id.version}")

    def _enabled_path(self, package_id: PackageID) -> Path:
        return self.enabled_packages / format_file_name(package_id)

    def mark_as_enabled(self, package_id: PackageID) -> None:
        """Mark the package as one of the enabled ones

        Copying the packages into the local hierarchy is the easiest way to get them to
        be synchronized with the remote sites.
        """
        package_path = self._get_existing_package_path(package_id)
        destination = self._enabled_path(package_id)
        if package_path == destination:
            return

        destination.parent.mkdir(parents=True, exist_ok=True)
        # We create a copy of the file in the local directory.
        # That way it'll be synced to the remote sites.
        # This creates redundant data on the system, but what are our options?
        #  a) extend the syncing mechanism: complex and makes the code more entangled
        #  b) move the file: also requires adjustments in a lot of places
        #  c) softlink: depends on the syncing mechanisms idea of how to handle a symlink -> see a)
        #  d) hardlink: *should* not work, see the linux kernel doc on
        #     "/proc/sys/fs/protect_hardlinks"
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
) -> Manifest | None:
    if (
        installed := installer.get_installed_manifest(package_id.name)
    ) is not None and installed.version == package_id.version:
        _uninstall(installer, path_config, callbacks, installed)
    package_store.remove_enabled_mark(package_id)
    return installed


def create(
    installer: Installer,
    manifest: Manifest,
    path_config: PathConfig,
    package_store: PackageStore,
    persisting_function: Callable[[Path, bytes], object],
    *,
    version_packaged: str,
) -> None:
    if installer.is_installed(manifest.name):
        raise PackageError("Package already exists.")

    _raise_for_nonexisting_files(manifest, path_config)
    _validate_package_files(manifest, installer)
    installer.add_installed_manifest(manifest)
    _create_enabled_mkp_from_installed_package(
        package_store,
        manifest,
        path_config,
        persisting_function,
        version_packaged=version_packaged,
    )


def edit(
    installer: Installer,
    pacname: PackageName,
    new_manifest: Manifest,
    path_config: PathConfig,
    package_store: PackageStore,
    persisting_function: Callable[[Path, bytes], object],
    *,
    version_packaged: str,
) -> None:
    if not installer.is_installed(pacname):
        raise PackageError(f"No such package installed: {pacname}")

    # Renaming: check for collision
    if pacname != new_manifest.name:
        if installer.is_installed(new_manifest.name):
            raise PackageError("Cannot rename package: a package with that name already exists.")

    _raise_for_nonexisting_files(new_manifest, path_config)
    _validate_package_files(new_manifest, installer)

    _create_enabled_mkp_from_installed_package(
        package_store,
        new_manifest,
        path_config,
        persisting_function,
        version_packaged=version_packaged,
    )
    installer.remove_installed_manifest(pacname)
    installer.add_installed_manifest(new_manifest)


def _raise_for_nonexisting_files(manifest: Manifest, path_config: PathConfig) -> None:
    for part, rel_path in manifest.files.items():
        for rp in rel_path:
            if not (fp := (path_config.get_path(part) / rp).exists()):
                raise PackageError(f"File {fp} does not exist.")


def _create_enabled_mkp_from_installed_package(
    package_store: PackageStore,
    manifest: Manifest,
    path_config: PathConfig,
    persisting_function: Callable[[Path, bytes], object],
    *,
    version_packaged: str,
) -> None:
    """Creates an MKP, saves it on disk and enables it

    After we changed and or created an MKP, we must make sure it is present on disk as
    an MKP, just like the uploaded ones.
    """
    mkp = create_mkp(manifest, path_config.get_path, version_packaged)
    package_store.store(mkp, persisting_function, overwrite=True)
    package_store.mark_as_enabled(manifest.id)


def install(
    installer: Installer,
    package_store: PackageStore,
    package_id: PackageID,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    *,
    site_version: str,
    version_check: bool,
    parse_version: Callable[[str], ComparableVersion],
) -> Manifest:
    try:
        return _install(
            installer,
            package_store.read_bytes(package_id),
            path_config,
            callbacks,
            site_version=site_version,
            version_check=version_check,
            parse_version=parse_version,
        )
    finally:
        # it is enabled, even if installing failed
        package_store.mark_as_enabled(package_id)


def _install(
    installer: Installer,
    mkp: bytes,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    *,
    site_version: str,
    parse_version: Callable[[str], ComparableVersion],
    version_check: bool,
) -> Manifest:
    original_manifest = extract_manifest(mkp)
    manifest = replace_legacy_linked_lib_check_mk_path(original_manifest)

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
        installer,
        path_config,
        manifest,
        old_manifest,
        site_version,
        version_check,
        parse_version,
    )

    extract_mkp(original_manifest, mkp, path_config.get_path)
    cleanup_legacy_linked_lib_check_mk_path(
        path_config.get_path(PackagePart.LIB), original_manifest
    )

    _fix_files_permissions(manifest, path_config)

    for part in set(manifest.files) & set(callbacks):
        with _log_exception(manifest, "install"):
            callbacks[part].install(manifest.files[part])

    # In case of an update remove files from old_package not present in new one
    if old_manifest is not None:
        for err in remove_files(old_manifest, keep_files=manifest.files, path_config=path_config):
            _logger.error(err)

        for part in set(old_manifest.files) & set(callbacks):
            new_files = set(manifest.files.get(part, []))
            with _log_exception(old_manifest, "uninstall"):
                callbacks[part].uninstall(
                    [f for f in old_manifest.files[part] if f not in new_files]
                )

    # Last but not least install package file
    installer.add_installed_manifest(manifest)

    return manifest


def _remove_pycache(manifest: Manifest, folder: Path) -> None:
    pycache_folder = folder / "__pycache__"
    shutil.rmtree(pycache_folder, ignore_errors=True)
    _logger.debug("[%s %s]: Removed folder %s", manifest.name, manifest.version, pycache_folder)


def _clear_remove_folders(manifest: Manifest, part: Path, folder: Path) -> None:
    folder_path = part / folder
    _remove_pycache(manifest, folder_path)
    try:
        folder_path.rmdir()
        _logger.debug(
            "[%s %s]: Removed empty directory %s",
            manifest.name,
            manifest.version,
            folder,
        )
    except OSError:
        return  # no point in recursing further

    if folder.parent.name:  # at the end, folder.parent is "." and folder.name is empty
        _clear_remove_folders(manifest, part, folder.parent)


def remove_files(
    manifest: Manifest,
    keep_files: Mapping[PackagePart, Iterable[Path]],
    path_config: PathConfig,
) -> tuple[str, ...]:
    errors = []
    paths_to_clean = set()
    for part, files in manifest.files.items():
        _logger.debug("  Part '%s':", part.ident)
        for fn in set(files) - set(keep_files.get(part, [])):
            paths_to_clean.add((part_path := path_config.get_path(part), fn.parent))
            path = part_path / fn
            try:
                path.unlink(missing_ok=True)
            except OSError as e:
                errors.append(f"[{manifest.name} {manifest.version}]: Error removing {path}: {e}")
            else:
                _logger.info("[%s %s]: Removed file %s", manifest.name, manifest.version, path)

    for part_path, folder in paths_to_clean:
        _clear_remove_folders(manifest, part_path, folder)

    return tuple(errors)


def _raise_for_installability(
    installer: Installer,
    path_config: PathConfig,
    package: Manifest,
    old_package: Manifest | None,
    site_version: str,
    version_check: bool,
    parse_version: Callable[[str], ComparableVersion],
) -> None:
    """Raise a `PackageException` if we should not install this package"""
    if version_check:
        _raise_for_too_old_cmk_version(parse_version, package.version_min_required, site_version)
        _raise_for_too_new_cmk_version(parse_version, package.version_usable_until, site_version)
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
            if (desired_perm := permissions(part, filename)) is None:
                continue

            path = path_config.get_path(part) / filename
            has_perm = path.stat().st_mode & 0o7777
            if has_perm != desired_perm:
                _logger.debug(
                    "Fixing %s: %s -> %s",
                    path,
                    filemode(has_perm),
                    filemode(desired_perm),
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
            f"Files already belong to {other_manifest.name} {other_manifest.version}: "
            + ", ".join(f"{fn} ({part})" for part, fn in collisions)
        )


def _raise_for_too_old_cmk_version(
    parse_version: Callable[[str], ComparableVersion],
    min_version: str,
    site_version: str,
) -> None:
    """Raise PackageException if the site is too old for this package

    If the sites version can not be parsed, the check is simply passing without error.
    """
    try:
        if parse_version(min_version) <= parse_version(site_version):
            return
    except Exception:
        # Be compatible: When a version can not be parsed, then skip this check
        return

    raise PackageError(
        f"Package requires a Checkmk version {min_version} or higher (this is {site_version})."
        f" You can skip all version checks by using the `--force-install` flag on the commandline."
    )


def _raise_for_too_new_cmk_version(
    parse_version: Callable[[str], ComparableVersion],
    until_version: str | None,
    site_version: str,
) -> None:
    """Raise PackageException if the site is too new for this package

    If the sites version can not be parsed, the check is simply passing without error.
    """
    if until_version is None:
        return

    try:
        if parse_version(site_version) < parse_version(until_version):
            return
    except Exception:
        # Be compatible: When a version can not be parsed, then skip this check
        return

    raise PackageError(
        f"Package requires a Checkmk version below {until_version} (this is {site_version})."
        f" You can skip all version checks by using the `--force-install` flag on the commandline."
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
    present = all_packable_files(path_config)
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
    package_store: PackageStore,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    site_version: str,
    parse_version: Callable[[str], ComparableVersion],
) -> tuple[Sequence[Manifest], Sequence[Manifest]]:
    """Update which of the enabled packages are actually active (installed)"""
    # order matters here (deinstall, then install)!
    return (
        _deinstall_inapplicable_active_packages(
            installer,
            path_config,
            callbacks,
            site_version=site_version,
            parse_version=parse_version,
        ),
        _install_applicable_inactive_packages(
            package_store,
            installer,
            path_config,
            callbacks,
            site_version=site_version,
            parse_version=parse_version,
        ),
    )


def _deinstall_inapplicable_active_packages(
    installer: Installer,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    *,
    parse_version: Callable[[str], ComparableVersion],
    site_version: str,
) -> Sequence[Manifest]:
    uninstalled = []
    for manifest in installer.get_installed_manifests():
        try:
            _raise_for_installability(
                installer,
                path_config,
                manifest,
                manifest,
                site_version,
                version_check=True,
                parse_version=parse_version,
            )
        except PackageError as exc:
            _logger.info("[%s %s]: Uninstalling: %s", manifest.name, manifest.version, exc)
            _uninstall(
                installer,
                path_config,
                callbacks,
                manifest,
            )
            uninstalled.append(manifest)
        else:
            _logger.info("[%s %s]: Not uninstalling", manifest.name, manifest.version)
    return uninstalled


def _install_applicable_inactive_packages(
    package_store: PackageStore,
    installer: Installer,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    *,
    site_version: str,
    parse_version: Callable[[str], ComparableVersion],
) -> Sequence[Manifest]:
    installed = []
    for name, manifests in _sort_enabled_packages_for_installation(package_store):
        for manifest in manifests:
            try:
                installed.append(
                    install(
                        installer,
                        package_store,
                        manifest.id,
                        path_config,
                        callbacks,
                        site_version=site_version,
                        version_check=True,
                        parse_version=parse_version,
                    )
                )
            except PackageError as exc:
                _logger.info("[%s %s]: Not installed: %s", name, manifest.version, exc)
            else:
                _logger.info("[%s %s]: Installed", name, manifest.version)
                # We're done with this package.
                # Do not try to install older versions, or the installation function will
                # silently downgrade the package.
                break
    return installed


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
    *,
    parse_version: Callable[[str], ComparableVersion],
    site_version: str,
) -> Sequence[Manifest]:
    """Check installed packages and disables the outdated ones

    Packages that contain a valid version number in the "version.usable_until" field can be disabled
    using this function. Others are not disabled.
    """
    disabled = []
    for manifest in installer.get_installed_manifests():
        try:
            _raise_for_too_new_cmk_version(
                parse_version, manifest.version_usable_until, site_version
            )
        except PackageError as exc:
            _logger.info(
                "[%s %s]: Disabling: %s",
                manifest.name,
                manifest.version,
                exc,
            )
            if (
                disabled_manifest := disable(
                    installer,
                    package_store,
                    path_config,
                    callbacks,
                    manifest.id,
                )
            ) is not None:
                disabled.append(disabled_manifest)
        else:
            _logger.info("[%s %s]: Not disabling", manifest.name, manifest.version)
    return disabled


def make_post_package_change_actions(
    *callbacks: tuple[tuple[PackagePart, ...], Callable[[], object]],
    on_any_change: tuple[Callable[[], object], ...],
) -> Callable[[Sequence[Manifest]], None]:
    def _execute_post_package_change_actions(
        packages: Sequence[Manifest],
    ) -> None:
        if not any(package.files for package in packages):
            # nothing changed at all
            return

        for triggers, callback in callbacks:
            if any(package.files.get(t) for t in triggers for package in packages):
                callback()

        for callback in on_any_change:
            callback()

    return _execute_post_package_change_actions
