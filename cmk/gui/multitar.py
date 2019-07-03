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
"""This module contains some helper functions dealing with the creation
of multi-tier tar files (tar files containing tar files)"""

import errno
import hashlib
import os
import tarfile
import time
import shutil
import cStringIO
import glob
import fnmatch
import subprocess
import traceback
import itertools
import multiprocessing

import cmk.utils.paths

from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException


class SnapshotComponentsParser(object):
    def __init__(self, component_list):
        super(SnapshotComponentsParser, self).__init__()
        self.components = []
        self._from_component_list(component_list)

    def _from_component_list(self, component_list):
        for component in component_list:
            self.components.append(SnapshotComponent(component))

    def get_component_names(self):
        return [x.name for x in self.components]


class SnapshotComponent(object):
    def __init__(self, component):
        self.component_type = None  # file or dir
        self.excludes = None  # exclude files from dir
        self.name = None  # the name of the subtar

        self.configured_path = None  # complete path, dir or file
        self.base_dir = None  # real path
        self.filename = None  # real filename, . for directories

        self._from_tuple(component)

    def _from_tuple(self, component):
        # Self explanatory, tuples are ugly to parse..
        if len(component) == 4:
            self.component_type, self.name, self.configured_path, excludes = component
            self.excludes = excludes[:]
        else:
            self.component_type, self.name, self.configured_path = component
            self.excludes = []

        self.configured_path = os.path.abspath(self.configured_path).rstrip("/")
        if self.component_type == "dir":
            self.filename = None
            self.base_dir = self.configured_path
        else:
            self.filename = os.path.basename(self.configured_path)
            self.base_dir = os.path.dirname(self.configured_path)

        self.excludes.append(".*new*")  # exclude all temporary files

    def __str__(self):
        return "type: %s, name: %s, configured_path: %s, base_dir: %s, filename: %s, excludes: %s" % \
                (self.component_type, self.name, self.configured_path, self.base_dir, self.filename, self.excludes)


