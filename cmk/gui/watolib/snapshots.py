#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import time
import shutil
import traceback
import tarfile
import subprocess
import cStringIO
from hashlib import sha256

import cmk.utils
import cmk.utils.store as store

import cmk.gui.config as config
import cmk.gui.multitar as multitar
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.i18n import _

var_dir = cmk.utils.paths.var_dir + "/wato/"
snapshot_dir = var_dir + "snapshots/"

backup_domains = {}


# TODO: Remove once new changes mechanism has been implemented
def create_snapshot(comment):
    store.mkdir(snapshot_dir)

    snapshot_name = "wato-snapshot-%s.tar" % time.strftime("%Y-%m-%d-%H-%M-%S",
                                                           time.localtime(time.time()))

    data = {}
    data["comment"] = _("Activated changes by %s.") % config.user.id

    if comment:
        data["comment"] += _("Comment: %s") % comment

    data["created_by"] = config.user.id
    data["type"] = "automatic"
    data["snapshot_name"] = snapshot_name

    _do_create_snapshot(data)
    _do_snapshot_maintenance()

    return snapshot_name


# TODO: Remove once new changes mechanism has been implemented
def _do_create_snapshot(data):
    snapshot_name = data["snapshot_name"]
    work_dir = snapshot_dir + "/workdir/%s" % snapshot_name

    try:
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        # Open / initialize files
        filename_target = "%s/%s" % (snapshot_dir, snapshot_name)
        filename_work = "%s/%s.work" % (work_dir, snapshot_name)

        file(filename_target, "w").close()

        def get_basic_tarinfo(name):
            tarinfo = tarfile.TarInfo(name)
            tarinfo.mtime = time.time()
            tarinfo.uid = 0
            tarinfo.gid = 0
            tarinfo.mode = 0o644
            tarinfo.type = tarfile.REGTYPE
            return tarinfo

        # Initialize the snapshot tar file and populate with initial information
        tar_in_progress = tarfile.open(filename_work, "w")

        for key in ["comment", "created_by", "type"]:
            tarinfo = get_basic_tarinfo(key)
            encoded_value = data[key].encode("utf-8")
            tarinfo.size = len(encoded_value)
            tar_in_progress.addfile(tarinfo, cStringIO.StringIO(encoded_value))

        tar_in_progress.close()

        # Process domains (sorted)
        subtar_info = {}

        for name, info in sorted(_get_default_backup_domains().items()):
            prefix = info.get("prefix", "")
            filename_subtar = "%s.tar.gz" % name
            path_subtar = "%s/%s" % (work_dir, filename_subtar)

            paths = ["." if x[1] == "" else x[1] for x in info.get("paths", [])]
            command = [
                "tar", "czf", path_subtar, "--ignore-failed-read", "--force-local", "-C", prefix
            ] + paths

            proc = subprocess.Popen(
                command,
                stdin=None,
                close_fds=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=prefix)
            _stdout, stderr = proc.communicate()
            exit_code = proc.wait()
            # Allow exit codes 0 and 1 (files changed during backup)
            if exit_code not in [0, 1]:
                raise MKGeneralException(
                    "Error while creating backup of %s (Exit Code %d) - %s.\n%s" %
                    (name, exit_code, stderr, command))

            subtar_hash = sha256(file(path_subtar).read()).hexdigest()
            subtar_signed = sha256(subtar_hash + _snapshot_secret()).hexdigest()
            subtar_info[filename_subtar] = (subtar_hash, subtar_signed)

            # Append tar.gz subtar to snapshot
            command = ["tar", "--append", "--file=" + filename_work, filename_subtar]
            proc = subprocess.Popen(command, cwd=work_dir, close_fds=True)
            proc.communicate()
            exit_code = proc.wait()

            if os.path.exists(filename_subtar):
                os.unlink(filename_subtar)

            if exit_code != 0:
                raise MKGeneralException("Error on adding backup domain %s to tarfile" % name)

        # Now add the info file which contains hashes and signed hashes for
        # each of the subtars
        info = ''.join(['%s %s %s\n' % (k, v[0], v[1]) for k, v in subtar_info.items()]) + '\n'

        tar_in_progress = tarfile.open(filename_work, "a")
        tarinfo = get_basic_tarinfo("checksums")
        tarinfo.size = len(info)
        tar_in_progress.addfile(tarinfo, cStringIO.StringIO(info))
        tar_in_progress.close()

        shutil.move(filename_work, filename_target)

    finally:
        shutil.rmtree(work_dir)


