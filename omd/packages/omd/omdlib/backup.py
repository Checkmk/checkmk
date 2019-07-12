#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
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

import os
import sys
import errno
import socket
import tarfile
import fnmatch
from typing import Tuple  # pylint: disable=unused-import


def backup_site_to_tarfile(site, fh, mode, options, verbose):
    tar = BackupTarFile.open(fileobj=fh, mode=mode, site=site, verbose=verbose)
    # Add the version symlink as first file to be able to
    # check a) the sitename and b) the version before reading
    # the whole tar archive. Important for streaming.
    # The file is added twice to get the first for validation
    # and the second for excration during restore.
    tar.add(site.dir + "/version", site.name + "/version")
    _backup_site_files_to_tarfile(site, tar, options)
    tar.close()


def get_exclude_patterns(options):
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


def _backup_site_files_to_tarfile(site, tar, options):
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

    def filter_files(filename):
        for glob_pattern in exclude:
            # patterns are relative to site directory, filename is full path.
            # strip of the site.dir prefix from full path
            if fnmatch.fnmatch(filename[len(site.dir) + 1:], glob_pattern):
                return True  # exclude this file
        return False

    tar.add(site.dir, site.name, exclude=filter_files)


class BackupTarFile(tarfile.TarFile):
    """We need to use our tarfile class here to perform a rrdcached SUSPEND/RESUME
    to prevent writing to individual RRDs during backups."""
    def __init__(self, name, mode, fileobj, **kwargs):
        self._site = kwargs.pop("site")
        self._verbose = kwargs.pop("verbose")
        self._site_stopped = self._site.is_stopped()
        self._rrdcached_socket_path = self._site.dir + "/tmp/run/rrdcached.sock"
        self._sock = None
        self._sites_path = os.path.realpath("/omd/sites")

        super(BackupTarFile, self).__init__(name, mode, fileobj, **kwargs)

    # We override this function to workaround an issue in the builtin add() method in
    # case it is called in recursive mode and a file vanishes between the os.listdir()
    # and the first file access (often seen os.lstat()) during backup. Instead of failing
    # like this we want to skip those files silently during backup.
    def add(self, name, arcname=None, recursive=True, exclude=None, filter=None):  # pylint: disable=redefined-builtin
        try:
            super(BackupTarFile, self).add(name, arcname, recursive, exclude, filter)
        except OSError as e:
            if e.errno != errno.ENOENT or arcname == self._site.name:
                raise

            if self._verbose:
                sys.stdout.write("Skipping vanished file: %s\n" % arcname)

    def addfile(self, tarinfo, fileobj=None):
        # In case of a stopped site or stopped rrdcached there is no
        # need to suspend rrd updates
        if self._site_stopped or not os.path.exists(self._rrdcached_socket_path):
            super(BackupTarFile, self).addfile(tarinfo, fileobj)
            return

        site_rel_path = tarinfo.name[len(self._site.name) + 1:]

        is_rrd = (site_rel_path.startswith("var/pnp4nagios/perfdata") \
                  or site_rel_path.startswith("var/check_mk/rrd")) \
                 and site_rel_path.endswith(".rrd")

        # rrdcached works realpath
        rrd_file_path = os.path.join(self._sites_path, tarinfo.name)

        if is_rrd:
            self._suspend_rrd_update(rrd_file_path)

        try:
            super(BackupTarFile, self).addfile(tarinfo, fileobj)
        finally:
            if is_rrd:
                self._resume_rrd_update(rrd_file_path)

    def _suspend_rrd_update(self, path):
        if self._verbose:
            sys.stdout.write("Pausing RRD updates for %s\n" % path)
        self._send_rrdcached_command("SUSPEND %s" % path)

    def _resume_rrd_update(self, path):
        if self._verbose:
            sys.stdout.write("Resuming RRD updates for %s\n" % path)
        self._send_rrdcached_command("RESUME %s" % path)

    def _resume_all_rrds(self):
        if self._verbose:
            sys.stdout.write("Resuming RRD updates for ALL\n")
        self._send_rrdcached_command("RESUMEALL")

    def _send_rrdcached_command(self, cmd):
        if not self._sock:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                self._sock.connect(self._rrdcached_socket_path)
            except socket.error as e:
                # ECONNRESET: Broken pipe
                # EPIPE:      Connection reset by peer
                #             Happens, for example, when the rrdcached is reloaded/restarted during backup
                if e.errno in (errno.ECONNRESET, errno.EPIPE):
                    self._sock = None
                    if self._verbose:
                        sys.stdout.write("skipping rrdcached command (%s)\n" % e)
                    return
                else:
                    raise

        try:
            if self._verbose:
                sys.stdout.write("rrdcached command: %s\n" % cmd)
            self._sock.sendall("%s\n" % cmd)

            answer = ""
            while not answer.endswith("\n"):
                answer += self._sock.recv(1024)
        except socket.error as e:
            if e.errno == errno.EPIPE:
                self._sock = None
                if self._verbose:
                    sys.stdout.write("skipping rrdcached command (broken pipe)\n")
                return
            else:
                raise

        code, msg = answer.strip().split(" ", 1)
        if code == "-1":
            if self._verbose:
                sys.stdout.write("rrdcached response: %r\n" % (answer))

            if cmd.startswith("SUSPEND") and msg.endswith("already suspended"):
                pass  # is fine when trying to suspend
            elif cmd.startswith("RESUME") and msg.endswith("not suspended"):
                pass  # is fine when trying to resume
            elif msg.endswith("No such file or directory"):
                pass  # is fine (unknown RRD)
            else:
                raise Exception("Error while processing rrdcached command (%s): %s" % (cmd, msg))

        elif self._verbose:
            sys.stdout.write("rrdcached response: %r\n" % (answer))

    def close(self):
        super(BackupTarFile, self).close()

        if self._sock:
            self._resume_all_rrds()
            self._sock.close()


def get_site_and_version_from_backup(tar):
    # type: (tarfile.TarFile) -> Tuple[str, str]
    """Get the first file of the tar archive. Expecting <site>/version symlink
    for validation reasons."""
    site_tarinfo = tar.next()
    if site_tarinfo is None:
        raise Exception("Failed to detect version of backed up site.")

    try:
        sitename, version_name = site_tarinfo.name.split("/", 1)
    except ValueError:
        raise Exception("Failed to detect version of backed up site. "
                        "Maybe the backup is from an incompatible version.")

    if version_name == "version":
        version = site_tarinfo.linkname.split('/')[-1]
    else:
        raise Exception("Failed to detect version of backed up site.")

    return sitename, version
