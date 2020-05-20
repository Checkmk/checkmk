#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Preparing the site configuration in distributed setups for synchronization"""

import sys
import ast
import errno
import hashlib
import os
import tarfile
import time
import shutil
import io
import traceback
import itertools
import multiprocessing
from types import TracebackType  # pylint: disable=unused-import
from typing import (  # pylint: disable=unused-import
    Any, Optional, Type, Tuple, Dict, Text, List, NamedTuple,
)

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import

import cmk.utils.cmk_subprocess as subprocess
import cmk.utils.store as store
import cmk.utils.paths

from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException

Command = List[str]


class ReplicationPath(
        NamedTuple("ReplicationPath", [
            ("ty", str),
            ("ident", str),
            ("site_path", str),
            ("excludes", List[str]),
        ])):
    def __new__(cls, ty, ident, site_path, excludes):
        # type: (str, str, str, List[str]) -> ReplicationPath

        if site_path.startswith("/"):
            raise Exception("ReplicationPath.path must be a path relative to the site root")
        cleaned_path = site_path.rstrip("/")

        if ".*new*" not in excludes:
            final_excludes = excludes[:]
            final_excludes.append(".*new*")  # exclude all temporary files
        else:
            final_excludes = excludes

        return super(ReplicationPath, cls).__new__(
            cls,
            ty=ty,
            ident=ident,
            site_path=cleaned_path,
            excludes=final_excludes,
        )


