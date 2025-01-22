#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import grp
import json
import os
import pwd
import re
import socket
import subprocess
import sys
import time
from hashlib import md5
from pathlib import Path
from typing import Final

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.backup.job import Job, JobState
from cmk.utils.backup.stream import BackupStream, RestoreStream
from cmk.utils.backup.type_defs import Backup, RawBackupInfo, SiteBackupInfo

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


class UnrecognizedBackupTypeError(Exception): ...


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


def hostname() -> str:
    return socket.gethostname()


# The state file is in JSON format because it is 1:1 transferred
# to the Checkmk server through the Checkmk agent.
class State:
    def __init__(self, path: Path) -> None:
        self.path: Final = path
        self._state = JobState(
            state="started",
            pid=os.getpid(),
            started=time.time(),
            output="",
            bytes_per_second=0,
        )
        self._save()

    @property
    def current_state(self) -> JobState:
        return self._state

    def update_and_save(self, **update: object) -> None:
        self._state = self._state.copy(update=update)
        self._save()

    def _save(self) -> None:
        dumped = json.dumps(
            self.current_state.model_dump(),
            sort_keys=True,
            indent=4,
            separators=(",", ": "),
        )
        store.save_text_to_file(
            self.path,
            dumped,
        )


class InfoCalculator:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.hash = md5(usedforsecurity=False)  # pylint: disable=unexpected-keyword-arg
        self.size = 0

    @staticmethod
    def site_version(site_id: str) -> str:
        linkpath = os.readlink(f"/omd/sites/{site_id}/version")
        return linkpath.split("/")[-1]

    def update(self, chunk: bytes) -> None:
        self.hash.update(chunk)
        self.size += len(chunk)

    def info(self, job: Job, site_id: str) -> SiteBackupInfo:
        return SiteBackupInfo(
            config=job.config,
            filename=self.filename,
            checksum=self.hash.hexdigest(),
            finished=time.time(),
            hostname=hostname(),
            job_id=job.local_id,
            site_id=site_id,
            site_version=InfoCalculator.site_version(site_id),
            size=self.size,
        )


# Is used to duplicate output from stdout/stderr to a the job log. This
# is e.g. used during "mkbackup backup" to store the output.
class Log:
    def __init__(self, fd: int, state: State) -> None:
        self.fd = fd
        self.state = state
        if self.fd == 1:
            self.orig = sys.stdout
            sys.stdout = self
        else:
            self.orig = sys.stderr
            sys.stderr = self

        self.color_replace = re.compile("\033\\[\\d{1,2}m", re.UNICODE)

    def __del__(self) -> None:
        if self.fd == 1:
            sys.stdout = self.orig
        else:
            sys.stderr = self.orig

    def write(self, data: str) -> None:
        self.orig.write(data)
        try:
            self.state.update_and_save(
                output=self.state.current_state.output + self.color_replace.sub("", data)
            )
        except Exception as e:
            self.orig.write("Failed to add output: %s\n" % e)

    def flush(self) -> None:
        self.orig.flush()


class ProgressLogger:
    def __init__(self, state: State):
        self._state = state
        self._last_state_update = time.time()
        self._last_bps: float | None = None
        self._bytedif: int = 0

    def update(self, bytes_copied: int) -> None:
        timedif = time.time() - self._last_state_update
        self._bytedif += bytes_copied
        if timedif >= 1:
            this_bps = self._bytedif / timedif

            if self._last_bps is None:
                bps = this_bps  # initialize the value
            else:
                percentile, backlog_sec = 0.50, 10
                weight_per_sec = (1 - percentile) ** (1.0 / backlog_sec)
                weight = weight_per_sec**timedif
                bps = self._last_bps * weight + this_bps * (1 - weight)

            self._state.update_and_save(bytes_per_second=bps)
            self._last_state_update, self._last_bps = time.time(), bps
            self._bytedif = 0


def do_site_restore(
    backup: Backup,
    state: State,
    debug: bool,
) -> None:
    cmd = ["omd", "restore", "--kill", "-"]

    with subprocess.Popen(cmd, close_fds=True, stderr=subprocess.PIPE, stdin=subprocess.PIPE) as p:
        assert p.stdin is not None
        assert p.stderr is not None

        with backup.open() as backup_file:
            s = RestoreStream(
                stream=backup_file,
                is_alive=lambda: False,
                key_ident=backup.info.config["encrypt"],
                debug=debug,
            )
            progress_logger = ProgressLogger(state)
            try:
                for chunk in s.process():
                    p.stdin.write(chunk)
                    progress_logger.update(len(chunk))
            except OSError as e:
                log("Error while sending data to restore process: %s" % e)

        _stdout, stderr = p.communicate()

    if p.returncode:
        log(stderr.decode(encoding="utf-8", errors="strict"))
        raise MKGeneralException("Site restore failed")

    try:
        subprocess.check_output(["omd", "start"])
    except subprocess.CalledProcessError as exc:
        log(
            "Failed to start the site after restore.\n"
            f'Details: {exc.output.decode(encoding="utf-8")}'
        )


def do_site_backup(
    backup_path: Path, job: Job, state: State, verbose: int, debug: bool
) -> SiteBackupInfo:
    cmd = ["omd", "backup"]
    if not job.config["compress"]:
        cmd.append("--no-compression")
    if job.config.get("no_history", False):
        cmd.append("--no-past")
    cmd.append("-")

    site = current_site_id()
    info = InfoCalculator(backup_path.name)
    if verbose > 0:
        log("Command: %s" % " ".join(cmd))

    with subprocess.Popen(
        cmd,
        close_fds=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    ) as p:
        assert p.stdout is not None
        assert p.stderr is not None

        with open(backup_path, "wb") as backup_file:
            s = BackupStream(
                stream=p.stdout,
                is_alive=lambda: p.poll() is None,
                key_ident=job.config["encrypt"],
                debug=debug,
            )
            progress_logger = ProgressLogger(state)
            for chunk in s.process():
                backup_file.write(chunk)
                progress_logger.update(len(chunk))
                info.update(chunk)

        err = p.stderr.read().decode()

    if p.returncode != 0:
        raise MKGeneralException("Site backup failed: %s" % err)

    return info.info(job, site_id=site)