# TODO: Remove once new changes mechanism has been implemented
def _do_snapshot_maintenance():
    snapshots = []
    for f in os.listdir(snapshot_dir):
        if f.startswith('wato-snapshot-'):
            status = get_snapshot_status(f, check_correct_core=False)
            # only remove automatic and legacy snapshots
            if status.get("type") in ["automatic", "legacy"]:
                snapshots.append(f)

    snapshots.sort(reverse=True)
    while len(snapshots) > config.wato_max_snapshots:
        #log_audit(None, "snapshot-removed", _("Removed snapshot %s") % snapshots[-1])
        os.remove(snapshot_dir + snapshots.pop())


# Returns status information for snapshots or snapshots in progress
# TODO: Remove once new changes mechanism has been implemented
def get_snapshot_status(snapshot, validate_checksums=False, check_correct_core=True):
    if isinstance(snapshot, tuple):
        name, file_stream = snapshot
    else:
        name = snapshot
        file_stream = None

    # Defaults of available keys
    status = {
        "name": "",
        "total_size": 0,
        "type": None,
        "files": {},
        "comment": "",
        "created_by": "",
        "broken": False,
        "progress_status": "",
    }

    def access_snapshot(handler):
        if file_stream:
            file_stream.seek(0)
            return handler(file_stream)
        return handler(snapshot_dir + name)

    def check_size():
        if file_stream:
            file_stream.seek(0, os.SEEK_END)
            size = file_stream.tell()
        else:
            statinfo = os.stat(snapshot_dir + name)
            size = statinfo.st_size
        if size < 256:
            raise MKGeneralException(_("Invalid snapshot (too small)"))
        else:
            status["total_size"] = size

    def check_extension():
        # Check snapshot extension: tar or tar.gz
        if name.endswith(".tar.gz"):
            status["type"] = "legacy"
            status["comment"] = _("Snapshot created with old version")
        elif not name.endswith(".tar"):
            raise MKGeneralException(_("Invalid snapshot (incorrect file extension)"))

    def check_content():
        status["files"] = access_snapshot(multitar.list_tar_content)

        if status.get("type") == "legacy":
            allowed_files = ["%s.tar" % x[1] for x in _get_default_backup_domains()]
            for tarname in status["files"]:
                if tarname not in allowed_files:
                    raise MKGeneralException(
                        _("Invalid snapshot (contains invalid tarfile %s)") % tarname)
        else:  # new snapshots
            for entry in ["comment", "created_by", "type"]:
                if entry in status["files"]:

                    def handler(x, entry=entry):
                        return multitar.get_file_content(x, entry)

                    status[entry] = access_snapshot(handler)
                else:
                    raise MKGeneralException(_("Invalid snapshot (missing file: %s)") % entry)

    def check_core():
        if "check_mk.tar.gz" not in status["files"]:
            return

        cmk_tar = cStringIO.StringIO(
            access_snapshot(lambda x: multitar.get_file_content(x, 'check_mk.tar.gz')))
        files = multitar.list_tar_content(cmk_tar)
        using_cmc = os.path.exists(cmk.utils.paths.omd_root + '/etc/check_mk/conf.d/microcore.mk')
        snapshot_cmc = 'conf.d/microcore.mk' in files
        if using_cmc and not snapshot_cmc:
            raise MKGeneralException(
                _('You are currently using the Check_MK Micro Core, but this snapshot does not use the '
                  'Check_MK Micro Core. If you need to migrate your data, you could consider changing '
                  'the core, restoring the snapshot and changing the core back again.'))
        elif not using_cmc and snapshot_cmc:
            raise MKGeneralException(
                _('You are currently not using the Check_MK Micro Core, but this snapshot uses the '
                  'Check_MK Micro Core. If you need to migrate your data, you could consider changing '
                  'the core, restoring the snapshot and changing the core back again.'))

    def check_checksums():
        for f in status["files"].values():
            f['checksum'] = None

        # checksums field might contain three states:
        # a) None  - This is a legacy snapshot, no checksum file available
        # b) False - No or invalid checksums
        # c) True  - Checksums successfully validated
        if status['type'] == 'legacy':
            status['checksums'] = None
            return

        if 'checksums' not in status['files'].keys():
            status['checksums'] = False
            return

        # Extract all available checksums from the snapshot
        checksums_raw = access_snapshot(lambda x: multitar.get_file_content(x, 'checksums'))
        checksums = {}
        for l in checksums_raw.split('\n'):
            line = l.strip()
            if ' ' in line:
                parts = line.split(' ')
                if len(parts) == 3:
                    checksums[parts[0]] = (parts[1], parts[2])

        # now loop all known backup domains and check wheter or not they request
        # checksum validation, there is one available and it is valid
        status['checksums'] = True
        for domain_id, domain in backup_domains.items():
            filename = domain_id + '.tar.gz'
            if not domain.get('checksum', True) or filename not in status['files']:
                continue

            if filename not in checksums:
                continue

            checksum, signed = checksums[filename]

            # Get hashes of file in question
            def handler(x, filename=filename):
                return multitar.get_file_content(x, filename)

            subtar = access_snapshot(handler)
            subtar_hash = sha256(subtar).hexdigest()
            subtar_signed = sha256(subtar_hash + _snapshot_secret()).hexdigest()

            status['files'][filename]['checksum'] = (checksum == subtar_hash and
                                                     signed == subtar_signed)
            status['checksums'] &= status['files'][filename]['checksum']

    try:
        if len(name) > 35:
            status["name"] = "%s %s" % (name[14:24], name[25:33].replace("-", ":"))
        else:
            status["name"] = name

        if not file_stream:
            # Check if the snapshot build is still in progress...
            path_status = "%s/workdir/%s/%s.status" % (snapshot_dir, name, name)
            path_pid = "%s/workdir/%s/%s.pid" % (snapshot_dir, name, name)

            # Check if this process is still running
            if os.path.exists(path_pid):
                if os.path.exists(path_pid) \
                   and not os.path.exists("/proc/%s" % open(path_pid).read()):
                    status["progress_status"] = _("ERROR: Snapshot progress no longer running!")
                    raise MKGeneralException(
                        _("Error: The process responsible for creating the snapshot is no longer running!"
                         ))
                else:
                    status["progress_status"] = _("Snapshot build currently in progress")

            # Read snapshot status file (regularly updated by snapshot process)
            if os.path.exists(path_status):
                lines = file(path_status, "r").readlines()
                status["comment"] = lines[0].split(":", 1)[1]
                file_info = {}
                for filename in lines[1:]:
                    name, info = filename.split(":", 1)
                    text, size = info[:-1].split(":", 1)
                    file_info[name] = {"size": int(size), "text": text}
                status["files"] = file_info
                return status

        # Snapshot exists and is finished - do some basic checks
        check_size()
        check_extension()
        check_content()
        if check_correct_core:
            check_core()

        if validate_checksums:
            check_checksums()

    except Exception as e:
        if config.debug:
            status["broken_text"] = traceback.format_exc()
            status["broken"] = True
        else:
            status["broken_text"] = '%s' % e
            status["broken"] = True
    return status


def _get_default_backup_domains():
    domains = {}
    for domain, value in backup_domains.items():
        if "default" in value and not value.get("deprecated"):
            domains.update({domain: value})
    return domains


def _snapshot_secret():
    path = cmk.utils.paths.default_config_dir + '/snapshot.secret'
    try:
        return file(path).read()
    except IOError:
        # create a secret during first use
        try:
            s = os.urandom(256)
        except NotImplementedError:
            s = sha256(time.time())
        file(path, 'w').write(s)
        return s