class SnapshotCreationBase(object):
    def __init__(self, activation_work_dir):
        # type: (str) -> None
        super(SnapshotCreationBase, self).__init__()
        self._logger = logger.getChild("SnapshotCreationBase")
        self._multitar_workdir = os.path.join(activation_work_dir, "multitar_workdir")
        self._rsync_target_dir = os.path.join(self._multitar_workdir, "synced_files")
        self._tarfile_dir = os.path.join(self._multitar_workdir, "subtars")

        self._available_snapshots = {}  # type: Dict[Tuple[str, ...], str]

        # Debugging stuff
        self._statistics_rsync = []  # type: List[Text]
        self._statistics_tar = {}  # type: Dict[str, List[str]]

    def output_statistics(self):
        # type: () -> None
        self._logger.debug("============= Snapshot creation statistics =============")
        for line in self._statistics_rsync:
            self._logger.debug("RSYNC: %s" % line)

        for filepath, lines in self._statistics_tar.items():
            self._logger.debug("TAR: %s" % filepath)
            for line in lines:
                self._logger.debug("TAR:     - %s" % line)

    def _generate_snapshot(self, snapshot_work_dir, target_filepath, generic_components,
                           custom_components, reuse_identical_snapshots):
        # type: (str, str, List[ReplicationPath], List[ReplicationPath], bool) -> None
        generate_start_time = time.time()
        target_basename = os.path.basename(target_filepath)
        store.makedirs(os.path.dirname(target_filepath))

        # This is not supported in CME, most of the CME files are customized!
        # Only the sitespecific custom component is currently supported
        if reuse_identical_snapshots:
            # Note/Requirement: There is (currently) no need to rsync custom components, since these components are always
            #                   generated on the fly in a custom directory
            # Check if a snapshot with the same content has already been packed.
            snapshot_fingerprint = self._get_snapshot_fingerprint(snapshot_work_dir,
                                                                  generic_components,
                                                                  custom_components)
            identical_snapshot = self._available_snapshots.get(snapshot_fingerprint)
            if identical_snapshot:
                os.symlink(identical_snapshot, target_filepath)
                self._statistics_tar[os.path.basename(identical_snapshot)].append(
                    "Reused by %-40s (took %.4fsec)" %
                    (target_basename, time.time() - generate_start_time))
                return

        # Generate the final tar command
        required_subtars = ["%s.tar" % c.ident for c in generic_components]
        final_tar_command = [
            "tar", "czf", target_filepath, "--owner=0", "--group=0", "-C", self._tarfile_dir
        ] + required_subtars

        # Add custom files to final tar command
        if custom_components:
            base_dir = os.path.basename(target_filepath)
            tarfile_dir = "%s/custom_files/%s" % (self._tarfile_dir, base_dir)
            os.makedirs(tarfile_dir)

            self._create_custom_components_tarfiles(snapshot_work_dir, custom_components,
                                                    tarfile_dir)
            required_custom_subtars = ["%s.tar" % c.ident for c in custom_components]
            final_tar_command.extend(["-C", tarfile_dir] + required_custom_subtars)

        # Execute final tar command, create the snapshot
        self._execute_bash_commands([final_tar_command])

        if reuse_identical_snapshots:
            self._available_snapshots[snapshot_fingerprint] = target_filepath

        self._statistics_tar.setdefault(target_basename, []).append(
            "Snapshot creation took %.4fsec" % (time.time() - generate_start_time))
        self._logger.debug("Snapshot %-30s took %.4fsec" % (target_basename,
                                                            (time.time() - generate_start_time)))

    def _get_rsync_and_tar_commands(self, component, rsync_target_dir, tarfile_target_dir):
        # type: (ReplicationPath, str, str) -> List[Command]
        bash_commands = []

        # Rsync from source
        bash_commands.append(self._get_rsync_command(component, rsync_target_dir))

        # Create subtar
        bash_commands.append(
            self._get_subtar_command(component, rsync_target_dir, tarfile_target_dir))
        return bash_commands

    def _get_rsync_command(self, component, rsync_target_dir):
        # type: (ReplicationPath, str) -> Command
        exclude_args = list(
            itertools.chain.from_iterable([("--exclude", f) for f in component.excludes]))

        source_path = os.path.join(cmk.utils.paths.omd_root, component.site_path)
        if component.ty == "dir":
            # Sync the content of the directory, but not the directory itself
            source_path += "/"

        return ["rsync", "-av", "--delete", source_path, rsync_target_dir] + exclude_args

    def _get_subtar_command(self, component, source_dir, tarfile_target_dir):
        # type: (ReplicationPath, str, str) -> Command
        if component.ty == "dir":
            files_location = [source_dir, "."]
        else:
            files_location = [source_dir, os.path.basename(component.site_path)]

        return [
            "tar", "cf",
            os.path.join(tarfile_target_dir, component.ident + ".tar"), "--force-local", "-C"
        ] + files_location

    def _execute_bash_commands(self, commands, debug=False):
        # type: (List[Command], bool) -> None
        if not commands:
            return

        for command in commands:
            if debug:
                self._logger.debug(" ".join(command))
            try:
                p = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    close_fds=True,
                    encoding="utf-8",
                )
                stdout, stderr = p.communicate()
                if p.returncode != 0:
                    raise MKGeneralException(
                        _("Activate changes error. Unable to prepare site snapshots. Failed command: %r; StdOut: %r; StdErr: %s"
                         ) % (command, stdout, stderr))
            except OSError as e:
                raise MKGeneralException(
                    _("Activate changes error. Unable to prepare site snapshots. Failed command: %r, Exception: %s"
                     ) % (command, e))

    def _create_custom_components_tarfiles(self, snapshot_work_dir, custom_components, tarfile_dir):
        # type: (str, List[ReplicationPath], str) -> None
        # Add any custom_components
        custom_components_commands = []
        for component in custom_components:
            source_path = os.path.join(snapshot_work_dir, component.site_path)

            if not os.path.exists(source_path):
                # Create an empty tarfile for this component
                tar = tarfile.open(os.path.join(tarfile_dir, "%s.tar" % component.ident), "w")
                tar.close()
                continue

            base_dir = source_path if component.ty == "dir" else os.path.dirname(source_path)

            custom_components_commands.append(
                self._get_subtar_command(component, base_dir, tarfile_dir))
        self._execute_bash_commands(custom_components_commands)

    def _get_snapshot_fingerprint(self, snapshot_work_dir, generic_components, custom_components):
        # type: (str, List[ReplicationPath], List[ReplicationPath]) -> Tuple[str, ...]
        custom_components_md5sum = self._get_custom_components_md5sum(snapshot_work_dir,
                                                                      custom_components)
        return tuple(sorted(c.ident for c in generic_components) + [custom_components_md5sum])

    def _get_custom_components_md5sum(self, snapshot_work_dir, custom_components):
        # type: (str, List[ReplicationPath]) -> str
        if not custom_components:
            return ""

        # Note: currently there is only one custom component, the sitespecific.mk
        #       If there additional custom components in the future this call will fail
        #       This function raises an exception in case of an unknown component
        def is_supported(component):
            # type: (ReplicationPath) -> bool
            return (component.ident == "sitespecific" and  #
                    component.ty == "file" and  #
                    component.site_path.endswith("sitespecific.mk"))

        for component in custom_components:
            if not is_supported(component):
                raise MKGeneralException(
                    _("Identical snapshot detection not supported. Cannot create md5sum. "
                      "Unsupported custom snapshot component: %s.") % str(component))

        # Simply compute the checksum of the sitespecific.mk
        source_path = os.path.join(snapshot_work_dir, custom_components[0].site_path)
        return hashlib.md5(open(source_path, "rb").read()).hexdigest()


