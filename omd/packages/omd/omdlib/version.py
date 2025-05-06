#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path

import omdlib
from omdlib.site_paths import SitePaths
from omdlib.utils import site_exists


def main_version(
    _version_info: object,
    _site: object,
    _global_opts: object,
    args: Sequence[str],
    options: Mapping[str, str | None],
    omd_path: Path = Path("/omd/"),
) -> None:
    if len(args) > 0:
        site_name = args[0]
        site_home = SitePaths.from_site_name(site_name, omd_path).home
        if not site_exists(Path(site_home)):
            sys.exit("No such site: %s" % site_name)
        version = version_from_site_dir(Path(site_home))
    else:
        version = omdlib.__version__

    if version is None:
        sys.exit("Failed to determine site version")

    if "bare" in options:
        sys.stdout.write(version + "\n")
    else:
        sys.stdout.write("OMD - Open Monitoring Distribution Version %s\n" % version)


def main_versions(
    _version_info: object,
    _site: object,
    _global_opts: object,
    _args: Sequence[str],
    options: Mapping[str, str | None],
    versions_path: Path = Path("/omd/versions"),
) -> None:
    for v in omd_versions(versions_path):
        if v == default_version(versions_path) and "bare" not in options:
            sys.stdout.write("%s (default)\n" % v)
        else:
            sys.stdout.write("%s\n" % v)


def default_version(versions_path: Path) -> str:
    return (versions_path / "default").resolve().name


def omd_versions(versions_path: Path) -> Collection[str]:
    try:
        return sorted(d.name for d in versions_path.iterdir() if d.name != "default")
    except FileNotFoundError:
        return []


def version_exists(v: str, versions_path: Path) -> bool:
    return v in omd_versions(versions_path)


def version_from_site_dir(site_dir: Path) -> str | None:
    """The version of a site is solely determined by the link ~SITE/version
    In case the version of a site can not be determined, it reports None."""
    try:
        return (site_dir / "version").readlink().name
    except Exception:
        return None
