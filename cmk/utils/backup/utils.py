#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import grp
import json
import os
import pwd
import sys
import time
from hashlib import md5
from pathlib import Path

from cmk.utils.backup.type_defs import RawBackupInfo, SiteBackupInfo
from cmk.utils.exceptions import MKGeneralException

SITE_BACKUP_MARKER = "Check_MK"
BACKUP_INFO_FILENAME = "mkbackup.info"


def current_site_id() -> str:
    return os.environ["OMD_SITE"]


def log(s: str) -> None:
    msg = "{} {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), s)
    sys.stdout.write(msg)


def makedirs(
    path: Path, user: str | None = None, group: str | None = None, mode: int | None = None
) -> None:
    head, tail = os.path.split(path)
    if not tail:
        head, tail = os.path.split(head)

    if head and tail and not os.path.exists(head):
        try:
            makedirs(Path(head), user, group, mode)
        except OSError as e:
            # be happy if someone already created the path
            if e.errno != errno.EEXIST:
                raise
        if tail == ".":  # xxx/newdir/. exists if xxx/newdir exists
            return
    makedir(path, user, group, mode)


def makedir(
    path: Path, user: str | None = None, group: str | None = None, mode: int | None = None
) -> None:
    if os.path.exists(path):
        return
    os.mkdir(path)
    uid = pwd.getpwnam(user).pw_uid if user is not None else None
    gid = grp.getgrnam(group).gr_gid if group is not None else None
    set_permissions(path=path, uid=uid, gid=gid, mode=mode)


def set_permissions(
    *, path: Path, uid: int | None = None, gid: int | None = None, mode: int | None = None
) -> None:
    try:
        os.chown(path, uid if uid is not None else -1, gid if gid is not None else -1)
    except OSError as e:
        if e.errno == errno.EACCES:
            pass  # On CIFS mounts where "uid=0,forceuid,gid=1000,forcegid" mount options
            # are set, this is not possible. So skip over.
        elif e.errno == errno.EPERM:
            pass  # On NFS mounts where "" mount options are set, we get an
            # "Operation not permitted" error when trying to change e.g.
            # the group permission.
        else:
            raise

    try:
        if mode is not None:
            os.chmod(path, mode)
    except OSError as e:
        if e.errno == errno.EACCES:
            pass  # On CIFS mounts where "uid=0,forceuid,gid=1000,forcegid" mount options
            # are set, this is not possible. So skip over.
        elif e.errno == errno.EPERM:
            pass  # On NFS mounts where "" mount options are set, we get an
            # "Operation not permitted" error when trying to change e.g.
            # the group permission.
        else:
            raise


class UnrecognizedBackupTypeError(Exception):
    ...


def load_backup_info(path: Path) -> SiteBackupInfo:
    with open(path) as f:
        raw_info: RawBackupInfo = json.load(f)
    if (type_ := raw_info["type"]) != SITE_BACKUP_MARKER:
        raise UnrecognizedBackupTypeError(f"Non-site backup type: {type_}")
    # Load the backup_id from the second right path component. This is the
    # base directory of the mkbackup.info file. The user might have moved
    # the directory, e.g. for having multiple backups. Allow that.
    # Maybe we need to changed this later when we allow multiple generations
    # of backups.
    filename, _, checksum = raw_info["files"][0]
    return SiteBackupInfo(
        config=raw_info["config"],
        filename=filename,
        checksum=checksum,
        finished=raw_info["finished"],
        hostname=raw_info["hostname"],
        job_id=raw_info["job_id"],
        site_id=raw_info["site_id"],
        site_version=raw_info["site_version"],
        size=raw_info["size"],
    )


def save_backup_info(info: SiteBackupInfo, path: Path) -> None:
    raw_info: RawBackupInfo = {
        "config": info.config,
        "files": [(info.filename, info.size, info.checksum)],
        "hostname": info.hostname,
        "job_id": info.job_id,
        "site_id": info.site_id,
        "site_version": info.site_version,
        "size": info.size,
        "type": SITE_BACKUP_MARKER,
        "finished": info.finished,
    }
    with path.open("w") as f:
        json.dump(raw_info, f, sort_keys=True, indent=4, separators=(",", ": "))


def verify_backup_file(info: SiteBackupInfo, archive_path: Path) -> None:
    checksum = info.checksum
    this_checksum = file_checksum(archive_path)
    if this_checksum != checksum:
        raise MKGeneralException(
            "The backup seems to be damaged and can not be restored. "
            "The checksum of the archive %s is wrong (got %s but "
            "expected %s)." % (archive_path, this_checksum, checksum)
        )


def file_checksum(path: Path) -> str:
    hash_md5 = md5(usedforsecurity=False)  # pylint: disable=unexpected-keyword-arg
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