class SnapshotCreator(SnapshotCreationBase):
    def __init__(self, activation_work_dir, all_generic_components):
        # type: (str, List[ReplicationPath]) -> None
        super(SnapshotCreator, self).__init__(activation_work_dir)
        self._setup_directories()
        self._generic_components = all_generic_components
        self._worker_subprocesses = []  # type: List[multiprocessing.Process]

    def generate_snapshot(self, snapshot_work_dir, target_filepath, generic_components,
                          custom_components, reuse_identical_snapshots):
        # type: (str, str, List[ReplicationPath], List[ReplicationPath], bool) -> None
        self._generate_snapshot(snapshot_work_dir, target_filepath, generic_components,
                                custom_components, reuse_identical_snapshots)

    def generate_snapshot_in_subprocess(self, snapshot_work_dir, target_filepath,
                                        generic_components, custom_components,
                                        reuse_identical_snapshots):
        # type: (str, str, List[ReplicationPath], List[ReplicationPath], bool) -> None
        def myworker():
            # type: () -> None
            log = logger.getChild("SnapshotWorker(%d)" % os.getpid())
            try:
                self._generate_snapshot(snapshot_work_dir, target_filepath, generic_components,
                                        custom_components, reuse_identical_snapshots)
            except Exception:
                log.error("Error in subprocess")
                log.error(traceback.format_exc())

        worker = multiprocessing.Process(target=myworker)
        worker.daemon = True
        worker.start()
        self._worker_subprocesses.append(worker)

    def _setup_directories(self):
        # type: () -> None
        for path in [self._rsync_target_dir, self._tarfile_dir]:
            if not os.path.exists(path):
                os.makedirs(path)

    def __enter__(self):
        # type: () -> SnapshotCreator
        self._prepare_generic_tar_files()
        return self

    def __exit__(self, exception_type, exception_value, tb):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        for worker in self._worker_subprocesses:
            worker.join()
        self.output_statistics()

    def _prepare_generic_tar_files(self):
        # type: () -> None
        bash_commands = []  # type: List[Command]
        prepare_start_time = time.time()
        for component in self._generic_components:
            rsync_target_dir = os.path.join(self._rsync_target_dir, component.ident)
            source_path = os.path.join(cmk.utils.paths.omd_root, component.site_path)

            os.makedirs(rsync_target_dir)

            if os.path.exists(source_path):
                bash_commands.extend(
                    self._get_rsync_and_tar_commands(component, rsync_target_dir,
                                                     self._tarfile_dir))
            else:
                # create an empty tarfile for this component
                tar = tarfile.open(os.path.join(self._tarfile_dir, "%s.tar" % component.ident), "w")
                tar.close()

        self._execute_bash_commands(bash_commands)
        self._statistics_rsync.append(
            _("RSync of generic files took %.4fsec") % (time.time() - prepare_start_time))


def extract_from_buffer(buffer_, base_dir, elements):
    # type: (bytes, Path, List[ReplicationPath]) -> None
    """Called during activate changes on the remote site to apply the received configuration"""
    if not isinstance(elements, list):
        raise NotImplementedError()

    stream = io.BytesIO()
    stream.write(buffer_)
    stream.seek(0)
    _extract(tarfile.open(None, "r", stream), base_dir, elements)


