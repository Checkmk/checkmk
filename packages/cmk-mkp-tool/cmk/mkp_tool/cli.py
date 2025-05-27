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
from dataclasses import dataclass
from pathlib import Path

from .__version__ import __version__
from ._installed import Installer
from ._mkp import (
    create_mkp,
    extract_manifest,
    Manifest,
    manifest_template,
    PackagePart,
    read_manifest_optionally,
)
from ._parts import make_path_config_template, PackageOperationCallbacks, PathConfig, ui_title
from ._reporter import files_inventory
from ._standalone import read_path_config, simple_file_write
from ._type_defs import PackageError, PackageID, PackageName, PackageVersion
from ._unsorted import (
    ComparableVersion,
    disable,
    disable_outdated,
    format_file_name,
    get_classified_manifests,
    get_stored_manifests,
    get_unpackaged_files,
    install,
    PackageStore,
    release,
    remove_files,
    update_active_packages,
)

_logger = logging.getLogger(__name__)

_VERSION_STR = f"cmk-mkp-tool {__version__}"


@dataclass(frozen=True)
class SiteContext:
    package_store: PackageStore
    installed_packages_dir: Path
    callbacks: Mapping[PackagePart, PackageOperationCallbacks]
    post_package_change_actions: Callable[[Sequence[Manifest]], None]
    version: str
    parse_version: Callable[[str], ComparableVersion]


_HandlerFunction = Callable[
    [
        argparse.Namespace,
        PathConfig | None,
        Callable[[Path, bytes], None],
    ],
    int,
]

_SiteExclusiveHandlerFunction = Callable[
    [
        SiteContext,
        argparse.Namespace,
        PathConfig | None,
        Callable[[Path, bytes], None],
    ],
    int,
]


def partial(wrappee: _SiteExclusiveHandlerFunction, site_context: SiteContext) -> _HandlerFunction:
    def wrapped(
        args: argparse.Namespace,
        path_config: PathConfig | None,
        persisting_function: Callable[[Path, bytes], None],
    ) -> int:
        return wrappee(site_context, args, path_config, persisting_function)

    wrapped.__doc__ = wrappee.__doc__
    return wrapped


_SiteOptionalHandlerFunction = Callable[
    [
        SiteContext | None,
        argparse.Namespace,
        PathConfig | None,
        Callable[[Path, bytes], None],
    ],
    int,
]


def partial_opt(
    wrappee: _SiteOptionalHandlerFunction, site_context: SiteContext | None
) -> _HandlerFunction:
    def wrapped(
        args: argparse.Namespace,
        path_config: PathConfig | None,
        persisting_function: Callable[[Path, bytes], None],
    ) -> int:
        return wrappee(site_context, args, path_config, persisting_function)

    wrapped.__doc__ = wrappee.__doc__
    return wrapped


def _render_table(headers: list[str], rows: Iterable[list[str]]) -> str:
    """
    >>> for line in _render_table(
    ...      ['This', 'that'],
    ...      [
    ...          ['row11', 'row12__', 'row13'],
    ...          ['row22_', 'row23'],
    ...      ]
    ... ).splitlines():
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
        "\n  {}{}".format(ui_title(part, lambda s: s), "".join(f"\n    {f}" for f in fs))
        for part, fs in manifest.files.items()
    )
    return (
        f"Name:                          {manifest.name}\n"
        f"Version:                       {manifest.version}\n"
        f"Packaged on:                   {manifest.version_packaged}\n"
        f"Required Checkmk Version:      {manifest.version_min_required}\n"
        f"Valid until Checkmk version:   {valid_until_text}\n"
        f"Title:                         {manifest.title}\n"
        f"Author:                        {manifest.author}\n"
        f"Download-URL:                  {manifest.download_url}\n"
        f"Files:                         {files}\n"
        f"Description:\n  {manifest.description}\n"
    )


def _command_path_config_template(
    _args: argparse.Namespace,
    _path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Write a template for the path config to stdout"""
    sys.stdout.write(f"{make_path_config_template().to_toml()}\n")
    return 0


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
    site_context: SiteContext | None,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Show information about local files"""
    if path_config is None:
        path_config = read_path_config()

    packaged_files = (
        {}
        if site_context is None
        else Installer(site_context.installed_packages_dir).get_packaged_files()
    )

    files = files_inventory(packaged_files, path_config)

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
    _path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Show manifest of an MKP file"""
    file_path: Path = args.file
    try:
        file_content = file_path.read_bytes()
    except OSError as exc:
        raise PackageError from exc

    manifest = extract_manifest(file_content)

    sys.stdout.write(f"{manifest.model_dump_json() if args.json else _to_text(manifest)}\n")
    return 0


