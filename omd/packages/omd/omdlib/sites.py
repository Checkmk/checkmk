#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

from omdlib.site_paths import SitePaths
from omdlib.version import default_version, version_from_site_dir

from cmk.ccc import tty


def main_sites(
    _version_info: object,
    _site: object,
    _global_opts: object,
    _args: object,
    options: Mapping[str, str | None],
    omd_path: Path = Path("/omd/"),
) -> None:
    if sys.stdout.isatty() and "bare" not in options:
        sys.stdout.write("SITE             VERSION          COMMENTS\n")
    for sitename in all_sites(omd_path):
        site_home = SitePaths.from_site_name(sitename, omd_path).home
        tags = []
        if "bare" in options:
            sys.stdout.write("%s\n" % sitename)
        else:
            v = version_from_site_dir(Path(site_home))
            if v is None:
                v = "(none)"
                tags.append("empty site dir")
            elif v == default_version(omd_path / "versions"):
                tags.append("default version")
            if is_disabled(omd_path / f"apache/{sitename}.conf"):
                tags.append(tty.bold + tty.red + "disabled" + tty.normal)
            sys.stdout.write("%-16s %-16s %s " % (sitename, v, ", ".join(tags)))
            sys.stdout.write("\n")


def all_sites(omd_path: Path) -> Iterable[str]:
    basedir = omd_path / "sites"
    return sorted([s for s in os.listdir(basedir) if os.path.isdir(os.path.join(basedir, s))])


def is_disabled(apache_conf: Path) -> bool:
    """Whether or not this site has been disabled with 'omd disable'"""
    return not os.path.exists(apache_conf)