def _extract(tar, base_dir, components):
    # type: (tarfile.TarFile, Path, List[ReplicationPath]) -> None
    """Extract a tar archive with the new site configuration received from a central site"""
    for component in components:
        try:
            try:
                subtarstream = tar.extractfile(component.ident + ".tar")
            except Exception:
                continue  # may be missing, e.g. sites.tar is only present
                # if some sites have been created.

            component_path = str(base_dir.joinpath(component.site_path))

            if component.ty == "dir":
                target_dir = component_path
            else:
                target_dir = os.path.dirname(component_path)

            # Extract without use of temporary files
            subtar = tarfile.open(fileobj=subtarstream)

            # Remove old stuff
            if os.path.exists(component_path):
                if component.ident == "usersettings":
                    _update_usersettings(component_path, subtar)
                    continue
                if component.ident == "check_mk":
                    _update_check_mk(target_dir, subtar)
                    continue
                if component.ty == "dir":
                    _wipe_directory(component_path)
                else:
                    os.remove(component_path)
            elif component.ty == "dir":
                os.makedirs(component_path)

            subtar.extractall(target_dir)
        except Exception:
            raise MKGeneralException('Failed to extract subtar %s: %s' %
                                     (component.ident, traceback.format_exc()))


def _wipe_directory(path):
    # type: (str) -> None
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


def _get_local_users(tar_file):
    """The tar_file should contain var/check_mk/web/

From there on inspect every user's cached_profile.mk to recognize if they are a users
belonging to a certain customer in the CME."""
    return {
        os.path.normpath(os.path.dirname(entry)):
        ast.literal_eval(tar_file.extractfile(entry).read()).get('customer', None)
        for entry in tar_file.getnames()
        if os.path.basename(entry) == "cached_profile.mk"
    }


def _update_usersettings(path, tar_file):
    """Recursively traverse the usersettings dir and update files

    User can be split in two tiers.

    Customer-Users belong to a customer when working on the CME. They only
    work on the GUI of their corresponding remote site. They are allowed to
    customize their bookmarks, views, dashboards, reports, etc. These user
    local configurations are retained when receiving files from master as
    changes are activated.

        This meas all "user_*" files are retained during sync.

    Non-customer-users (e.g. GLOBAL users) normally work on the central
    site and thus they should be able to use their customizations when they
    log into remote sites. Thus all files are synced in their case.


    No backup of the remote site dir happens during sync, data is removed,
    added, skipped in place to avoid collisions."""
    def is_user_file(filepath):
        entry = os.path.basename(filepath)
        return entry.startswith('user_') or entry in [
            'tableoptions.mk', 'treestates.mk', 'sidebar.mk'
        ]

    user_p = _get_local_users(tar_file)
    user = os.path.basename(path)

    for entry in os.listdir(path):
        p = path + "/" + entry
        if os.path.isdir(p):
            _update_usersettings(p, tar_file)
        elif (user_p.get(user, False) and is_user_file(entry)):
            continue
        else:
            os.remove(p)

    # This verifies the function is at a user level path to extract tar_file
    if user in user_p:
        members = (m for m in tar_file.getmembers() if m.name.startswith('./' + user + '/'))
        if user_p[user] is not None:
            members = (m for m in members if not is_user_file(m.name))

        tar_file.extractall(os.path.dirname(path), members=members)


def _update_check_mk(path, tar_file):
    "extract check_mk/conf.d/wato folder but skip overwriting user notification_rules"

    members = [m for m in tar_file.getmembers() if m.name != "./contacts.mk"]
    for entry in members:
        filepath = os.path.join(path, entry.name)
        if os.path.isfile(filepath):
            os.remove(filepath)

    tar_file.extractall(path, members=members)

    master_vars = {"contacts": {}}  # type: Dict[str, Any]
    eval(tar_file.extractfile("./contacts.mk").read(), {}, master_vars)

    site_vars = {"contacts": {}}  # type: Dict[str, Any]
    with Path(path).joinpath("contacts.mk").open(encoding="utf-8") as f:
        eval(f.read(), {}, site_vars)

    site_contacts = _update_contacts_dict(master_vars["contacts"], site_vars["contacts"])

    store.save_to_mk_file(os.path.join(path, "contacts.mk"), "contacts", site_contacts)


def _update_contacts_dict(master, site):
    # type: (Dict, Dict) -> Dict

    site_contacts = {}

    for user_id, settings in master.items():
        user_notifications = site.get(user_id, {}).get("notification_rules")

        if user_notifications and settings.get("customer") is not None:
            settings["notification_rules"] = user_notifications

        site_contacts.update({user_id: settings})

    return site_contacts