class SnapshotCreationBase(object):
    def __init__(self, work_dir):
        super(SnapshotCreationBase, self).__init__()
        self._logger = logger.getChild("SnapshotCreationBase")
        self._work_dir = work_dir
        self._multitar_workdir = os.path.join(self._work_dir, "multitar_workdir")
        self._rsync_target_dir = os.path.join(self._multitar_workdir, "synced_files")
        self._tarfile_dir = os.path.join(self._multitar_workdir, "subtars")

        self._available_snapshots = {}

        # Debugging stuff
        self._statistics = {"rsync": [], "tar": {}}

    def output_statistics(self):
        self._logger.debug(_("============= Snapshot creation statistics ============="))
        for line in self._statistics["rsync"]:
            self._logger.debug("RSYNC: %s" % line)

        for filepath, lines in self._statistics["tar"].items():
            self._logger.debug("TAR: %s" % filepath)
            for line in lines:
                self._logger.debug("TAR:     - %s" % line)

    def _generate_snapshot(self,
                           target_filepath,
                           generic_components,
                           custom_components,
                           reuse_identical_snapshots=False):
        generate_start_time = time.time()
        if not custom_components:
            custom_components = []

        target_basename = os.path.basename(target_filepath)

        # Convert the tuple lists into a more managable format
        parsed_generic_components = SnapshotComponentsParser(generic_components)
        parsed_custom_components = SnapshotComponentsParser(custom_components)

        # This is not supported in CME, most of the CME files are customized!
        # Only the sitespecific custom component is currently supported
        if reuse_identical_snapshots:
            # Note/Requirement: There is (currently) no need to rsync custom components, since these components are always
            #                   generated on the fly in a custom directory
            # Check if a snapshot with the same content has already been packed.
            snapshot_fingerprint = self._get_snapshot_fingerprint(parsed_generic_components,
                                                                  parsed_custom_components)
            identical_snapshot = self._available_snapshots.get(snapshot_fingerprint)
            if identical_snapshot:
                os.symlink(identical_snapshot, target_filepath)
                self._statistics["tar"][os.path.basename(identical_snapshot)].append("Reused by %-40s (took %.4fsec)" %\
                                                                        (target_basename, time.time() - generate_start_time))
                return

        # Generate the final tar command
        required_subtars = ["%s.tar" % x for x in parsed_generic_components.get_component_names()]
        final_tar_command = [
            "tar", "czf", target_filepath, "--owner=0", "--group=0", "-C", self._tarfile_dir
        ] + required_subtars

        # Add custom files to final tar command
        if parsed_custom_components.components:
            base_dir = os.path.basename(target_filepath)
            tarfile_dir = "%s/custom_files/%s" % (self._tarfile_dir, base_dir)
            os.makedirs(tarfile_dir)

            self._create_custom_components_tarfiles(parsed_custom_components, tarfile_dir)
            required_custom_subtars = [
                "%s.tar" % x for x in parsed_custom_components.get_component_names()
            ]
            final_tar_command.extend(["-C", tarfile_dir] + required_custom_subtars)

        # Execute final tar command, create the snapshot
        self._execute_bash_commands([final_tar_command])

        if reuse_identical_snapshots:
            self._available_snapshots[snapshot_fingerprint] = target_filepath

        self._statistics["tar"].setdefault(target_basename, []).append(
            "Snapshot creation took %.4fsec" % (time.time() - generate_start_time))
        self._logger.debug("Snapshot %-30s took %.4fsec" % (target_basename,
                                                            (time.time() - generate_start_time)))

    def _get_rsync_and_tar_commands(self, component, rsync_target_dir, tarfile_target_dir):
        bash_commands = []

        # Rsync from source
        bash_commands.append(self._get_rsync_command(component, rsync_target_dir))

        # Create subtar
        bash_commands.append(
            self._get_subtar_command(component, rsync_target_dir, tarfile_target_dir))
        return bash_commands

    def _get_rsync_command(self, component, rsync_target_dir):
        exclude_args = list(
            itertools.chain.from_iterable([("--exclude", f) for f in component.excludes]))
        if component.component_type == "dir":
            # Sync the content of the directory, but not the directory itself
            archive_path = "%s/" % component.configured_path
        else:
            # component.configured_path points to the file
            archive_path = component.configured_path

        return ["rsync", "-av", "--delete", archive_path, rsync_target_dir] + exclude_args

    def _get_subtar_command(self, component, source_dir, tarfile_target_dir):
        if component.component_type == "dir":
            files_location = [source_dir, "."]
        else:
            files_location = [source_dir, component.filename]

        return [
            "tar", "cf",
            os.path.join(tarfile_target_dir, component.name + ".tar"), "--force-local", "-C"
        ] + files_location

    def _execute_bash_commands(self, commands, debug=False):
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
                    shell=False,
                    close_fds=True)
                stdout, stderr = p.communicate()
                if p.returncode != 0:
                    raise MKGeneralException(_("Activate changes error. Unable to prepare site snapshots. Failed command: %r; StdOut: %r; StdErr: %s") %\
                                                        (command, stdout, stderr))
            except OSError as e:
                raise MKGeneralException(
                    _("Activate changes error. Unable to prepare site snapshots. Failed command: %r, Exception: %s"
                     ) % (command, e))

    def _create_custom_components_tarfiles(self, parsed_custom_components, tarfile_dir):
        # Add any custom_components
        custom_components_commands = []
        for component in parsed_custom_components.components:
            if not os.path.exists(component.configured_path):
                # Create an empty tarfile for this component
                tar = tarfile.open(os.path.join(tarfile_dir, "%s.tar" % component.name), "w")
                tar.close()
                continue
            custom_components_commands.append(
                self._get_subtar_command(component, component.base_dir, tarfile_dir))
        self._execute_bash_commands(custom_components_commands)

    def _get_snapshot_fingerprint(self, parsed_generic_components, parsed_custom_components):
        custom_components_md5sum = self._get_custom_components_md5sum(parsed_custom_components)
        return tuple(
            sorted(parsed_generic_components.get_component_names()) + [custom_components_md5sum])

    def _get_custom_components_md5sum(self, parsed_custom_components):
        if not parsed_custom_components:
            return ""

        # Note: currently there is only one custom component, the sitespecific.mk
        #       If there additional custom components in the future this call will fail
        #       This function raises an exception in case of an unknown component
        def is_supported(component):
            if component.name != "sitespecific":
                return False
            elif component.component_type != "file":
                return False
            elif not component.configured_path.endswith("sitespecific.mk"):
                return False
            return True

        for component in parsed_custom_components.components:
            if not is_supported(component):
                raise MKGeneralException(
                    _("Identical snapshot detection not supported. Cannot create md5sum. "
                      "Unsupported custom snapshot component: %s.") % str(component))

        # Simply compute the checksum of the sitespecific.mk
        return hashlib.md5(file(
            parsed_custom_components.components[0].configured_path).read()).hexdigest()


class SnapshotWorkerSubprocess(SnapshotCreationBase, multiprocessing.Process):
    def __init__(self, work_dir):
        super(SnapshotWorkerSubprocess, self).__init__(work_dir)
        self._logger = logger.getChild("SnapshotWorker(%d)" % os.getpid())

    def run(self):
        try:
            self._generate_snapshot(*self._args, **self._kwargs)
        except Exception:
            self._logger.error("Error in subprocess")
            self._logger.error(traceback.format_exc())


