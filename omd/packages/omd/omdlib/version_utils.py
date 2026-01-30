#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import sys
from collections.abc import Collection
from pathlib import Path
from typing import NoReturn


def default_version(versions_path: Path) -> str:
    return (versions_path / "default").resolve().name


def omd_versions(versions_path: Path = Path("/omd/versions")) -> Collection[str]:
    try:
        return sorted(d.name for d in versions_path.iterdir() if d.name != "default")
    except FileNotFoundError:
        return []


def version_exists(v: str, versions_path: Path = Path("/omd/versions")) -> bool:
    return v in omd_versions(versions_path)


def version_from_site_dir(site_dir: Path) -> str | None:
    """The version of a site is solely determined by the link ~SITE/version
    In case the version of a site can not be determined, it reports None."""
    try:
        return (site_dir / "version").readlink().name
    except Exception:
        return None


def exec_other_omd(version: str) -> NoReturn:
    """Rerun current omd command with other version"""
    omd_path = "/omd/versions/%s/bin/omd" % version
    if not version_exists(version):
        available_versions = ", ".join(omd_versions())
        sys.exit(f"Version {version} is not installed, available versions: {available_versions}")

    # Prevent inheriting environment variables from this versions/site environment
    # into the executed omd call. The omd call must import the python version related
    # modules and libraries. This only works when PYTHONPATH and LD_LIBRARY_PATH are
    # not already set when calling omd.
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("LD_LIBRARY_PATH", None)

    os.execv(omd_path, sys.argv)
    sys.exit("Cannot run bin/omd of version %s." % version)
