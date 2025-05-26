#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import glob
import io
import os
import shutil
import subprocess
import tarfile
import time
import traceback
from collections.abc import Callable, Generator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import IO, Literal, NotRequired, TypedDict, TypeVar

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId

import cmk.utils
import cmk.utils.paths

from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.utils.request_context import copy_request_context
from cmk.gui.watolib.audit_log import log_audit

from cmk import trace

var_dir = str(cmk.utils.paths.var_dir) + "/wato/"
snapshot_dir = var_dir + "snapshots/"

backup_domains: dict[str, "DomainSpec"] = {}


class DomainSpec(TypedDict):
    group: NotRequired[str]
    title: str
    prefix: Path | str
    paths: list[tuple[Literal["file", "dir"], str]]
    exclude: NotRequired[list[str]]
    default: NotRequired[Literal[True]]
    checksum: NotRequired[bool]
    cleanup: NotRequired[bool]
    deprecated: NotRequired[bool]
    pre_restore: NotRequired[Callable[[], list[str]]]
    post_restore: NotRequired[Callable[[], list[str]]]


class SnapshotData(TypedDict, total=False):
    comment: str
    created_by: Literal[""] | UserId
    type: Literal["automatic"]
    snapshot_name: str


class FileInfo(TypedDict, total=False):
    checksum: None | bool
    size: int
    text: str


class SnapshotStatus(TypedDict):
    broken: bool
    comment: str
    created_by: str
    files: dict[str, FileInfo]
    name: str
    progress_status: str
    total_size: int
    type: None | Literal["automatic", "legacy"]

    broken_text: NotRequired[str]
    # checksums field might contain three states:
    # a) None  - This is a legacy snapshot, no checksum file available
    # b) False - No or invalid checksums
    # c) True  - Checksums successfully validated
    checksums: NotRequired[None | bool]