class SnapshotCreator(SnapshotCreationBase):
    def __init__(self, work_dir, all_generic_components):
        super(SnapshotCreator, self).__init__(work_dir)
        self._setup_directories()
        self._parsed_generic_components = SnapshotComponentsParser(all_generic_components)
        self._worker_subprocesses = []

    def generate_snapshot(self, *args, **kwargs):
        self._generate_snapshot(*args, **kwargs)

    def generate_snapshot_in_subprocess(self, *args, **kwargs):
        new_worker = SnapshotWorkerSubprocess(self._work_dir)
        new_worker._args = args
        new_worker._kwargs = kwargs
        new_worker.daemon = True
        new_worker.start()
        self._worker_subprocesses.append(new_worker)

    def _setup_directories(self):
        for path in [self._rsync_target_dir, self._tarfile_dir]:
            if not os.path.exists(path):
                os.makedirs(path)

    def __enter__(self):
        self._prepare_generic_tar_files()
        return self

    def __exit__(self, exception_type, exception_value, tb):
        for worker in self._worker_subprocesses:
            worker.join()
        self.output_statistics()

    def _prepare_generic_tar_files(self):
        bash_commands = []
        prepare_start_time = time.time()
        for component in self._parsed_generic_components.components:
            rsync_target_dir = os.path.join(self._rsync_target_dir, component.name)
            os.makedirs(rsync_target_dir)

            if os.path.exists(component.configured_path):
                bash_commands.extend(
                    self._get_rsync_and_tar_commands(component, rsync_target_dir,
                                                     self._tarfile_dir))
            else:
                # create an empty tarfile for this component
                tar = tarfile.open(os.path.join(self._tarfile_dir, "%s.tar" % component.name), "w")
                tar.close()

        self._execute_bash_commands(bash_commands)
        self._statistics["rsync"].append(
            _("RSync of generic files took %.4fsec") % (time.time() - prepare_start_time))


# Can be removed soon, since it is deprecated by the SnapshotCreator
def create(tar_filename, components):
    tar = tarfile.open(tar_filename, "w:gz")
    start = time.time()
    for component in components:
        if len(component) == 4:
            what, name, path, excludes = component
        else:
            what, name, path = component
            excludes = []

        excludes = excludes[:]
        # exclude all temporary files
        excludes.append(".*new*")

        abspath = os.path.abspath(path)
        if os.path.exists(path):
            if what == "dir":
                basedir = abspath
                filename = "."
            else:
                basedir = os.path.dirname(abspath)
                filename = os.path.basename(abspath)

            subtar_buffer = cStringIO.StringIO()
            with tarfile.TarFile(fileobj=subtar_buffer, mode="w") as subtar_obj:

                def exclude_filter(x, excludes=excludes):
                    return filter_subtar_files(x, excludes)

                subtar_obj.add(
                    os.path.join(basedir, filename), arcname=filename, filter=exclude_filter)

            subtar_size = len(subtar_buffer.getvalue())
            subtar_buffer.seek(0)

            info = tarfile.TarInfo("%s.tar" % name)
            info.mtime = time.time()
            info.uid = 0
            info.gid = 0
            info.size = subtar_size
            info.mode = 0o644
            info.type = tarfile.REGTYPE

            tar.addfile(info, subtar_buffer)

    logger.debug(
        "Packaging %s took %.3fsec" % (os.path.basename(tar_filename), time.time() - start))


def filter_subtar_files(tarinfo, excludes):
    filename = os.path.basename(tarinfo.name)

    for exclude in excludes:
        if filename == exclude:
            return None
        elif fnmatch.fnmatchcase(filename, exclude):
            return None

    return tarinfo


def extract_from_buffer(buffer_, elements):
    stream = cStringIO.StringIO()
    stream.write(buffer_)
    stream.seek(0)
    if isinstance(elements, list):
        extract(tarfile.open(None, "r", stream), elements)
    elif isinstance(elements, dict):
        extract_domains(tarfile.open(None, "r", stream), elements)


def list_tar_content(the_tarfile):
    files = {}
    try:
        if not isinstance(the_tarfile, str):
            the_tarfile.seek(0)
            tar = tarfile.open("r", fileobj=the_tarfile)
        else:
            tar = tarfile.open(the_tarfile, "r")
        for x in tar.getmembers():
            files.update({x.name: {"size": x.size}})
    except Exception:
        return {}
    return files


