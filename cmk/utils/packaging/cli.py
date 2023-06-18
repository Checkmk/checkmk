#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Command line interface for the Checkmk Extension Packages"""
import argparse
import json
import logging
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

from . import (
    disable,
    disable_outdated,
    get_classified_manifests,
    get_stored_manifests,
    get_unpackaged_files,
    install,
    PackageStore,
    release,
    update_active_packages,
)
from ._installed import Installer
from ._mkp import (
    create_mkp,
    extract_manifest,
    Manifest,
    manifest_template,
    PackagePart,
    read_manifest_optionally,
)
from ._parts import PackageOperationCallbacks, PathConfig, ui_title
from ._reporter import files_inventory
from ._type_defs import PackageError, PackageID, PackageName, PackageVersion

_logger = logging.getLogger(__name__)


def _render_table(headers: list[str], rows: Iterable[list[str]]) -> str:
    """
    >>> for line in _render_table(['This', 'that'], [['row11', 'row12__', 'row13'], ['row22_', 'row23']]).splitlines():
    ...     line
    'This   that   '
    '------ -------'
    'row11  row12__'
    'row22_ row23  '
    """
    header, *table = zip(
        *([f"%-{max(len(i) for i in e)}s" % i for i in e] for e in zip(headers, *rows))
    )
    return "\n".join(
        (
            " ".join(header),
            " ".join("-" * len(i) for i in header),
            *(" ".join(row) for row in table),
        )
    )


def _to_text(manifest: Manifest) -> str:
    valid_until_text = manifest.version_usable_until or "No version limitation"
    files = "".join(
        "\n  {}{}".format(ui_title(part), "".join(f"\n    {f}" for f in fs))
        for part, fs in manifest.files.items()
    )
    return (
        f"Name:                          {manifest.name}\n"
        f"Version:                       {manifest.version}\n"
        f"Packaged on Checkmk Version:   {manifest.version_packaged}\n"
        f"Required Checkmk Version:      {manifest.version_min_required}\n"
        f"Valid until Checkmk version:   {valid_until_text}\n"
        f"Title:                         {manifest.title}\n"
        f"Author:                        {manifest.author}\n"
        f"Download-URL:                  {manifest.download_url}\n"
        f"Files:                         {files}\n"
        f"Description:\n  {manifest.description}\n"
    )


def _args_find(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include packaged files in report",
    )
    subparser.add_argument(
        "--json",
        action="store_true",
        help="format output as json",
    )


