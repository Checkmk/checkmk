#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import shutil
import subprocess
from collections.abc import Iterable, Mapping
from itertools import groupby
from pathlib import Path
from typing import Final

from pydantic import BaseModel

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.i18n import _  # noqa: F401
from cmk.utils.log import VERBOSE
from cmk.utils.version import is_daily_build_of_master, parse_check_mk_version

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

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
from ._parts import CONFIG_PARTS, PathConfig, permissions, ui_title  # noqa: F401
from ._reporter import all_local_files, all_rule_pack_files
from ._type_defs import PackageException, PackageID, PackageName, PackageVersion

g_logger = logging.getLogger("cmk.utils.packaging")


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


def release(installer: Installer, pacname: PackageName, logger: logging.Logger) -> None:
    if (manifest := installer.get_installed_manifest(pacname)) is None:
        raise PackageException(f"Package {pacname} not installed or corrupt.")

    logger.log(VERBOSE, "Releasing files of package %s into freedom...", pacname)
    for part, files in manifest.files.items():
        logger.log(VERBOSE, "  Part '%s':", part.ident)
        for f in files:
            logger.log(VERBOSE, "    %s", f)

    if filenames := manifest.files.get(PackagePart.EC_RULE_PACKS):
        ec.release_packaged_rule_packs([str(f) for f in filenames])

    installer.remove_installed_manifest(pacname)


def create_mkp_object(manifest: Manifest, path_config: PathConfig) -> bytes:
    return create_mkp(manifest, cmk_version.__version__, path_config.get_path, g_logger)


def uninstall(
    installer: Installer,
    path_config: PathConfig,
    manifest: Manifest,
    post_package_change_actions: bool = True,
) -> None:
    for part, filenames in manifest.files.items():
        g_logger.log(VERBOSE, "  Part '%s':", part.ident)
        if part is PackagePart.EC_RULE_PACKS:
            _remove_packaged_rule_packs(filenames)
            continue

        for fn in filenames:
            g_logger.log(VERBOSE, "    %s", fn)
            try:
                (path_config.get_path(part) / fn).unlink(missing_ok=True)
            except Exception as exc:
                raise PackageException(
                    f"Cannot uninstall {manifest.name} {manifest.version}: {exc}\n"
                ) from exc

    installer.remove_installed_manifest(manifest.name)

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


def disable(
    installer: Installer,
    path_config: PathConfig,
    package_name: PackageName,
    package_version: PackageVersion | None,
) -> None:
    package_path, manifest = _find_path_and_package_info(package_name, package_version)

    if (installed := installer.get_installed_manifest(package_name)) is not None:
        if package_version is None or installed.version == package_version:
            uninstall(installer, path_config, manifest)

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

    matching_packages = [
        (package_path, manifest)
        for package_path in _get_enabled_package_paths()
        if (manifest := extract_manifest_optionally(package_path, g_logger)) is not None
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


def create(installer: Installer, manifest: Manifest, path_config: PathConfig) -> None:
    if installer.is_installed(manifest.name):
        raise PackageException("Packet already exists.")

    package_store = PackageStore()

    _raise_for_nonexisting_files(manifest, path_config)
    _validate_package_files(manifest, installer, path_config)
    installer.add_installed_manifest(manifest)
    _create_enabled_mkp_from_installed_package(package_store, manifest, path_config)


def edit(
    installer: Installer, pacname: PackageName, new_manifest: Manifest, path_config: PathConfig
) -> None:
    if not installer.is_installed(pacname):
        raise PackageException("No such package")

    # Renaming: check for collision
    if pacname != new_manifest.name:
        if installer.is_installed(new_manifest.name):
            raise PackageException(
                "Cannot rename package: a package with that name already exists."
            )
    package_store = PackageStore()

    _raise_for_nonexisting_files(new_manifest, path_config)
    _validate_package_files(new_manifest, installer, path_config)

    _create_enabled_mkp_from_installed_package(package_store, new_manifest, path_config)
    installer.remove_installed_manifest(pacname)
    installer.add_installed_manifest(new_manifest)


def _raise_for_nonexisting_files(manifest: Manifest, path_config: PathConfig) -> None:
    for part, rel_path in manifest.files.items():
        for rp in rel_path:
            if not (fp := (path_config.get_path(part) / rp).exists()):
                raise PackageException(f"File {fp} does not exist.")


def _create_enabled_mkp_from_installed_package(
    package_store: PackageStore, manifest: Manifest, path_config: PathConfig
) -> None:
    """Creates an MKP, saves it on disk and enables it

    After we changed and or created an MKP, we must make sure it is present on disk as
    an MKP, just like the uploaded ones.
    """
    base_name = format_file_name(manifest.id)
    file_path = cmk.utils.paths.local_optional_packages_dir / base_name

    file_path.parent.mkdir(parents=True, exist_ok=True)

    mkp = create_mkp_object(manifest, path_config)
    file_path.write_bytes(mkp)

    mark_as_enabled(package_store, manifest.id)


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
    installer: Installer,
    package_store: PackageStore,
    package_id: PackageID,
    path_config: PathConfig,
    allow_outdated: bool = True,
    post_package_change_actions: bool = True,
) -> Manifest:
    try:
        return _install(
            installer,
            package_store.get_existing_package_path(package_id).read_bytes(),
            path_config,
            allow_outdated=allow_outdated,
            post_package_change_actions=post_package_change_actions,
        )
    finally:
        # it is enabled, even if installing failed
        mark_as_enabled(package_store, package_id)


