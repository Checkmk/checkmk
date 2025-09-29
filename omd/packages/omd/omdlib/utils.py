#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import enum
import os
import pwd
import shutil
import sys
from pathlib import Path
from typing import NoReturn

from omdlib.skel_permissions import get_skel_permissions, Permissions
from omdlib.type_defs import Replacements


def is_containerized() -> bool:
    return (
        os.path.exists("/.dockerenv")
        or os.path.exists("/run/.containerenv")
        or os.environ.get("CMK_CONTAINERIZED") == "TRUE"
    )


def delete_user_file(user_path: str) -> None:
    if not os.path.islink(user_path) and os.path.isdir(user_path):
        shutil.rmtree(user_path)
    else:
        os.remove(user_path)


def delete_directory_contents(d: str) -> None:
    for f in os.listdir(d):
        delete_user_file(d + "/" + f)


def get_editor() -> str:
    alternative = os.environ.get("EDITOR", "/usr/bin/vi")
    editor = os.environ.get("VISUAL", alternative)

    if not os.path.exists(editor):
        return "vi"

    return editor


class SiteDistributedSetup(str, enum.Enum):
    DISTRIBUTED_REMOTE = "distributed_remote"
    NOT_DISTRIBUTED = "not_distributed"
    UNKNOWN = "unknown"


def get_site_distributed_setup() -> SiteDistributedSetup:
    file_vars: dict[str, object] = {}
    if (distr_wato_filepath := Path("~/etc/omd/distributed.mk").expanduser()).exists():
        exec(  # nosec B102 # BNS:aee528
            distr_wato_filepath.read_text(),
            file_vars,
            file_vars,
        )
    if "is_wato_remote_site" not in file_vars:
        return SiteDistributedSetup.UNKNOWN
    if file_vars["is_wato_remote_site"] is True:
        return SiteDistributedSetup.DISTRIBUTED_REMOTE
    return SiteDistributedSetup.NOT_DISTRIBUTED


def chown_tree(directory: str, user: str) -> None:
    uid = pwd.getpwnam(user).pw_uid
    gid = pwd.getpwnam(user).pw_gid
    os.chown(directory, uid, gid)
    for dirpath, dirnames, filenames in os.walk(directory):
        for entry in dirnames + filenames:
            os.lchown(dirpath + "/" + entry, uid, gid)


def create_skeleton_file(
    skelbase: str,
    userbase: str,
    relpath: str,
    replacements: Replacements,
    permissions: Permissions,
) -> None:
    skel_path = Path(skelbase, relpath)
    user_path = Path(userbase, relpath)

    # Remove old version, if existing (needed during update)
    if user_path.exists():
        delete_user_file(str(user_path))

    # Create directories, symlinks and files
    if skel_path.is_symlink():
        user_path.symlink_to(skel_path.readlink())
    elif skel_path.is_dir():
        user_path.mkdir(parents=True)
    else:
        user_path.write_bytes(replace_tags(skel_path.read_bytes(), replacements))

    if not skel_path.is_symlink():
        user_path.chmod(get_skel_permissions(skelbase, permissions, relpath.removeprefix("./")))


def create_skeleton_files(
    site_dir: str,
    replacements: Replacements,
    skelroot: str,
    skel_permissions: Permissions,
    directory: str,
) -> None:
    # Hack: exclude tmp if dir is '.'
    exclude_tmp = directory == "."
    with contextlib.chdir(skelroot):  # make relative paths
        for dirpath, dirnames, filenames in os.walk(directory):
            dirpath = dirpath.removeprefix("./")
            for entry in dirnames + filenames:
                if exclude_tmp:
                    if dirpath == "." and entry == "tmp":
                        continue
                    if dirpath == "tmp" or dirpath.startswith("tmp/"):
                        continue
                create_skeleton_file(
                    skelroot, site_dir, dirpath + "/" + entry, replacements, skel_permissions
                )


def replace_tags(content: bytes, replacements: Replacements) -> bytes:
    for var, value in replacements.items():
        content = content.replace(var.encode("utf-8"), value.encode("utf-8"))
    return content


def exec_other_omd(version: str) -> NoReturn:
    """Rerun current omd command with other version"""
    omd_path = "/omd/versions/%s/bin/omd" % version
    if not os.path.exists(omd_path):
        sys.exit("Version '%s' is not installed." % version)

    # Prevent inheriting environment variables from this versions/site environment
    # into the executed omd call. The omd call must import the python version related
    # modules and libraries. This only works when PYTHONPATH and LD_LIBRARY_PATH are
    # not already set when calling omd.
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("LD_LIBRARY_PATH", None)

    os.execv(omd_path, sys.argv)
    sys.exit("Cannot run bin/omd of version %s." % version)


# TODO: move to sites.py, this is currently not possible due to circular import
def site_exists(site_dir: Path) -> bool:
    # In container environments the tmpfs may be managed by the container runtime (when
    # using the --tmpfs option).  In this case the site directory is
    # created as parent of the tmp directory to mount the tmpfs during
    # container initialization. Detect this situation and don't treat the
    # site as existing in that case.
    if is_containerized():
        if not os.path.exists(site_dir):
            return False
        if os.listdir(site_dir) == ["tmp"]:
            return False
        return True

    return os.path.exists(site_dir)