@contextmanager
def create_snapshot_in_concurrent_thread(
    *,
    comment: str | None,
    created_by: UserId | None,
    secret: bytes,
    max_snapshots: int,
    use_git: bool,
    debug: bool,
    parent_span_context: trace.SpanContext,
) -> Generator[Future]:
    def create_snapshot_with_tracing() -> None:
        with trace.get_tracer().span(
            "create_backup_snapshot",
            trace.set_span_in_context(trace.NonRecordingSpan(parent_span_context)),
        ):
            create_snapshot(
                comment=comment,
                created_by=created_by,
                secret=secret,
                max_snapshots=max_snapshots,
                use_git=use_git,
                debug=debug,
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        yield pool.submit(copy_request_context(create_snapshot_with_tracing))


def create_snapshot(
    *,
    comment: str | None,
    created_by: UserId | None,
    secret: bytes,
    max_snapshots: int,
    use_git: bool,
    debug: bool,
) -> None:
    logger.debug("Start creating backup snapshot")
    start = time.time()
    Path(snapshot_dir).mkdir(mode=0o770, exist_ok=True, parents=True)

    snapshot_name = "wato-snapshot-%s.tar" % time.strftime(
        "%Y-%m-%d-%H-%M-%S", time.localtime(time.time())
    )

    data: SnapshotData = {}
    data["comment"] = _("Activated changes by %s.") % (created_by or "")

    if comment:
        data["comment"] += _("Comment: %s") % comment

    # with SuperUserContext the user.id is None; later this value will be encoded for tar
    data["created_by"] = created_by or ""
    data["type"] = "automatic"
    data["snapshot_name"] = snapshot_name

    _do_create_snapshot(data, secret)
    _do_snapshot_maintenance(max_snapshots, debug)

    log_audit(
        action="snapshot-created",
        message="Created snapshot %s" % snapshot_name,
        use_git=use_git,
        user_id=created_by,
    )
    logger.debug("Backup snapshot creation took %.4f", time.time() - start)


def _do_create_snapshot(data: SnapshotData, secret: bytes) -> None:
    snapshot_name = data["snapshot_name"]
    work_dir = snapshot_dir.rstrip("/") + "/workdir/%s" % snapshot_name

    try:
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        # Open / initialize files
        filename_target = f"{snapshot_dir}/{snapshot_name}"
        filename_work = f"{work_dir}/{snapshot_name}.work"

        with open(filename_target, "wb"):
            pass

        def get_basic_tarinfo(name: str) -> tarfile.TarInfo:
            tarinfo = tarfile.TarInfo(name)
            tarinfo.mtime = int(time.time())
            tarinfo.uid = 0
            tarinfo.gid = 0
            tarinfo.mode = 0o644
            tarinfo.type = tarfile.REGTYPE
            return tarinfo

        # Process domains (sorted)
        subtar_info: dict[str, tuple[str, str]] = {}

        for name, info in sorted(_get_default_backup_domains().items()):
            prefix = info.get("prefix", "")
            filename_subtar = "%s.tar.gz" % name
            path_subtar = f"{work_dir}/{filename_subtar}"

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
                capture_output=True,
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

            # TODO(Replace with HMAC?)
            subtar_signed = sha256(subtar_hash.encode() + secret).hexdigest()
            subtar_info[filename_subtar] = (subtar_hash, subtar_signed)

            # Append tar.gz subtar to snapshot
            command = ["tar", "--append", "--file=" + filename_work, filename_subtar]
            completed_proc = subprocess.run(command, cwd=work_dir, close_fds=True, check=False)

            if os.path.exists(filename_subtar):
                os.unlink(filename_subtar)

            if completed_proc.returncode:
                raise MKGeneralException("Error on adding backup domain %s to tarfile" % name)

        # Now add the info file which contains hashes and signed hashes for
        # each of the subtars and the initial information files. Adding the
        # initial information first will create a file unable to handle UID
        # and GID greater than 2097152 (Werk #16714)

        info_str = "".join([f"{k} {v[0]} {v[1]}\n" for k, v in subtar_info.items()]) + "\n"

        with tarfile.open(filename_work, "a") as tar_in_progress:
            tarinfo = get_basic_tarinfo("checksums")
            tarinfo.size = len(info_str)
            tar_in_progress.addfile(tarinfo, io.BytesIO(info_str.encode()))

            for key in ("comment", "created_by", "type"):
                tarinfo = get_basic_tarinfo(key)
                encoded_value = data[key].encode("utf-8")
                tarinfo.size = len(encoded_value)
                tar_in_progress.addfile(tarinfo, io.BytesIO(encoded_value))

        shutil.move(filename_work, filename_target)

    finally:
        shutil.rmtree(work_dir)


def _do_snapshot_maintenance(max_snapshots: int, debug: bool) -> None:
    snapshots = []
    for f in os.listdir(snapshot_dir):
        if f.startswith("wato-snapshot-"):
            status = get_snapshot_status(f, debug, check_correct_core=False)
            # only remove automatic and legacy snapshots
            if status.get("type") in ["automatic", "legacy"]:
                snapshots.append(f)

    snapshots.sort(reverse=True)
    while len(snapshots) > max_snapshots:
        # TODO can this be removed or will it ever come back to live?
        # log_audit("snapshot-removed", "Removed snapshot %s" % snapshots[-1])
        os.remove(snapshot_dir + snapshots.pop())


# Returns status information for snapshots or snapshots in progress
def get_snapshot_status(
    snapshot: str,
    debug: bool,
    validate_checksums: bool = False,
    check_correct_core: bool = True,
) -> SnapshotStatus:
    if isinstance(snapshot, tuple):
        name, file_stream = snapshot
    else:
        name = snapshot
        file_stream = None

    # Defaults of available keys
    status: SnapshotStatus = {
        "name": "",
        "total_size": 0,
        "type": None,
        "files": {},
        "comment": "",
        "created_by": "",
        "broken": False,
        "progress_status": "",
    }
    T = TypeVar("T")

    def access_snapshot(handler: Callable[[IO | str], T]) -> T:
        if file_stream:
            file_stream.seek(0)
            return handler(file_stream)
        return handler(snapshot_dir + name)

    def check_size() -> None:
        if file_stream:
            file_stream.seek(0, os.SEEK_END)
            size = file_stream.tell()
        else:
            statinfo = os.stat(snapshot_dir + name)
            size = statinfo.st_size
        if size < 256:
            raise MKGeneralException(_("Invalid snapshot (too small)"))
        status["total_size"] = size

    def check_extension() -> None:
        # Check snapshot extension: tar or tar.gz
        if name.endswith(".tar.gz"):
            status["type"] = "legacy"
            status["comment"] = _("Snapshot created with old version")
        elif not name.endswith(".tar"):
            raise MKGeneralException(_("Invalid snapshot (incorrect file extension)"))

    def check_content() -> None:
        status["files"] = access_snapshot(_list_tar_content)

        if status.get("type") == "legacy":
            allowed_files = ["%s.tar" % x[1] for x in _get_default_backup_domains()]
            for tarname in status["files"]:
                if tarname not in allowed_files:
                    raise MKGeneralException(
                        _("Invalid snapshot (contains invalid tarfile %s)") % tarname
                    )
        else:  # new snapshots
            for entry in ("comment", "created_by", "type"):
                if entry in status["files"]:

                    def handler(x: str | IO[bytes], entry: str = entry) -> str:
                        return _get_file_content(x, entry).decode("utf-8")

                    status[entry] = access_snapshot(handler)
                else:
                    raise MKGeneralException(_("Invalid snapshot (missing file: %s)") % entry)

    def check_core() -> None:
        if "check_mk.tar.gz" not in status["files"]:
            return

        cmk_tar = io.BytesIO(access_snapshot(lambda x: _get_file_content(x, "check_mk.tar.gz")))
        files = _list_tar_content(cmk_tar)
        using_cmc = (cmk.utils.paths.omd_root / "etc/check_mk/conf.d/microcore.mk").exists()
        snapshot_cmc = "conf.d/microcore.mk" in files
        if using_cmc and not snapshot_cmc:
            raise MKGeneralException(
                _(
                    "You are currently using the Checkmk Micro Core, but this snapshot does not use the "
                    "Checkmk Micro Core. If you need to migrate your data, you could consider changing "
                    "the core, restoring the snapshot and changing the core back again."
                )
            )
        if not using_cmc and snapshot_cmc:
            raise MKGeneralException(
                _(
                    "You are currently not using the Checkmk Micro Core, but this snapshot uses the "
                    "Checkmk Micro Core. If you need to migrate your data, you could consider changing "
                    "the core, restoring the snapshot and changing the core back again."
                )
            )

    def check_checksums() -> None:
        for f in status["files"].values():
            f["checksum"] = None

        if status["type"] == "legacy":
            status["checksums"] = None
            return

        if "checksums" not in status["files"]:
            status["checksums"] = False
            return

        # Extract all available checksums from the snapshot
        checksums_raw = access_snapshot(lambda x: _get_file_content(x, "checksums")).decode()
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
            def handler(x: str | IO[bytes], filename: str = filename) -> bytes:
                return _get_file_content(x, filename)

            subtar = access_snapshot(handler)
            subtar_hash = sha256(subtar).hexdigest()
            subtar_signed = sha256(subtar_hash.encode() + snapshot_secret()).hexdigest()

            checksum_result = checksum == subtar_hash and signed == subtar_signed
            status["files"][filename]["checksum"] = checksum_result
            assert status["checksums"] is not None  # We set it right in front of the loop...
            status["checksums"] &= checksum_result

    try:
        if len(name) > 35:
            status["name"] = "{} {}".format(name[14:24], name[25:33].replace("-", ":"))
        else:
            status["name"] = name

        if not file_stream:
            # Check if the snapshot build is still in progress...
            path_status = f"{snapshot_dir}/workdir/{name}/{name}.status"
            path_pid = f"{snapshot_dir}/workdir/{name}/{name}.pid"

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
                file_info: dict[str, FileInfo] = {}
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
        if debug:
            status["broken_text"] = traceback.format_exc()
            status["broken"] = True
        else:
            status["broken_text"] = "%s" % e
            status["broken"] = True
    return status


def _list_tar_content(the_tarfile: str | IO[bytes]) -> dict[str, FileInfo]:
    files: dict[str, FileInfo] = {}
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


def _get_file_content(the_tarfile: str | IO[bytes], filename: str) -> bytes:
    if not isinstance(the_tarfile, str):
        the_tarfile.seek(0)
        with tarfile.open("r", fileobj=the_tarfile) as tar:
            if obj := tar.extractfile(filename):
                return obj.read()
    else:
        with tarfile.open(the_tarfile, "r") as tar:
            if obj := tar.extractfile(filename):
                return obj.read()

    raise MKGeneralException(_("Failed to extract %s") % filename)


def _get_default_backup_domains() -> dict[str, DomainSpec]:
    domains = {}
    for domain, value in backup_domains.items():
        if "default" in value and not value.get("deprecated"):
            domains.update({domain: value})
    return domains


def snapshot_secret() -> bytes:
    path = cmk.utils.paths.default_config_dir / "snapshot.secret"
    try:
        return path.read_bytes()
    except OSError:
        # create a secret during first use
        s = os.urandom(256)
        path.write_bytes(s)
        return s


def extract_snapshot(
    tar: tarfile.TarFile,
    domains: dict[str, DomainSpec],
) -> None:
    """Used to restore a configuration snapshot for "discard changes"""
    tar_domains = {}
    for member in tar.getmembers():
        try:
            if member.name.endswith(".tar.gz"):
                tar_domains[member.name[:-7]] = member
        except Exception:
            pass

    # We are using the var_dir, because tmp_dir might not have enough space
    restore_dir = str(cmk.utils.paths.var_dir / "wato/snapshots/restore_snapshot")
    if not os.path.exists(restore_dir):
        os.makedirs(restore_dir)

    def check_domain(domain: DomainSpec, tar_member: tarfile.TarInfo) -> list[str]:
        errors = []

        prefix = domain["prefix"]

        def check_exists_or_writable(path_tokens: list[str]) -> bool:
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
            ["tar", "tzf", f"{restore_dir}/{tar_member.name}"],
            capture_output=True,
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
        os.unlink(f"{restore_dir}/{tar_member.name}")

        return errors

    def cleanup_domain(domain: DomainSpec) -> list[str]:
        # Some domains, e.g. authorization, do not get a cleanup
        if domain.get("cleanup") is False:
            return []

        def path_valid(_prefix: str | Path, path: str) -> bool:
            if path.startswith("/") or path.startswith(".."):
                return False
            return True

        # Remove old stuff
        for what, path in domain.get("paths", {}):
            if not path_valid(domain["prefix"], path):
                continue
            full_path = "{}/{}".format(domain["prefix"], path)
            if os.path.exists(full_path):
                if what == "dir":
                    exclude_files = []
                    for pattern in domain.get("exclude", []):
                        if "*" in pattern:
                            exclude_files.extend(
                                glob.glob("{}/{}".format(domain["prefix"], pattern))
                            )
                        else:
                            exclude_files.append("{}/{}".format(domain["prefix"], pattern))
                    _cleanup_dir(full_path, exclude_files)
                else:
                    os.remove(full_path)
        return []

    def extract_domain(domain: DomainSpec, tar_member: tarfile.TarInfo) -> list[str]:
        try:
            target_dir = domain.get("prefix")
            if not target_dir:
                return []
            # The complete tar.gz file never fits in stringIO buffer..
            tar.extract(tar_member, restore_dir)

            command = ["tar", "xzf", f"{restore_dir}/{tar_member.name}", "-C", target_dir]
            completed_process = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )

            if completed_process.returncode:
                return ["{} - {}".format(domain["title"], completed_process.stderr)]
        except Exception as e:
            return ["{} - {}".format(domain["title"], str(e))]

        return []

    def execute_restore(domain: DomainSpec, is_pre_restore: bool = True) -> list[str]:
        if is_pre_restore:
            if "pre_restore" in domain:
                return domain["pre_restore"]()
        elif "post_restore" in domain:
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
            lambda domain, _tar_member: execute_restore(domain, is_pre_restore=True),
        ),
        ("Cleanup", False, lambda domain, _tar_member: cleanup_domain(domain)),
        ("Extract", False, extract_domain),
        (
            "Post-Restore",
            False,
            lambda domain, _tar_member: execute_restore(domain, is_pre_restore=False),
        ),
    ]:
        errors: list[str] = []
        for name, tar_member in tar_domains.items():
            if name in domains:
                try:
                    dom_errors = handler(domains[name], tar_member)
                    errors.extend(dom_errors or [])
                except Exception:
                    # This should NEVER happen
                    err_info = (
                        f"Restore-Phase: {what}, Domain: {name}\nError: {traceback.format_exc()}"
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
def _cleanup_dir(root_path: str, exclude_files: list[str] | None = None) -> None:
    if exclude_files is None:
        exclude_files = []

    paths_to_remove = []
    files_to_remove = []
    for path, dirnames, filenames in os.walk(root_path):
        for dirname in dirnames:
            pathname = f"{path}/{dirname}"
            for entry in exclude_files:
                if entry.startswith(pathname):
                    break
            else:
                paths_to_remove.append(pathname)
        for filename in filenames:
            filepath = f"{path}/{filename}"
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
            except FileNotFoundError:
                pass
