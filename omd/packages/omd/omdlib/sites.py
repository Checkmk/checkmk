#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from collections.abc import Iterable, Mapping

import omdlib
from omdlib.contexts import SiteContext
from omdlib.version import default_version

import cmk.utils.tty as tty


def main_sites(
    _version_info: object,
    _site: object,
    _global_opts: object,
    _args: object,
    options: Mapping[str, str | None],
) -> None:
    if sys.stdout.isatty() and "bare" not in options:
        sys.stdout.write("SITE             VERSION          COMMENTS\n")
    for sitename in all_sites():
        site = SiteContext(sitename)
        tags = []
        if "bare" in options:
            sys.stdout.write("%s\n" % site.name)
        else:
            disabled = site.is_disabled()
            v = site.version
            if v is None:
                v = "(none)"
                tags.append("empty site dir")
            elif v == default_version():
                tags.append("default version")
            if disabled:
                tags.append(tty.bold + tty.red + "disabled" + tty.normal)
            sys.stdout.write("%-16s %-16s %s " % (site.name, v, ", ".join(tags)))
            sys.stdout.write("\n")


def all_sites() -> Iterable[str]:
    basedir = os.path.join(omdlib.utils.omd_base_path(), "omd/sites")
    return sorted([s for s in os.listdir(basedir) if os.path.isdir(os.path.join(basedir, s))])
