#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import glob
import io
import os
import shutil
import subprocess
import tarfile
import time
import traceback
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import cmk.utils
import cmk.utils.paths
import cmk.utils.store as store

from cmk.gui.exceptions import MKGeneralException
from cmk.gui.globals import config, user
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.watolib.changes import log_audit

DomainSpec = Dict

var_dir = cmk.utils.paths.var_dir + "/wato/"
snapshot_dir = var_dir + "snapshots/"

backup_domains: Dict[str, Dict[str, Any]] = {}


# TODO: Remove once new changes mechanism has been implemented
def create_snapshot(comment):
    logger.debug("Start creating backup snapshot")
    start = time.time()
    store.mkdir(snapshot_dir)

    snapshot_name = "wato-snapshot-%s.tar" % time.strftime(
        "%Y-%m-%d-%H-%M-%S", time.localtime(time.time())
    )

    data: Dict[str, Any] = {}
    data["comment"] = _("Activated changes by %s.") % user.id

    if comment:
        data["comment"] += _("Comment: %s") % comment

    # with SuperUserContext the user.id is None; later this value will be encoded for tar
    data["created_by"] = "" if user.id is None else user.id
    data["type"] = "automatic"
    data["snapshot_name"] = snapshot_name

    _do_create_snapshot(data)
    _do_snapshot_maintenance()

    log_audit("snapshot-created", _("Created snapshot %s") % snapshot_name)
    logger.debug("Backup snapshot creation took %.4f", time.time() - start)


# TODO: Remove once new changes mechanism has been implemented
def _do_create_snapshot(data):
    snapshot_name = data["snapshot_name"]
    work_dir = snapshot_dir.rstrip("/") + "/workdir/%s" % snapshot_name

    try:
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        # Open / initialize files
        filename_target = "%s/%s" % (snapshot_dir, snapshot_name)
        filename_work = "%s/%s.work" % (work_dir, snapshot_name)

        with open(filename_target, "wb"):
            pass

        def get_basic_tarinfo(name):
            tarinfo = tarfile.TarInfo(name)
            tarinfo.mtime = int(time.time())
            tarinfo.uid = 0
            tarinfo.gid = 0
            tarinfo.mode = 0o644
            tarinfo.type = tarfile.REGTYPE
            return tarinfo

        # Initialize the snapshot tar file and populate with initial information
        with tarfile.open(filename_work, "w") as tar_in_progress:

            for key in ["comment", "created_by", "type"]:
                tarinfo = get_basic_tarinfo(key)
                encoded_value = data[key].encode("utf-8")
                tarinfo.size = len(encoded_value)
                tar_in_progress.addfile(tarinfo, io.BytesIO(encoded_value))

        # Process domains (sorted)
        subtar_info = {}

        for name, info in sorted(_get_default_backup_domains().items()):
            prefix = info.get("prefix", "")
            filename_subtar = "%s.tar.gz" % name
            path_subtar = "%s/%s" % (work_dir, filename_subtar)

            paths = ["." if x[1] == "" else x[1] for x in info.get("paths", [])]
            command = [
                "tar",
                "czf",
                path_subtar,
                "--ignore-failed-read",
                "--force-local",
                "-C",
                prefix,
            ] + paths

            completed_process = subprocess.run(
                command,
                stdin=None,
                close_fds=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=prefix,
                encoding="utf-8",
                check=False,
            )
            # Allow exit codes 0 and 1 (files changed during backup)
            if completed_process.returncode not in [0, 1]:
                raise MKGeneralException(
                    "Error while creating backup of %s (Exit Code %d) - %s.\n%s"
                    % (name, completed_process.returncode, completed_process.stderr, command)
                )

            with open(path_subtar, "rb") as subtar:
                subtar_hash = sha256(subtar.read()).hexdigest()

            subtar_signed = sha256(subtar_hash.encode() + _snapshot_secret()).hexdigest()
            subtar_info[filename_subtar] = (subtar_hash, subtar_signed)

            # Append tar.gz subtar to snapshot
            command = ["tar", "--append", "--file=" + filename_work, filename_subtar]
            completed_proc = subprocess.run(command, cwd=work_dir, close_fds=True, check=False)

            if os.path.exists(filename_subtar):
                os.unlink(filename_subtar)

            if completed_proc.returncode:
                raise MKGeneralException("Error on adding backup domain %s to tarfile" % name)

        # Now add the info file which contains hashes and signed hashes for
        # each of the subtars
        info = "".join(["%s %s %s\n" % (k, v[0], v[1]) for k, v in subtar_info.items()]) + "\n"

        with tarfile.open(filename_work, "a") as tar_in_progress:
            tarinfo = get_basic_tarinfo("checksums")
            tarinfo.size = len(info)
            tar_in_progress.addfile(tarinfo, io.BytesIO(info.encode()))

        shutil.move(filename_work, filename_target)

    finally:
        shutil.rmtree(work_dir)