def _command_find(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Show information about local files"""
    installer = Installer(path_config.installed_packages_dir)

    files = files_inventory(installer, path_config)

    if not args.all:
        files = [f for f in files if not f["package"]]

    if args.json:
        sys.stdout.write(f"{json.dumps(files, indent='  ')}\n")
        return 0

    table = _render_table(
        ["File", "Package", "Version", "Part", "Mode"],
        [[f["file"], f["package"], f["version"], f["part_title"], f["mode"]] for f in files],
    )
    sys.stdout.write(f"{table}\n")
    return 0


def _args_inspect(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("--json", action="store_true", help="format output as json")
    subparser.add_argument("file", type=Path, help="Path to an MKP file")


def _command_inspect(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Show manifest of an MKP file"""
    file_path: Path = args.file
    try:
        file_content = file_path.read_bytes()
    except OSError as exc:
        raise PackageError from exc

    manifest = extract_manifest(file_content)

    sys.stdout.write(f"{manifest.json() if args.json else _to_text(manifest)}\n")
    return 0


def _args_show_all(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("--json", action="store_true", help="format output as json")


def _command_show_all(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Show all manifests"""
    stored_manifests = get_stored_manifests(
        PackageStore(
            shipped_dir=path_config.packages_shipped_dir,
            local_dir=path_config.packages_local_dir,
            enabled_dir=path_config.packages_enabled_dir,
        )
    )

    if args.json:
        sys.stdout.write(f"{stored_manifests.json()}\n")
        return 0

    # I don't think this is very useful, but we include it for consistency.
    sys.stdout.write("Local extension packages\n========================\n\n")
    sys.stdout.write("".join(f"{_to_text(m)}\n" for m in stored_manifests.local))
    sys.stdout.write("Shipped extension packages\n==========================\n\n")
    sys.stdout.write("".join(f"{_to_text(m)}\n" for m in stored_manifests.shipped))
    return 0


def _args_show(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("--json", action="store_true", help="format output as json")
    _args_package_id(subparser)


def _command_show(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Show manifest of a stored package"""
    package_store = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    )
    manifest = extract_manifest(
        package_store.read_bytes(_get_package_id(args.name, args.version, package_store))
    )
    sys.stdout.write(f"{manifest.json() if args.json else _to_text(manifest)}\n")
    return 0


def _command_files(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Show all files beloning to a package"""
    package_store = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    )
    manifest = extract_manifest(
        package_store.read_bytes(_get_package_id(args.name, args.version, package_store))
    )
    sys.stdout.write(
        "".join(
            f"{path_config.get_path(part) / rel_path}\n"
            for part, rel_paths in manifest.files.items()
            for rel_path in rel_paths
        )
    )
    return 0


def _args_list(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("--json", action="store_true", help="format output as json")


def _command_list(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Show a table of all known files, including the deployment state"""
    installer = Installer(path_config.installed_packages_dir)
    classified_manifests = get_classified_manifests(
        PackageStore(
            shipped_dir=path_config.packages_shipped_dir,
            local_dir=path_config.packages_local_dir,
            enabled_dir=path_config.packages_enabled_dir,
        ),
        installer,
    )

    if args.json:
        sys.stdout.write(f"{classified_manifests.json()}\n")
        return 0

    enabled_ids = {m.id for m in classified_manifests.enabled}
    disabled = [
        m
        for m in [
            *classified_manifests.stored.local,
            *classified_manifests.stored.shipped,
        ]
        if m.id not in enabled_ids
    ]
    table = _render_table(
        ["Name", "Version", "Title", "Author", "Req. Version", "Until Version", "Files", "State"],
        [
            *(_row(m, "Enabled (active on this site)") for m in classified_manifests.installed),
            *(_row(m, "Enabled (inactive on this site)") for m in classified_manifests.inactive),
            *(_row(m, "Disabled") for m in disabled),
        ],
    )
    sys.stdout.write(f"{table}\n")
    return 0


def _row(manifest: Manifest, state: str) -> list[str]:
    return [
        str(manifest.name),
        str(manifest.version),
        str(manifest.title),
        str(manifest.author),
        str(manifest.version_min_required),
        str(manifest.version_usable_until),
        str(sum(len(f) for f in manifest.files.values())),
        state,
    ]


def _args_install_deprecated(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("file", type=str, metavar="(DEPRECATED)")


def _command_install_deprecated(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """This command is deprecated. Please use the `add` and `enable` commands."""
    sys.stderr.write(f"{_command_install_deprecated.__doc__}\n")
    return 1


def _args_add(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("file", type=Path, help="Path to an MKP file")


def _command_add(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Add an MKP to the collection of managed MKPs"""
    file_path: Path = args.file
    try:
        file_content = file_path.read_bytes()
    except OSError as exc:
        raise PackageError from exc

    manifest = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    ).store(file_content)

    # these are the required arguments for `mkp enable`!
    sys.stdout.write(f"{manifest.name} {manifest.version}\n")
    return 0


def _args_release(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument(
        "name",
        type=PackageName,
        help="The packages name",
    )


def _command_release(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Remove the package and leave its contained files as unpackaged files behind."""
    release(Installer(path_config.installed_packages_dir), args.name, callbacks)
    return 0


def _command_remove(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Remove a package from the site"""
    package_store = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    )
    package_id = _get_package_id(args.name, args.version, package_store)
    if package_id in package_store.get_enabled_manifests():
        raise PackageError("This package is enabled! Please disable it first.")

    _logger.info("Removing package %s...", package_id.name)
    package_store.remove(package_id)
    _logger.info("Successfully removed package %s.", package_id.name)
    return 0


def _command_disable_outdated(
    _args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Disable MKP packages that are declared to be outdated with the new version.

    Since 1.6 there is the option version.usable_until available in MKP packages.
    For all installed packages, this command compares that version with the Checkmk version.
    In case it is outdated, the package is disabled.
    """
    disabled = disable_outdated(
        Installer(path_config.installed_packages_dir),
        PackageStore(
            shipped_dir=path_config.packages_shipped_dir,
            local_dir=path_config.packages_local_dir,
            enabled_dir=path_config.packages_enabled_dir,
        ),
        path_config,
        callbacks,
        site_version=this_version,
    )
    post_package_change_actions(disabled)
    return 0


def _command_update_active(
    _args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Disable MKP packages that are not suitable for this version, and enable others.

    Packages can declare their minimum or maximum required Checkmk versions.
    Also packages can collide with one another or fail to load for other reasons.

    This command deactivates all packages that are not applicable, and then activates the ones that are.
    """
    uninstalled, installed = update_active_packages(
        Installer(path_config.installed_packages_dir),
        path_config,
        callbacks,
        site_version=this_version,
    )
    post_package_change_actions([*uninstalled, *installed])
    return 0


def _args_package_id(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument(
        "name",
        type=PackageName,
        help="The package name",
    )
    subparser.add_argument(
        "version",
        type=PackageVersion,
        default=None,
        nargs="?",
        help="The package version. If only one package by the given name is applicable, the version can be omitted.",
    )


def _command_enable(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Enable a disabled package"""
    installer = Installer(path_config.installed_packages_dir)
    package_store = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    )
    installed = install(
        installer,
        package_store,
        _get_package_id(args.name, args.version, package_store),
        path_config,
        callbacks,
        site_version=this_version,
    )
    post_package_change_actions([installed])

    return 0


def _command_disable(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Disable an enabled package"""
    package_store = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    )
    if (
        disabled := disable(
            Installer(path_config.installed_packages_dir),
            package_store,
            path_config,
            callbacks,
            _get_package_id(args.name, args.version, package_store),
        )
    ) is not None:
        post_package_change_actions([disabled])
    return 0


def _args_template(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument(
        "name",
        type=PackageName,
        help="The packages name",
    )


def _command_template(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Create a template of a package manifest"""
    installer = Installer(path_config.installed_packages_dir)

    unpackaged = get_unpackaged_files(installer, path_config)

    package = manifest_template(
        name=args.name,
        version_packaged=this_version,
        files={part: files_ for part in PackagePart if (files_ := unpackaged.get(part))},
    )

    temp_file = path_config.tmp_dir / f"{args.name}.manifest.temp"
    temp_file.write_text(package.file_content())
    sys.stdout.write(
        f"Created '{temp_file}'.\n"
        "You may now edit it.\n"
        f"Create the package using `mkp package {temp_file}`.\n"
    )
    return 0


def _args_package(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument(
        "manifest_file",
        type=Path,
        help="The path to an package manifest file",
    )


def _command_package(
    args: argparse.Namespace,
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    """Create an .mkp file from the provided manifest.

    You can use the `template` command to create a manifest template.
    """
    if (package := read_manifest_optionally(args.manifest_file)) is None:
        return 1

    try:
        _ = PackageVersion.parse_semver(package.version)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    store = PackageStore(
        shipped_dir=path_config.packages_shipped_dir,
        local_dir=path_config.packages_local_dir,
        enabled_dir=path_config.packages_enabled_dir,
    )
    installer = Installer(path_config.installed_packages_dir)
    try:
        manifest = store.store(
            create_mkp(package, path_config.get_path, version_packaged=this_version)
        )
        installed = install(
            installer,
            store,
            manifest.id,
            path_config,
            callbacks,
            site_version=this_version,
        )
        post_package_change_actions([installed])
    except PackageError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    _logger.info("Successfully created %s %s", manifest.name, manifest.version)
    return 0


def _get_package_id(
    name: PackageName,
    version: PackageVersion | None,
    package_store: PackageStore,
) -> PackageID:
    if version is not None:
        return PackageID(name=name, version=version)

    stored_packages = get_stored_manifests(package_store)
    match [
        *(p for p in stored_packages.local if p.name == name),
        *(p for p in stored_packages.shipped if p.name == name),
    ]:
        case ():
            raise PackageError(f"No such package: {name}")
        case (single_match,):
            return single_match.id
        case multiple_matches:
            raise PackageError(
                f"Please specify version ({', '.join(m.version for m in multiple_matches)})"
            )


def _parse_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mkp",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--debug", "-d", action="store_true")
    parser.add_argument("--verbose", "-v", action="count", default=0, help="Be more verbose")
    subparsers = parser.add_subparsers(required=True, title="available commands")

    _add_command(subparsers, "find", _args_find, _command_find)
    _add_command(subparsers, "inspect", _args_inspect, _command_inspect)
    _add_command(subparsers, "show", _args_show, _command_show)
    _add_command(subparsers, "show-all", _args_show_all, _command_show_all)
    _add_command(subparsers, "files", _args_package_id, _command_files)
    _add_command(subparsers, "list", _args_list, _command_list)
    # Can be dropped in 2.3
    _add_command(subparsers, "install", _args_install_deprecated, _command_install_deprecated)
    _add_command(subparsers, "add", _args_add, _command_add)
    _add_command(subparsers, "release", _args_release, _command_release)
    _add_command(subparsers, "remove", _args_package_id, _command_remove)
    _add_command(subparsers, "enable", _args_package_id, _command_enable)
    _add_command(subparsers, "disable", _args_package_id, _command_disable)
    _add_command(subparsers, "template", _args_template, _command_template)
    _add_command(subparsers, "package", _args_package, _command_package)
    _add_command(subparsers, "disable-outdated", _no_args, _command_disable_outdated)
    _add_command(subparsers, "update-active", _no_args, _command_update_active)

    return parser.parse_args(argv)


def _no_args(subparser: argparse.ArgumentParser) -> None:
    """This command has no arguments"""


def _add_command(
    subparsers: argparse._SubParsersAction,
    cmd: str,
    args_adder: Callable[[argparse.ArgumentParser], None],
    handler: Callable[
        [
            argparse.Namespace,
            PathConfig,
            Mapping[PackagePart, PackageOperationCallbacks],
            str,
            Callable[[Sequence[Manifest]], None],
        ],
        int,
    ],
) -> None:
    subparser = subparsers.add_parser(cmd, help=handler.__doc__, description=handler.__doc__)
    args_adder(subparser)
    subparser.set_defaults(handler=handler)


def set_up_logging(verbosity: int) -> None:
    logging.basicConfig(
        format="%(levelname)s: %(message)s" if verbosity else "%(message)s",
        level={0: logging.WARNING, 1: logging.INFO}.get(verbosity, logging.DEBUG),
    )


def main(
    argv: list[str],
    path_config: PathConfig,
    callbacks: Mapping[PackagePart, PackageOperationCallbacks],
    this_version: str,
    post_package_change_actions: Callable[[Sequence[Manifest]], None],
) -> int:
    args = _parse_arguments(argv)
    set_up_logging(args.verbose)
    try:
        return args.handler(args, path_config, callbacks, this_version, post_package_change_actions)
    except PackageError as exc:
        if args.debug:
            raise
        sys.stderr.write(f"{exc}\n")
        return 1
