#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Cares about backing up the files of a site"""

import contextlib
import errno
import fnmatch
import os
import shutil
import socket
import sqlite3
import sys
import tarfile
from collections.abc import Callable, Iterator
from pathlib import Path
from types import TracebackType
from typing import override

from omdlib.contexts import SiteContext
from omdlib.global_options import GlobalOptions
from omdlib.site_paths import SitePaths
from omdlib.type_defs import CommandOptions

from cmk.utils.paths import mkbackup_lock_dir


def _try_backup_site_to_tarfile(
    tar: tarfile.TarFile,
    options: CommandOptions,
    site: SiteContext,
    global_opts: GlobalOptions,
) -> None:
    try:
        site_home = SitePaths.from_site_name(site.name).home
        _backup_site_to_tarfile(
            site.name,
            site_home,
            site.is_stopped(global_opts.verbose),
            tar,
            options,
            global_opts.verbose,
        )
    except OSError as e:
        sys.exit("Failed to perform backup: %s" % e)


def main_backup(
    _version_info: object,
    site: SiteContext,
    global_opts: GlobalOptions,
    args: list[str],
    options: CommandOptions,
    orig_working_directory: str,
) -> None:
    if len(args) == 0:
        sys.exit(
            'You need to provide either a path to the destination file or "-" for backup to stdout.'
        )

    dest = args[0]

    if dest == "-":
        with tarfile.open(
            fileobj=sys.stdout.buffer,
            mode="w|" if "no-compression" in options else "w|gz",
        ) as tar:
            _try_backup_site_to_tarfile(tar, options, site, global_opts)
    else:
        if not (dest_path := Path(dest)).is_absolute():
            dest_path = orig_working_directory / dest_path
        with tarfile.open(
            dest_path,
            mode="w:" if "no-compression" in options else "w:gz",
        ) as tar:
            _try_backup_site_to_tarfile(tar, options, site, global_opts)


def ensure_mkbackup_lock_dir_rights() -> None:
    try:
        mkbackup_lock_dir.mkdir(mode=0o0770, exist_ok=True)
        shutil.chown(mkbackup_lock_dir, group="omd")
        mkbackup_lock_dir.chmod(0o0770)
    except PermissionError:
        pass


def _backup_site_to_tarfile(
    site_name: str,
    site_home: str,
    site_is_stopped: bool,
    tar: tarfile.TarFile,
    options: CommandOptions,
    verbose: bool,
) -> None:
    if not os.path.isdir(site_home):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), site_home)

    excludes = get_exclude_patterns(options)

    def accepted_files(tarinfo: tarfile.TarInfo) -> bool:
        # patterns are relative to site directory, tarinfo.name includes site name.
        return not any(
            fnmatch.fnmatch(tarinfo.name[len(site_name) + 1 :], glob_pattern)
            for glob_pattern in excludes
        )

    with _RRDSocket(site_is_stopped, site_name, verbose) as rrd_socket:
        # Add the version symlink as first file to be able to
        # check a) the sitename and b) the version before reading
        # the whole tar archive. Important for streaming.
        # The file is added twice to get the first for validation
        # and the second for extraction during restore.
        _tar_add(
            rrd_socket,
            tar,
            site_home + "/version",
            site_name + "/version",
            verbose=verbose,
        )
        _tar_add(
            rrd_socket,
            tar,
            site_home,
            site_name,
            predicate=accepted_files,
            verbose=verbose,
        )


