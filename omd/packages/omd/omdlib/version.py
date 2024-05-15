#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from collections.abc import Iterable, Mapping, Sequence

import omdlib
from omdlib.contexts import SiteContext


def main_version(
    _version_info: object,
    _site: object,
    _global_opts: object,
    args: Sequence[str],
    options: Mapping[str, str | None],
) -> None:
    if len(args) > 0:
        site = SiteContext(args[0])
        if not site.exists():
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
) -> None:
    for v in omd_versions():
        if v == default_version() and "bare" not in options:
            sys.stdout.write("%s (default)\n" % v)
        else:
            sys.stdout.write("%s\n" % v)


def default_version() -> str:
    return os.path.basename(
        os.path.realpath(os.path.join(omdlib.utils.omd_base_path(), "omd/versions/default"))
    )


def omd_versions() -> Iterable[str]:
    try:
        return sorted(
            [
                v
                for v in os.listdir(os.path.join(omdlib.utils.omd_base_path(), "omd/versions"))
                if v != "default"
            ]
        )
    except FileNotFoundError:
        return []


def version_exists(v: str) -> bool:
    return v in omd_versions()