def _install(  # pylint: disable=too-many-branches
    installer: Installer,
    mkp: bytes,
    path_config: PathConfig,
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
        g_logger.log(
            VERBOSE,
            "Updating %s from version %s to %s.",
            manifest.name,
            old_manifest.version,
            manifest.version,
        )
    else:
        g_logger.log(VERBOSE, "Installing %s version %s.", manifest.name, manifest.version)

    _raise_for_installability(
        installer, path_config, manifest, old_manifest, cmk_version.__version__, allow_outdated
    )

    extract_mkp(manifest, mkp, path_config.get_path, g_logger)

    _fix_files_permissions(manifest, path_config, g_logger)

    if ecfiles := manifest.files.get(PackagePart.EC_RULE_PACKS):
        ec.add_rule_pack_proxies((str(f) for f in ecfiles))

    # In case of an update remove files from old_package not present in new one
    if old_manifest is not None:
        for part, old_files in old_manifest.files.items():
            new_files = set(manifest.files.get(part, []))
            remove_files = set(old_files) - new_files
            for fn in remove_files:
                path = path_config.get_path(part) / fn
                g_logger.log(VERBOSE, "Removing outdated file %s.", path)
                try:
                    path.unlink(missing_ok=True)
                except OSError as e:
                    g_logger.error("Error removing %s: %s", path, e)

            if part is PackagePart.EC_RULE_PACKS:
                _remove_packaged_rule_packs(list(remove_files), delete_export=False)

        remove_enabled_mark(old_manifest)

    # Last but not least install package file
    installer.add_installed_manifest(manifest)

    if post_package_change_actions:
        _execute_post_package_change_actions(manifest)

    return manifest


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
        raise PackageException(f"File conflict: {file_path} ({type_of_collision})")


def _conflicting_files(
    package: Manifest,
    old_package: Manifest | None,
    installer: Installer,
    path_config: PathConfig,
) -> Iterable[tuple[Path, str]]:
    packaged_files = installer.get_packaged_files()
    # Before installing check for conflicts
    for part, files in package.files.items():
        packaged = packaged_files.get(part, ())

        old_files = set(old_package.files.get(part, [])) if old_package else set()

        for fn in files:
            if fn in old_files:
                continue
            path = path_config.get_path(part) / fn
            if fn in packaged:
                yield path, "part of another package"
            elif path.exists():
                yield path, "already existing"


def _fix_files_permissions(
    manifest: Manifest, path_config: PathConfig, logger: logging.Logger
) -> None:
    for part, filenames in manifest.files.items():
        for filename in filenames:
            path = path_config.get_path(part) / filename
            desired_perm = _get_permissions(part, filename)
            has_perm = path.stat().st_mode & 0o7777
            if has_perm != desired_perm:
                logger.log(
                    VERBOSE,
                    "    Fixing permissions of %s: %04o -> %04o",
                    path,
                    has_perm,
                    desired_perm,
                )
                path.chmod(desired_perm)


def _remove_packaged_rule_packs(file_names: Iterable[Path], delete_export: bool = True) -> None:
    """
    This function synchronizes the rule packs in rules.mk and the packaged rule packs
    of a MKP upon deletion of that MKP. When a modified or an unmodified MKP is
    deleted the exported rule pack and the rule pack in rules.mk are both deleted.
    """
    if not file_names:
        return

    rule_packs = list(ec.load_rule_packs())
    rule_pack_ids = [rp["id"] for rp in rule_packs]
    affected_ids = [fn.stem for fn in file_names]

    for id_ in affected_ids:
        index = rule_pack_ids.index(id_)
        del rule_packs[index]
        if delete_export:
            ec.remove_exported_rule_pack(id_)
        rule_pack_ids.remove(id_)

    ec.save_rule_packs(rule_packs)


def _validate_package_files(
    manifest: Manifest, installer: Installer, path_config: PathConfig
) -> None:
    """Packaged files must not already belong to another package"""
    for other_manifest in installer.get_installed_manifests():
        if manifest.name == other_manifest.name:
            continue
        _raise_for_collision(path_config, manifest, other_manifest)


def _raise_for_collision(
    path_config: PathConfig, manifest: Manifest, other_manifest: Manifest
) -> None:
    """Packaged files must not already belong to another package"""
    if collisions := set(
        str(path_config.get_path(part) / fn)
        for part in PackagePart
        for fn in manifest.files.get(part, ())
        if fn in other_manifest.files.get(part, ())
    ):
        raise PackageException(
            f"Files already belong to {other_manifest.name} {other_manifest.version}: {', '.join(collisions)}"
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


class StoredManifests(BaseModel):
    local: list[Manifest]
    shipped: list[Manifest]


def get_stored_manifests(
    package_store: PackageStore,
) -> StoredManifests:
    return StoredManifests(
        local=extract_manifests(package_store.list_local_packages(), g_logger),
        shipped=extract_manifests(package_store.list_shipped_packages(), g_logger),
    )


class ClassifiedManifests(BaseModel):
    stored: StoredManifests
    installed: list[Manifest]
    inactive: list[Manifest]

    @property
    def enabled(self) -> list[Manifest]:

        return [*self.installed, *self.inactive]


def get_classified_manifests(
    package_store: PackageStore, installer: Installer, logger: logging.Logger
) -> ClassifiedManifests:
    installed = installer.get_installed_manifests(logger)
    installed_ids = {m.id for m in installed}
    return ClassifiedManifests(
        stored=get_stored_manifests(package_store),
        installed=list(installed),
        inactive=[
            m for id_, m in get_enabled_manifests(logger).items() if id_ not in installed_ids
        ],
    )


def get_enabled_manifests(log: logging.Logger | None = None) -> Mapping[PackageID, Manifest]:
    return {m.id: m for m in extract_manifests(_get_enabled_package_paths(), log or g_logger)}


def _get_enabled_package_paths() -> list[Path]:
    try:
        return list(cmk.utils.paths.local_enabled_packages_dir.iterdir())
    except FileNotFoundError:
        return []


def get_unpackaged_files(
    installer: Installer, path_config: PathConfig
) -> dict[PackagePart, list[Path]]:
    packaged = installer.get_packaged_files()
    present = all_local_files(path_config)
    return {
        **{
            part: sorted(present[part] - (packaged.get(part) or set()))
            for part in PackagePart
            if part is not None
        },
        PackagePart.EC_RULE_PACKS: sorted(
            all_rule_pack_files(path_config.get_path(PackagePart.EC_RULE_PACKS))
            - packaged[PackagePart.EC_RULE_PACKS]
        ),
    }


def rule_pack_id_to_mkp(
    installer: Installer, rule_pack_files: Iterable[Path]
) -> dict[str, PackageName | None]:
    """
    Returns a dictionary of rule pack ID to MKP package for a given manifest.
    Every rule pack is contained exactly once in this mapping. If no corresponding
    MKP exists, the value of that mapping is None.
    """
    package_map = {
        file: manifest.name
        for manifest in installer.get_installed_manifests()
        for file in manifest.files.get(PackagePart.EC_RULE_PACKS, ())
    }

    return {f.stem: package_map.get(f) for f in rule_pack_files}


def update_active_packages(
    installer: Installer, log: logging.Logger, path_config: PathConfig
) -> None:
    """Update which of the enabled packages are actually active (installed)"""
    package_store = PackageStore()
    _deinstall_inapplicable_active_packages(
        installer, log, path_config, post_package_change_actions=False
    )
    _install_applicable_inactive_packages(
        package_store, installer, path_config, log, post_package_change_actions=False
    )
    _execute_post_package_change_actions(None)


def _deinstall_inapplicable_active_packages(
    installer: Installer,
    log: logging.Logger,
    path_config: PathConfig,
    *,
    post_package_change_actions: bool,
) -> None:
    for manifest in installer.get_installed_manifests(log):
        try:
            _raise_for_installability(
                installer,
                path_config,
                manifest,
                manifest,
                cmk_version.__version__,
                allow_outdated=False,
            )
        except PackageException as exc:
            log.log(VERBOSE, "[%s %s]: Uninstalling (%s)", manifest.name, manifest.version, exc)
            uninstall(
                installer,
                path_config,
                manifest,
                post_package_change_actions=post_package_change_actions,
            )
        else:
            log.log(VERBOSE, "[%s %s]: Kept", manifest.name, manifest.version)


def _install_applicable_inactive_packages(
    package_store: PackageStore,
    installer: Installer,
    path_config: PathConfig,
    log: logging.Logger,
    *,
    post_package_change_actions: bool,
) -> None:
    for name, manifests in _sort_enabled_packages_for_installation(log):
        for manifest in manifests:
            try:
                install(
                    installer,
                    package_store,
                    manifest.id,
                    path_config,
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


def disable_outdated(installer: Installer, path_config: PathConfig) -> None:
    """Check installed packages and disables the outdated ones

    Packages that contain a valid version number in the "version.usable_until" field can be disabled
    using this function. Others are not disabled.
    """
    for manifest in installer.get_installed_manifests(g_logger):
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
            disable(installer, path_config, manifest.name, manifest.version)
        else:
            g_logger.log(VERBOSE, "[%s %s]: Not disabling", manifest.name, manifest.version)


def _execute_post_package_change_actions(package: Manifest | None) -> None:
    _build_setup_search_index_background()

    if package is None or _package_contains_gui_files(package):
        _reload_apache()


def _build_setup_search_index_background() -> None:
    # Only trigger an index update if redis is running.
    #
    # This is mainly important in the context of 01_mkp-disable-outdated: Without the check if redis
    # is up, `mkp update-active` would attempt to trigger an update of the search index in a
    # background job. This involves deserializing a status file which was written during the
    # previous execution. In 2.2, the format of this file changed, which makes the deserialization
    # fail (CMK-12128). We have an update action which takes care of this, however,
    # cmk-update-config is called after mkp-disable-outdated, which is too late.
    #
    # Note that calling init-redis when redis is not running does not cause an error on the command
    # line. However, the background job would fail, which is shown in the background jobs page.
    if not subprocess.run(
        [
            cmk.utils.paths.omd_root / "etc/init.d/redis",
            "status",
        ],
        check=False,
        capture_output=True,
    ).returncode:
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