def get_exclude_patterns(options: CommandOptions) -> list[str]:
    excludes = []
    excludes.append("tmp/*")  # Exclude all tmpfs files

    # exclude all temporary files that are created during cmk.ccc.store writes
    excludes.append("*.mk.new*")
    excludes.append("var/log/.liveproxyd.state.new*")

    # exclude the "cache" / working directory for the Agent Bakery
    excludes.append("var/check_mk/agents/.files_cache/*")

    # exclude section cache because files may vanish during backup. It would
    # be better to have them in the backup and simply don't make the backup
    # fail in case a file vanishes during the backup, but the tarfile module
    # does not allow this.
    excludes.append("var/check_mk/persisted/*")
    excludes.append("var/check_mk/persisted_sections/*")

    if "no-rrds" in options or "no-past" in options:
        excludes.append("var/pnp4nagios/perfdata/*")
        excludes.append("var/pnp4nagios/spool/*")
        excludes.append("var/rrdcached/*")
        excludes.append("var/pnp4nagios/states/*")
        excludes.append("var/check_mk/rrd/*")

    if "no-agents" in options or "no-past" in options:
        excludes.append("var/check_mk/agents/*")

    if "no-logs" in options or "no-past" in options:
        # Logs of different components
        excludes.append("var/log/*.log*")
        excludes.append("var/log/*/*")
        excludes.append("var/pnp4nagios/log/*")
        excludes.append("var/pnp4nagios/perfdata.dump")
        # Nagios monitoring history
        excludes.append("var/nagios/nagios.log")
        excludes.append("var/nagios/archive/")
        # Event console
        excludes.append("var/mkeventd/history/*")
        # Micro Core monitoring history
        excludes.append("var/check_mk/core/history")
        excludes.append("var/check_mk/core/archive/*")
        # HW/SW Inventory history
        excludes.append("var/check_mk/inventory_archive/*/*")
        # WATO
        excludes.append("var/check_mk/wato/snapshots/*.tar")

    return excludes


class _RRDSocket(contextlib.AbstractContextManager):
    def __init__(self, site_stopped: bool, site_name: str, verbose: bool) -> None:
        self._rrdcached_socket_path = str(Path("site_dir") / "tmp/run/rrdcached.sock")
        self._site_requires_suspension = not site_stopped and os.path.exists(
            self._rrdcached_socket_path
        )
        self._sock: None | socket.socket = None
        self._verbose: bool = verbose
        self._sites_path: str = os.path.realpath("/omd/sites")
        self._site_name: str = site_name

    @contextlib.contextmanager
    def suspend_rrd_update_if_needed(self, tarinfo_name: str) -> Iterator[None]:
        if self._path_requires_suspension(tarinfo_name):
            self._suspend_rrd_update(tarinfo_name)
            try:
                yield
            finally:
                self._resume_rrd_update(tarinfo_name)
        else:
            yield

    def _path_requires_suspension(self, tarinfo_name: str) -> bool:
        # In case of a stopped site or stopped rrdcached there is no
        # need to suspend rrd updates
        site_rel_path = tarinfo_name[len(self._site_name) + 1 :]
        return (
            self._site_requires_suspension
            and (
                site_rel_path.startswith("var/pnp4nagios/perfdata")
                or site_rel_path.startswith("var/check_mk/rrd")
            )
            and tarinfo_name.endswith(".rrd")
        )

    def _suspend_rrd_update(self, tarinfo_name: str) -> None:
        # rrdcached works realpath
        path = os.path.join(self._sites_path, tarinfo_name)
        if self._verbose:
            sys.stdout.write("Pausing RRD updates for %s\n" % path)
        self._send_rrdcached_command("SUSPEND %s" % path)

    def _resume_rrd_update(self, tarinfo_name: str) -> None:
        # rrdcached works realpath
        path = os.path.join(self._sites_path, tarinfo_name)
        if self._verbose:
            sys.stdout.write("Resuming RRD updates for %s\n" % path)
        self._send_rrdcached_command("RESUME %s" % path)

    def _resume_all_rrds(self) -> None:
        if self._verbose:
            sys.stdout.write("Resuming RRD updates for ALL\n")
        self._send_rrdcached_command("RESUMEALL")

    def _send_rrdcached_command(self, cmd: str) -> None:
        if self._sock is None:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect(self._rrdcached_socket_path)
            except OSError as e:
                if self._verbose:
                    sys.stdout.write("skipping rrdcached command (%s)\n" % e)
                return
            self._sock = sock

        try:
            if self._verbose:
                sys.stdout.write("rrdcached command: %s\n" % cmd)
            self._sock.sendall(("%s\n" % cmd).encode("utf-8"))

            answer = ""
            while not answer.endswith("\n"):
                answer += self._sock.recv(1024).decode("utf-8")
        except OSError:
            self._sock = None
            if self._verbose:
                sys.stdout.write("skipping rrdcached command (broken pipe)\n")
            return
        except Exception:
            self._sock = None
            raise

        self._raise_error_from_answer(answer, cmd)

    def _raise_error_from_answer(self, answer: str, cmd: str) -> None:
        if self._verbose:
            sys.stdout.write("rrdcached response: %r\n" % (answer))
        code, msg = answer.strip().split(" ", 1)
        if code == "-1" and not (
            (cmd.startswith("SUSPEND") and msg.endswith("already suspended"))  # ok, if suspending
            or (cmd.startswith("RESUME") and msg.endswith("not suspended"))  # ok, if resuming
            or msg.endswith("No such file or directory")  # is fine (unknown RRD)
        ):
            raise Exception(f"Error while processing rrdcached command ({cmd}): {msg}")

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._resume_all_rrds()
        if self._sock is not None:
            self._sock.close()


