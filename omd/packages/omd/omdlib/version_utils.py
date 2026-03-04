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


def werk_18891_error(version: str, restore: bool) -> str:
    if restore:
        return (
            f"ERROR: Refusing to execute vulnerable omd version '{version}'.\n\n"
            f"For your security, automatic version switching to older version is blocked.\n"
            f"For more details on this vulnerability and the required updates, see:\n"
            f"https://checkmk.com/werk/18891\n\n"
            "Restoring your site is still possible. Please follow the instructions on the linked page."
        )
    return (
        f"ERROR: Refusing to execute vulnerable omd version '{version}'.\n\n"
        f"For your security, automatic version switching to older version is blocked.\n"
        f"For more details on this vulnerability and the required updates, see:\n"
        f"https://checkmk.com/werk/18891"
    )


def ensure_version_exists(version: str) -> None:
    if not version_exists(version):
        available = " ".join(omd_versions())
        sys.exit(f"Version {version} is not installed, available versions:\n{available}\n")


def exec_other_omd(version: str) -> NoReturn:
    """Rerun current omd command with other version"""
    omd_path = "/omd/versions/%s/bin/omd" % version
    ensure_version_exists(version)

    # Prevent inheriting environment variables from this versions/site environment
    # into the executed omd call. The omd call must import the python version related
    # modules and libraries. This only works when PYTHONPATH and LD_LIBRARY_PATH are
    # not already set when calling omd.
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("LD_LIBRARY_PATH", None)

    os.execv(omd_path, sys.argv)
    sys.exit("Cannot run bin/omd of version %s." % version)


def verify_security(version: str) -> bool:
    return Path(f"/omd/versions/{version}/share/omd/security-werk-18891.flag").exists()
