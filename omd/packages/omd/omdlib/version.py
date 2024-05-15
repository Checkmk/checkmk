#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

import omdlib
from omdlib.contexts import SiteContext
from omdlib.utils import site_exists


def main_version(
    _version_info: object,
    _site: object,
    _global_opts: object,
    args: Sequence[str],
    options: Mapping[str, str | None],
) -> None:
    if len(args) > 0:
        site = SiteContext(args[0])
        if not site_exists(Path(site.dir)):
            sys.exit("No such site: %s" % site.name)
        version = site.version
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
    args: Sequence[str],
    options: Mapping[str, str | None],
    versions_path: Path = Path("/omd/versions"),
) -> None:
    for v in omd_versions(versions_path):
        if v == default_version(versions_path) and "bare" not in options:
            sys.stdout.write("%s (default)\n" % v)
        else:
            sys.stdout.write("%s\n" % v)


def default_version(versions_path: Path) -> str:
    return os.path.basename(os.path.realpath(versions_path / "default"))


def omd_versions(versions_path: Path) -> Iterable[str]:
    try:
        return sorted([v for v in os.listdir(versions_path) if v != "default"])
    except FileNotFoundError:
        return []


def version_exists(v: str, versions_path: Path) -> bool:
    return v in omd_versions(versions_path)