def _args_show_all(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("--json", action="store_true", help="format output as json")


def _command_show_all(
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Show all manifests"""
    if path_config is None:
        path_config = read_path_config()

    stored_manifests = get_stored_manifests(site_context.package_store)

    if args.json:
        sys.stdout.write(f"{stored_manifests.model_dump_json()}\n")
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
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Show manifest of a stored package"""
    if path_config is None:
        path_config = read_path_config()

    manifest = extract_manifest(
        site_context.package_store.read_bytes(
            _get_package_id(args.name, args.version, site_context.package_store)
        )
    )
    sys.stdout.write(f"{manifest.model_dump_json() if args.json else _to_text(manifest)}\n")
    return 0


def _command_files(
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Show all files beloning to a package"""
    if path_config is None:
        path_config = read_path_config()

    manifest = extract_manifest(
        site_context.package_store.read_bytes(
            _get_package_id(args.name, args.version, site_context.package_store)
        )
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
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Show a table of all known files, including the deployment state"""
    if path_config is None:
        path_config = read_path_config()

    installer = Installer(site_context.installed_packages_dir)
    classified_manifests = get_classified_manifests(
        site_context.package_store,
        installer,
    )

    if args.json:
        sys.stdout.write(f"{classified_manifests.model_dump_json()}\n")
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


def _args_add(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("file", type=Path, help="Path to an MKP file")


def _command_add(
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Add an MKP to the collection of managed MKPs"""
    if path_config is None:
        path_config = read_path_config()

    file_path: Path = args.file
    try:
        file_content = file_path.read_bytes()
    except OSError as exc:
        raise PackageError from exc

    manifest = site_context.package_store.store(file_content, persisting_function)

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
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Remove the package and leave its contained files as unpackaged files behind."""
    if path_config is None:
        path_config = read_path_config()

    release(Installer(site_context.installed_packages_dir), args.name, site_context.callbacks)
    return 0


def _command_remove(
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Remove a package from the site"""
    if path_config is None:
        path_config = read_path_config()

    package_store = site_context.package_store
    package_id = _get_package_id(args.name, args.version, package_store)
    if package_id in package_store.get_enabled_manifests():
        raise PackageError("This package is enabled! Please disable it first.")

    _logger.info("Removing package %s...", package_id.name)
    package_store.remove(package_id)
    _logger.info("Successfully removed package %s.", package_id.name)
    return 0


def _command_disable_outdated(
    site_context: SiteContext,
    _args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Disable MKP packages that are declared to be outdated with the new version.

    Since 1.6 there is the option version.usable_until available in MKP packages.
    For all installed packages, this command compares that version with the Checkmk version.
    In case it is outdated, the package is disabled.
    """
    if path_config is None:
        path_config = read_path_config()

    disabled = disable_outdated(
        Installer(site_context.installed_packages_dir),
        site_context.package_store,
        path_config,
        site_context.callbacks,
        site_version=site_context.version,
        parse_version=site_context.parse_version,
    )
    site_context.post_package_change_actions(disabled)
    return 0


def _command_update_active(
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Disable MKP packages that are not suitable for this version, and enable others.

    Packages can declare their minimum or maximum required Checkmk versions.
    Also packages can collide with one another or fail to load for other reasons.

    This command deactivates all packages that are not applicable.
    After that it activates the ones that are.
    """
    if path_config is None:
        path_config = read_path_config()

    uninstalled, installed = update_active_packages(
        Installer(site_context.installed_packages_dir),
        path_config,
        site_context.package_store,
        site_context.callbacks,
        site_version=site_context.version,
        parse_version=site_context.parse_version,
    )
    site_context.post_package_change_actions([*uninstalled, *installed])
    _writeout_changed_packages(installed=installed, uninstalled=uninstalled, use_json=args.json)
    return 0


def _writeout_changed_packages(
    *,
    installed: Sequence[Manifest],
    uninstalled: Sequence[Manifest],
    use_json: bool,
) -> None:
    """Print information about changed packages in either JSON or text format.

    Note that there are various reasons why a package might be uninstalled or installed:
    - The sites version is higher than the supported versions of the package
    - The sites version is lower than the supported versions of the package
    - The package is not compatible with other installed packages

    Let's not try to be too smart about it and just print the package name and version.
    """
    if use_json:
        sys.stdout.write(
            json.dumps(
                {
                    "installed": [{"name": m.name, "version": m.version} for m in installed],
                    "uninstalled": [{"name": m.name, "version": m.version} for m in uninstalled],
                },
                indent=2,
            )
            + "\n"
        )
    else:
        for m in installed:
            sys.stdout.write(f"[{m.name} {m.version}]: enabled\n")
        for m in uninstalled:
            sys.stdout.write(f"[{m.name} {m.version}]: disabled\n")


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
        help=(
            "The package version. If only one package by the given name is applicable,"
            " the version can be omitted."
        ),
    )


def _args_enable(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument(
        "--force-install",
        action="store_true",
        help="Skip the version check, and install the package even if it is not suitable for this site",
    )
    _args_package_id(subparser)


def _command_enable(
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Enable a disabled package"""
    if path_config is None:
        path_config = read_path_config()

    installer = Installer(site_context.installed_packages_dir)
    installed = install(
        installer,
        site_context.package_store,
        _get_package_id(args.name, args.version, site_context.package_store),
        path_config,
        site_context.callbacks,
        site_version=site_context.version,
        version_check=not args.force_install,
        parse_version=site_context.parse_version,
    )
    site_context.post_package_change_actions([installed])

    return 0


def _command_disable(
    site_context: SiteContext,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Disable an enabled package"""
    if path_config is None:
        path_config = read_path_config()

    if (
        disabled := disable(
            Installer(site_context.installed_packages_dir),
            site_context.package_store,
            path_config,
            site_context.callbacks,
            _get_package_id(args.name, args.version, site_context.package_store),
        )
    ) is not None:
        site_context.post_package_change_actions([disabled])
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
    site_context: SiteContext | None,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    _persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Create a template of a package manifest

    You can pipe the output of this command into a file, and edit it.
    When you're happy with the manifest, you can use the `mkp package <path-to-file>` command to create the package.
    """
    if site_context:
        installer = Installer(site_context.installed_packages_dir)
        unpackaged = get_unpackaged_files(installer, path_config or read_path_config())
        files = {part: files_ for part in PackagePart if (files_ := unpackaged.get(part))}
    else:
        # for now: lets not look for files without a site context
        files = {part: [] for part in PackagePart}

    package = manifest_template(
        name=args.name,
        version_packaged=_VERSION_STR,
        version_required=site_context.version if site_context else "",
        files=files,
    )

    sys.stdout.write(f"{package.file_content()}\n")
    return 0


def _args_package(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("manifest_file", type=Path, help="The path to an package manifest file")


def _args_package_with_target(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument("manifest_file", type=Path, help="The path to an package manifest file")
    subparser.add_argument("target_dir", type=Path, help="The directory to create the mkp in")


def _command_package(
    site_context: SiteContext | None,
    args: argparse.Namespace,
    path_config: PathConfig | None,
    persisting_function: Callable[[Path, bytes], None],
) -> int:
    """Create an .mkp file from the provided manifest.

    You can use the `template` command to create a manifest template.
    """
    if path_config is None:
        path_config = read_path_config()

    if (package := read_manifest_optionally(args.manifest_file)) is None:
        return 1

    try:
        _ = PackageVersion.parse_semver(package.version)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    try:
        package_bytes = create_mkp(package, path_config.get_path, version_packaged=_VERSION_STR)
    except PackageError as exc:
        if args.debug:
            raise
        sys.stderr.write(f"{exc}\n")
        return 1
    _logger.info("Successfully created %s %s", package.name, package.version)

    if site_context is None:
        persisting_function(
            args.target_dir / format_file_name(package.id),
            package_bytes,
        )
        _logger.info("Successfully wrote package file")
        return 0

    manifest = site_context.package_store.store(
        package_bytes,
        persisting_function,
    )
    _logger.info("Successfully wrote package file")

    _logger.info("Removing packaged files before reinstalling...")
    # remove the files, so that we can "properly" install the package.
    # Installing calls hooks and fixes permissions, we want that.
    for err in remove_files(package, {}, path_config):
        _logger.info(err)

    installer = Installer(site_context.installed_packages_dir)
    try:
        installed = install(
            installer,
            site_context.package_store,
            manifest.id,
            path_config,
            site_context.callbacks,
            site_version=site_context.version,
            version_check=False,
            parse_version=site_context.parse_version,
        )
        site_context.post_package_change_actions([installed])
    except PackageError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    _logger.info("Successfully installed %s %s", manifest.name, manifest.version)

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


def _parse_arguments(argv: list[str], site_context: SiteContext | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mkp",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--debug", "-d", action="store_true")
    parser.add_argument("--verbose", "-v", action="count", default=0, help="Be more verbose")
    subparsers = parser.add_subparsers(required=True, title="available commands")

    _add_command(
        subparsers,
        "path-config-template",
        _no_args,
        _command_path_config_template,
    )
    _add_command(subparsers, "find", _args_find, partial_opt(_command_find, site_context))
    _add_command(subparsers, "inspect", _args_inspect, _command_inspect)
    _add_command(
        subparsers,
        "template",
        _args_template,
        partial_opt(_command_template, site_context),
    )
    _add_command(
        subparsers,
        "package",
        _args_package_with_target if site_context is None else _args_package,
        partial_opt(_command_package, site_context),
    )

    if site_context is None:
        return parser.parse_args(argv)

    _add_command(subparsers, "show", _args_show, partial(_command_show, site_context))
    _add_command(subparsers, "show-all", _args_show_all, partial(_command_show_all, site_context))
    _add_command(subparsers, "files", _args_package_id, partial(_command_files, site_context))
    _add_command(subparsers, "list", _args_list, partial(_command_list, site_context))
    _add_command(subparsers, "add", _args_add, partial(_command_add, site_context))
    _add_command(subparsers, "remove", _args_package_id, partial(_command_remove, site_context))
    _add_command(subparsers, "release", _args_release, partial(_command_release, site_context))
    _add_command(subparsers, "enable", _args_enable, partial(_command_enable, site_context))
    _add_command(subparsers, "disable", _args_package_id, partial(_command_disable, site_context))
    _add_command(
        subparsers, "disable-outdated", _no_args, partial(_command_disable_outdated, site_context)
    )
    _add_command(
        subparsers, "update-active", _args_show_all, partial(_command_update_active, site_context)
    )

    return parser.parse_args(argv)


def _no_args(_subparser: argparse.ArgumentParser) -> None:
    """This command has no arguments"""


def _add_command(
    subparsers: argparse._SubParsersAction,  # type: ignore[type-arg]  # providing one will crash
    cmd: str,
    args_adder: Callable[[argparse.ArgumentParser], None],
    handler: _HandlerFunction,
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
    path_config: PathConfig | None = None,
    site_context: SiteContext | None = None,
    persisting_function: Callable[[Path, bytes], None] = simple_file_write,
) -> int:
    args = _parse_arguments(sys.argv[1:] or ["--help"], site_context)
    set_up_logging(args.verbose)

    try:
        return int(
            args.handler(
                args,
                path_config,
                persisting_function,
            )
        )
    except PackageError as exc:
        if args.debug:
            raise
        sys.stderr.write(f"{exc}\n")
        return 1
