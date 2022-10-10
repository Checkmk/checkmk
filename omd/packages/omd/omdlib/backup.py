#!/usr/bin/env python3
#
#       U  ___ u  __  __   ____
#        \/"_ \/U|' \/ '|u|  _"\
#        | | | |\| |\/| |/| | | |
#    .-,_| |_| | | |  | |U| |_| |\
#     \_)-\___/  |_|  |_| |____/ u
#          \\   <<,-,,-.   |||_
#         (__)   (./  \.) (__)_)
#
# This file is part of OMD - The Open Monitoring Distribution.
# The official homepage is at <http://omdistro.org>.
#
# OMD  is  free software;  you  can  redistribute it  and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the  Free Software  Foundation  in  version 2.  OMD  is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Cares about backing up the files of a site"""

import contextlib
import fnmatch
import io
import os
import socket
import sys
import tarfile
from typing import BinaryIO, List, Tuple, Union

from omdlib.contexts import SiteContext
from omdlib.type_defs import CommandOptions


def backup_site_to_tarfile(
    site: SiteContext,
    fh: Union[BinaryIO, io.BufferedWriter],
    mode: str,
    options: CommandOptions,
    verbose: bool,
) -> None:

    # Mypy does not understand this: Unexpected keyword argument "verbose" for "open" of "TarFile", same for "site".
    with RRDSocket(site.dir, site.is_stopped(), site.name, verbose) as rrd_socket:
        with BackupTarFile.open(  # type: ignore[call-arg]
            fileobj=fh,
            mode=mode,
            site=site,
            verbose=verbose,
            rrd_socket=rrd_socket,
        ) as tar:
            # Add the version symlink as first file to be able to
            # check a) the sitename and b) the version before reading
            # the whole tar archive. Important for streaming.
            # The file is added twice to get the first for validation
            # and the second for excration during restore.
            tar.add(site.dir + "/version", site.name + "/version")
            _backup_site_files_to_tarfile(site, tar, options)


def get_exclude_patterns(options: CommandOptions) -> List[str]:
    excludes = []
    if "no-rrds" in options or "no-past" in options:
        excludes.append("var/pnp4nagios/perfdata/*")
        excludes.append("var/pnp4nagios/spool/*")
        excludes.append("var/rrdcached/*")
        excludes.append("var/pnp4nagios/states/*")
        excludes.append("var/check_mk/rrd/*")

    if "no-logs" in options or "no-past" in options:
        # Logs of different components
        excludes.append("var/log/*.log")
        excludes.append("var/log/*/*")
        excludes.append("var/pnp4nagios/log/*")
        excludes.append("var/pnp4nagios/perfdata.dump")
        # Nagios monitoring history
        excludes.append("var/nagios/nagios.log")
        excludes.append("var/nagios/archive/")
        # Event console
        excludes.append("var/mkeventd/history/*")
        # Microcore monitoring history
        excludes.append("var/check_mk/core/history")
        excludes.append("var/check_mk/core/archive/*")
        # HW/SW Inventory history
        excludes.append("var/check_mk/inventory_archive/*/*")
        # WATO
        excludes.append("var/check_mk/wato/snapshots/*.tar")

    return excludes


def _backup_site_files_to_tarfile(
    site: SiteContext, tar: "BackupTarFile", options: CommandOptions
) -> None:
    exclude = get_exclude_patterns(options)
    exclude.append("tmp/*")  # Exclude all tmpfs files

    # exclude all temporary files that are created during cmk.utils.store writes
    exclude.append("*.mk.new*")
    exclude.append("var/log/.liveproxyd.state.new*")

    # exclude section cache because files may vanish during backup. It would
    # be better to have them in the backup and simply don't make the backup
    # fail in case a file vanishes during the backup, but the tarfile module
    # does not allow this.
    exclude.append("var/check_mk/persisted/*")
    exclude.append("var/check_mk/persisted_sections/*")

    def filter_files(tarinfo):
        # patterns are relative to site directory, tarinfo.name includes site name.
        matches_exclude = any(
            fnmatch.fnmatch(tarinfo.name[len(site.name) + 1 :], glob_pattern)
            for glob_pattern in exclude
        )
        return None if matches_exclude else tarinfo

    tar.add(site.dir, site.name, filter=filter_files)


class BackupTarFile(tarfile.TarFile):
    """We need to use our tarfile class here to perform a rrdcached SUSPEND/RESUME
    to prevent writing to individual RRDs during backups."""

    def __init__(  # type:ignore[no-untyped-def]
        self, name, mode, fileobj, rrd_socket, **kwargs
    ) -> None:
        site = kwargs.pop("site")
        self._site_name = site.name
        self._verbose = kwargs.pop("verbose")
        self._rrd_socket = rrd_socket

        super().__init__(name, mode, fileobj, **kwargs)

    # We override this function to workaround an issue in the builtin add() method in
    # case it is called in recursive mode and a file vanishes between the os.listdir()
    # and the first file access (often seen os.lstat()) during backup. Instead of failing
    # like this we want to skip those files silently during backup.
    def add(
        self, name, arcname=None, recursive=True, *, filter=None
    ):  # pylint: disable=redefined-builtin
        if arcname == self._site_name:
            super().add(name, arcname, recursive, filter=filter)
            return
        try:
            super().add(name, arcname, recursive, filter=filter)
        except FileNotFoundError:
            if self._verbose:
                sys.stdout.write("Skipping vanished file: %s\n" % arcname)

    def addfile(self, tarinfo, fileobj=None):
        requires_suspension = self._rrd_socket.path_requires_suspension(tarinfo.name)
        if requires_suspension:
            self._rrd_socket.suspend_rrd_update(tarinfo.name)
        super().addfile(tarinfo, fileobj)
        if requires_suspension:
            self._rrd_socket.resume_rrd_update(tarinfo.name)


class RRDSocket(contextlib.AbstractContextManager):
    def __init__(self, site_dir: str, site_stopped: bool, site_name: str, verbose: bool) -> None:
        self._rrdcached_socket_path = site_dir + "/tmp/run/rrdcached.sock"
        self._site_requires_suspension = not site_stopped and os.path.exists(
            self._rrdcached_socket_path
        )
        self._sock: None | socket.socket = None
        self._verbose: bool = verbose
        self._sites_path: str = os.path.realpath("/omd/sites")
        self._site_name: str = site_name

    def path_requires_suspension(self, tarinfo_name: str) -> bool:
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

    def suspend_rrd_update(self, tarinfo_name: str) -> None:
        # rrdcached works realpath
        path = os.path.join(self._sites_path, tarinfo_name)
        if self._verbose:
            sys.stdout.write("Pausing RRD updates for %s\n" % path)
        self._send_rrdcached_command("SUSPEND %s" % path)

    def resume_rrd_update(self, tarinfo_name: str) -> None:
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
            except IOError as e:
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
        except IOError:
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
            raise Exception("Error while processing rrdcached command (%s): %s" % (cmd, msg))

    def __exit__(self, exc_type: object, exc_value: object, exc_tb: object) -> None:
        self._resume_all_rrds()
        if self._sock is not None:
            self._sock.close()


def get_site_and_version_from_backup(tar: tarfile.TarFile) -> Tuple[str, str]:
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