def get_file_content(the_tarfile, filename):
    if not isinstance(the_tarfile, str):
        the_tarfile.seek(0)
        tar = tarfile.open("r", fileobj=the_tarfile)
    else:
        tar = tarfile.open(the_tarfile, "r")
    return tar.extractfile(filename).read()


def extract_domains(tar, domains):
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

    def check_domain(domain, tar_member):
        errors = []

        prefix = domain["prefix"]

        def check_exists_or_writable(path_tokens):
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
        p = subprocess.Popen(["tar", "tzf", "%s/%s" % (restore_dir, tar_member.name)],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if stderr:
            errors.append(_("Contains corrupt file %s") % tar_member.name)
            return errors

        for line in stdout:
            full_path = prefix + "/" + line
            path_tokens = full_path.split("/")
            check_exists_or_writable(path_tokens)

        # Cleanup
        os.unlink("%s/%s" % (restore_dir, tar_member.name))

        return errors

    def cleanup_domain(domain):
        # Some domains, e.g. authorization, do not get a cleanup
        if domain.get("cleanup") is False:
            return []

        def path_valid(prefix, path):
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
                    cleanup_dir(full_path, exclude_files)
                else:
                    os.remove(full_path)
        return []

    def extract_domain(domain, tar_member):
        try:
            target_dir = domain.get("prefix")
            if not target_dir:
                return []
            # The complete tar.gz file never fits in stringIO buffer..
            tar.extract(tar_member, restore_dir)

            command = ["tar", "xzf", "%s/%s" % (restore_dir, tar_member.name), "-C", target_dir]
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _stdout, stderr = p.communicate()
            exit_code = p.wait()
            if exit_code:
                return ["%s - %s" % (domain["title"], stderr)]
        except Exception as e:
            return ["%s - %s" % (domain["title"], str(e))]

        return []

    def execute_restore(domain, is_pre_restore=True):
        if is_pre_restore:
            if "pre_restore" in domain:
                return domain["pre_restore"]()
        else:
            if "post_restore" in domain:
                return domain["post_restore"]()
        return []

    total_errors = []
    logger.info("Restoring snapshot: %s" % tar.name)
    logger.info("Domains: %s" % ", ".join(tar_domains.keys()))
    for what, abort_on_error, handler in [
        ("Permissions", True, check_domain),
        ("Pre-Restore", True,
         lambda domain, tar_member: execute_restore(domain, is_pre_restore=True)),
        ("Cleanup", False, lambda domain, tar_member: cleanup_domain(domain)),
        ("Extract", False, extract_domain),
        ("Post-Restore", False,
         lambda domain, tar_member: execute_restore(domain, is_pre_restore=False))
    ]:
        errors = []
        for name, tar_member in tar_domains.items():
            if name in domains:
                try:
                    dom_errors = handler(domains[name], tar_member)
                    errors.extend(dom_errors or [])
                except Exception:
                    # This should NEVER happen
                    err_info = "Restore-Phase: %s, Domain: %s\nError: %s" % (what, name,
                                                                             traceback.format_exc())
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
                    _("<br>If there are permission problems, please ensure the site user has write permissions."
                     ))
            if abort_on_error:
                raise MKGeneralException(
                    _("%s - Unable to restore snapshot:<br>%s") % (what, "<br>".join(errors)))
            total_errors.extend(errors)

    # Cleanup
    wipe_directory(restore_dir)

    if total_errors:
        raise MKGeneralException(
            _("Errors on restoring snapshot:<br>%s") % "<br>".join(total_errors))


# Extract a tarball
def extract(tar, components):
    for component in components:
        if len(component) == 4:
            what, name, path, _excludes = component
        else:
            what, name, path = component

        try:
            try:
                subtarstream = tar.extractfile(name + ".tar")
            except Exception:
                continue  # may be missing, e.g. sites.tar is only present
                # if some sites have been created.

            if what == "dir":
                target_dir = path
            else:
                target_dir = os.path.dirname(path)

            # Remove old stuff
            if os.path.exists(path):
                if what == "dir":
                    wipe_directory(path)
                else:
                    os.remove(path)
            elif what == "dir":
                os.makedirs(path)

            # Extract without use of temporary files
            subtar = tarfile.open(fileobj=subtarstream)
            subtar.extractall(target_dir)
        except Exception:
            raise MKGeneralException(
                'Failed to extract subtar %s: %s' % (name, traceback.format_exc()))


# Try to cleanup everything starting from the root_path
# except the specific exclude files
def cleanup_dir(root_path, exclude_files=None):
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


def wipe_directory(path):
    for entry in os.listdir(path):
        if entry not in ['.', '..']:
            p = path + "/" + entry
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            else:
                try:
                    os.remove(p)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        continue
                    else:
                        raise