def _tar_add(
    rrd_socket: _RRDSocket,
    tar: tarfile.TarFile,
    name: str,
    arcname: str,
    *,
    predicate: Callable[[tarfile.TarInfo], bool] = lambda _: True,
    verbose: bool,
) -> None:
    """Reimplement tar.add().

    Using tar.add() on a site directory is undesirable for two reasons:
      - When reading file information via tar.addfile and tar.gettarinfo, we
        don't want the rrd files to be modified. This addressed by RRDSocket.
      - A file may vanish between os.listdir and calling a tarfile.Tarfile
        method. Those files are silently skipped.
    """
    # Skip if somebody tries to archive the archive...
    if tar.name is not None and os.path.abspath(name) == tar.name:
        return
    directory_files = []
    try:
        with rrd_socket.suspend_rrd_update_if_needed(arcname):
            # Create a TarInfo object from the file.
            tarinfo = tar.gettarinfo(name, arcname)

            # Exclude files.
            if tarinfo is None or not predicate(tarinfo):
                return

            # Create a backup of history file and add it to the archive as history.sqlite.
            if name.endswith("var/mkeventd/history/history.sqlite"):
                backup_name = f"{name}.backup"
                try:
                    _backup_sqlite(name, backup_name)
                    backup_tarinfo = tar.gettarinfo(backup_name, arcname=arcname)
                    with open(backup_name, "rb") as file:
                        tar.addfile(backup_tarinfo, file)
                finally:
                    os.remove(backup_name)
                return

            # Append the tar header and data to the archive.
            if tarinfo.isfile():
                with open(name, "rb") as file:
                    tar.addfile(tarinfo, file)
            else:
                tar.addfile(tarinfo)

            if tarinfo.isdir():
                directory_files = sorted(os.listdir(name))
    except FileNotFoundError:
        if verbose:
            sys.stdout.write("Skipping vanished file: %s\n" % arcname)

    for filename in directory_files:
        _tar_add(  # recursive call
            rrd_socket,
            tar,
            os.path.join(name, filename),
            os.path.join(arcname, filename),
            predicate=predicate,
            verbose=verbose,
        )


def get_site_and_version_from_backup(tar: tarfile.TarFile) -> tuple[str, str]:
    """Get the first file of the tar archive. Expecting <site>/version symlink
    for validation reasons."""
    site_tarinfo = tar.next()
    if site_tarinfo is None:
        raise Exception("Failed to detect version of backed up site.")

    try:
        sitename, version_name = site_tarinfo.name.split("/", 1)
    except ValueError:
        raise Exception(
            "Failed to detect version of backed up site. "
            "Maybe the backup is from an incompatible version."
        )

    if version_name == "version":
        version = site_tarinfo.linkname.split("/")[-1]
    else:
        raise Exception("Failed to detect version of backed up site.")

    return sitename, version


def _backup_sqlite(src: str | Path, dst: str | Path) -> None:
    """Backup sqlite database file.

    Uses sqlite3 backup API to create a backup of the database file.
    """
    with (
        contextlib.closing(sqlite3.connect(src, timeout=10)) as src_conn,
        contextlib.closing(sqlite3.connect(dst)) as dst_conn,
    ):
        src_conn.backup(dst_conn)