# TODO: Remove once new changes mechanism has been implemented
def _do_snapshot_maintenance():
    snapshots = []
    for f in os.listdir(snapshot_dir):
        if f.startswith("wato-snapshot-"):
            status = get_snapshot_status(f, check_correct_core=False)
            # only remove automatic and legacy snapshots
            if status.get("type") in ["automatic", "legacy"]:
                snapshots.append(f)

    snapshots.sort(reverse=True)
    while len(snapshots) > config.wato_max_snapshots:
        # log_audit("snapshot-removed", _("Removed snapshot %s") % snapshots[-1])
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
    status: Dict[str, Any] = {
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
        status["total_size"] = size

    def check_extension():
        # Check snapshot extension: tar or tar.gz
        if name.endswith(".tar.gz"):
            status["type"] = "legacy"
            status["comment"] = _("Snapshot created with old version")
        elif not name.endswith(".tar"):
            raise MKGeneralException(_("Invalid snapshot (incorrect file extension)"))

    def check_content():
        status["files"] = access_snapshot(_list_tar_content)

        if status.get("type") == "legacy":
            allowed_files = ["%s.tar" % x[1] for x in _get_default_backup_domains()]
            for tarname in status["files"]:
                if tarname not in allowed_files:
                    raise MKGeneralException(
                        _("Invalid snapshot (contains invalid tarfile %s)") % tarname
                    )
        else:  # new snapshots
            for entry in ["comment", "created_by", "type"]:
                if entry in status["files"]:

                    def handler(x, entry=entry):
                        return _get_file_content(x, entry).decode("utf-8")

                    status[entry] = access_snapshot(handler)
                else:
                    raise MKGeneralException(_("Invalid snapshot (missing file: %s)") % entry)

    def check_core():
        if "check_mk.tar.gz" not in status["files"]:
            return

        cmk_tar = io.BytesIO(access_snapshot(lambda x: _get_file_content(x, "check_mk.tar.gz")))
        files = _list_tar_content(cmk_tar)
        using_cmc = (cmk.utils.paths.omd_root / "etc/check_mk/conf.d/microcore.mk").exists()
        snapshot_cmc = "conf.d/microcore.mk" in files
        if using_cmc and not snapshot_cmc:
            raise MKGeneralException(
                _(
                    "You are currently using the Check_MK Micro Core, but this snapshot does not use the "
                    "Check_MK Micro Core. If you need to migrate your data, you could consider changing "
                    "the core, restoring the snapshot and changing the core back again."
                )
            )
        if not using_cmc and snapshot_cmc:
            raise MKGeneralException(
                _(
                    "You are currently not using the Check_MK Micro Core, but this snapshot uses the "
                    "Check_MK Micro Core. If you need to migrate your data, you could consider changing "
                    "the core, restoring the snapshot and changing the core back again."
                )
            )

    def check_checksums():
        for f in status["files"].values():
            f["checksum"] = None

        # checksums field might contain three states:
        # a) None  - This is a legacy snapshot, no checksum file available
        # b) False - No or invalid checksums
        # c) True  - Checksums successfully validated
        if status["type"] == "legacy":
            status["checksums"] = None
            return

        if "checksums" not in status["files"]:
            status["checksums"] = False
            return

        # Extract all available checksums from the snapshot
        checksums_raw = access_snapshot(lambda x: _get_file_content(x, "checksums"))
        checksums = {}
        for l in checksums_raw.split("\n"):
            line = l.strip()
            if " " in line:
                parts = line.split(" ")
                if len(parts) == 3:
                    checksums[parts[0]] = (parts[1], parts[2])

        # now loop all known backup domains and check wheter or not they request
        # checksum validation, there is one available and it is valid
        status["checksums"] = True
        for domain_id, domain in backup_domains.items():
            filename = domain_id + ".tar.gz"
            if not domain.get("checksum", True) or filename not in status["files"]:
                continue

            if filename not in checksums:
                continue

            checksum, signed = checksums[filename]

            # Get hashes of file in question
            def handler(x, filename=filename):
                return _get_file_content(x, filename)

            subtar = access_snapshot(handler)
            subtar_hash = sha256(subtar).hexdigest()
            subtar_signed = sha256(subtar_hash.encode() + _snapshot_secret()).hexdigest()

            status["files"][filename]["checksum"] = (
                checksum == subtar_hash and signed == subtar_signed
            )
            status["checksums"] &= status["files"][filename]["checksum"]

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
                with Path(path_pid).open(encoding="utf-8") as f:
                    pid = int(f.read())

                if not os.path.exists("/proc/%d" % pid):
                    status["progress_status"] = _("ERROR: Snapshot progress no longer running!")
                    raise MKGeneralException(
                        _(
                            "Error: The process responsible for creating the snapshot is no longer running!"
                        )
                    )
                status["progress_status"] = _("Snapshot build currently in progress")

            # Read snapshot status file (regularly updated by snapshot process)
            if os.path.exists(path_status):
                with Path(path_status).open(encoding="utf-8") as f:
                    lines = f.readlines()

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
            status["broken_text"] = "%s" % e
            status["broken"] = True
    return status


def _list_tar_content(the_tarfile: Union[str, io.BytesIO]) -> Dict[str, Dict[str, int]]:
    files = {}
    try:
        if not isinstance(the_tarfile, str):
            the_tarfile.seek(0)
            with tarfile.open("r", fileobj=the_tarfile) as tar:
                for x in tar.getmembers():
                    files.update({x.name: {"size": x.size}})
        else:
            with tarfile.open(the_tarfile, "r") as tar:
                for x in tar.getmembers():
                    files.update({x.name: {"size": x.size}})

    except Exception:
        return {}
    return files


def _get_file_content(the_tarfile: Union[str, io.BytesIO], filename: str) -> bytes:
    if not isinstance(the_tarfile, str):
        the_tarfile.seek(0)
        with tarfile.open("r", fileobj=the_tarfile) as tar:
            obj = tar.extractfile(filename)
    else:
        with tarfile.open(the_tarfile, "r") as tar:
            obj = tar.extractfile(filename)

    if obj is None:
        raise MKGeneralException(_("Failed to extract %s") % filename)

    return obj.read()


def _get_default_backup_domains():
    domains = {}
    for domain, value in backup_domains.items():
        if "default" in value and not value.get("deprecated"):
            domains.update({domain: value})
    return domains


def _snapshot_secret() -> bytes:
    path = Path(cmk.utils.paths.default_config_dir, "snapshot.secret")
    try:
        return path.read_bytes()
    except IOError:
        # create a secret during first use
        try:
            s = os.urandom(256)
        except NotImplementedError:
            s = str(sha256(str(time.time()).encode())).encode()
        path.write_bytes(s)
        return s


def extract_snapshot(tar: tarfile.TarFile, domains: Dict[str, DomainSpec]) -> None:
    """Used to restore a configuration snapshot for "discard changes"""
    tar_domains = {}
    for member in tar.getmembers():
        try:
            if member.name.endswith(".tar.gz"):
                tar_domains[member.name[:-7]] = member
        except Exception:
            pass

    # We are using the var_dir, because tmp_dir might not have enough space
    restore_dir = cmk.utils.paths.var_dir + "/wato/snapshots/restore_snapshot"
    if not os.path.exists(restore_dir):
        os.makedirs(restore_dir)

    def check_domain(domain: DomainSpec, tar_member: tarfile.TarInfo) -> List[str]:
        errors = []

        prefix = domain["prefix"]

        def check_exists_or_writable(path_tokens: List[str]) -> bool:
            if not path_tokens:
                return False
            if os.path.exists("/".join(path_tokens)):
                if os.access("/".join(path_tokens), os.W_OK):
                    return True  # exists and writable

                errors.append(_("Permission problem: Path not writable %s") % "/".join(path_tokens))
                return False  # not writable

            return check_exists_or_writable(path_tokens[:-1])

        # The complete tar file never fits in stringIO buffer..
        tar.extract(tar_member, restore_dir)

        # Older versions of python tarfile handle empty subtar archives :(
        # This won't work: subtar = tarfile.open("%s/%s" % (restore_dir, tar_member.name))
        completed_process = subprocess.run(
            ["tar", "tzf", "%s/%s" % (restore_dir, tar_member.name)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            check=False,
        )
        if completed_process.stderr:
            errors.append(_("Contains corrupt file %s") % tar_member.name)
            return errors

        for line in completed_process.stdout:
            full_path = str(prefix) + "/" + line
            path_tokens = full_path.split("/")
            check_exists_or_writable(path_tokens)

        # Cleanup
        os.unlink("%s/%s" % (restore_dir, tar_member.name))

        return errors

    def cleanup_domain(domain: DomainSpec) -> List[str]:
        # Some domains, e.g. authorization, do not get a cleanup
        if domain.get("cleanup") is False:
            return []

        def path_valid(prefix: str, path: str) -> bool:
            if path.startswith("/") or path.startswith(".."):
                return False
            return True

        # Remove old stuff
        for what, path in domain.get("paths", {}):
            if not path_valid(domain["prefix"], path):
                continue
            full_path = "%s/%s" % (domain["prefix"], path)
            if os.path.exists(full_path):
                if what == "dir":
                    exclude_files = []
                    for pattern in domain.get("exclude", []):
                        if "*" in pattern:
                            exclude_files.extend(glob.glob("%s/%s" % (domain["prefix"], pattern)))
                        else:
                            exclude_files.append("%s/%s" % (domain["prefix"], pattern))
                    _cleanup_dir(full_path, exclude_files)
                else:
                    os.remove(full_path)
        return []

    def extract_domain(domain: DomainSpec, tar_member: tarfile.TarInfo) -> List[str]:
        try:
            target_dir = domain.get("prefix")
            if not target_dir:
                return []
            # The complete tar.gz file never fits in stringIO buffer..
            tar.extract(tar_member, restore_dir)

            command = ["tar", "xzf", "%s/%s" % (restore_dir, tar_member.name), "-C", target_dir]
            completed_process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                check=False,
            )

            if completed_process.returncode:
                return ["%s - %s" % (domain["title"], completed_process.stderr)]
        except Exception as e:
            return ["%s - %s" % (domain["title"], str(e))]

        return []

    def execute_restore(domain: DomainSpec, is_pre_restore: bool = True) -> List[str]:
        if is_pre_restore:
            if "pre_restore" in domain:
                return domain["pre_restore"]()
        else:
            if "post_restore" in domain:
                return domain["post_restore"]()
        return []

    total_errors = []
    logger.info("Restoring snapshot: %s", tar.name)
    logger.info("Domains: %s", ", ".join(tar_domains.keys()))
    for what, abort_on_error, handler in [
        ("Permissions", True, check_domain),
        (
            "Pre-Restore",
            True,
            lambda domain, tar_member: execute_restore(domain, is_pre_restore=True),
        ),
        ("Cleanup", False, lambda domain, tar_member: cleanup_domain(domain)),
        ("Extract", False, extract_domain),
        (
            "Post-Restore",
            False,
            lambda domain, tar_member: execute_restore(domain, is_pre_restore=False),
        ),
    ]:
        errors: List[str] = []
        for name, tar_member in tar_domains.items():
            if name in domains:
                try:
                    dom_errors = handler(domains[name], tar_member)
                    errors.extend(dom_errors or [])
                except Exception:
                    # This should NEVER happen
                    err_info = "Restore-Phase: %s, Domain: %s\nError: %s" % (
                        what,
                        name,
                        traceback.format_exc(),
                    )
                    errors.append(err_info)
                    logger.critical(err_info)
                    if not abort_on_error:
                        # At this state, the restored data is broken.
                        # We still try to apply the rest of the snapshot
                        # Hopefully the log entry helps in identifying the problem..
                        logger.critical("Snapshot restore FAILED! (possible loss of snapshot data)")
                        continue
                    break

        if errors:
            if what == "Permissions":
                errors = list(set(errors))
                errors.append(
                    _(
                        "<br>If there are permission problems, please ensure the site user has write permissions."
                    )
                )
            if abort_on_error:
                raise MKGeneralException(
                    _("%s - Unable to restore snapshot:<br>%s") % (what, "<br>".join(errors))
                )
            total_errors.extend(errors)

    # Cleanup
    _wipe_directory(restore_dir)

    if total_errors:
        raise MKGeneralException(
            _("Errors on restoring snapshot:<br>%s") % "<br>".join(total_errors)
        )


# Try to cleanup everything starting from the root_path
# except the specific exclude files
def _cleanup_dir(root_path: str, exclude_files: Optional[List[str]] = None) -> None:
    if exclude_files is None:
        exclude_files = []

    paths_to_remove = []
    files_to_remove = []
    for path, dirnames, filenames in os.walk(root_path):
        for dirname in dirnames:
            pathname = "%s/%s" % (path, dirname)
            for entry in exclude_files:
                if entry.startswith(pathname):
                    break
            else:
                paths_to_remove.append(pathname)
        for filename in filenames:
            filepath = "%s/%s" % (path, filename)
            if filepath not in exclude_files:
                files_to_remove.append(filepath)

    paths_to_remove.sort()
    files_to_remove.sort()

    for path in paths_to_remove:
        if os.path.exists(path) and os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)

    for filename in files_to_remove:
        if os.path.dirname(filename) not in paths_to_remove:
            os.remove(filename)


def _wipe_directory(path: str) -> None:
    for entry in os.listdir(path):
        p = path + "/" + entry
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                os.remove(p)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
