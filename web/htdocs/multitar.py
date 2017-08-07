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

# This module contains some helper functions dealing with the creation
# of multi-tier tar files (tar files containing tar files)

import cmk.paths
import os, tarfile, time, shutil, cStringIO, grp
import glob
import fnmatch
import subprocess
import traceback
import itertools
from lib import *
from log import logger

def create(tar_filename, components):
    tar = tarfile.open(tar_filename, "w:gz")
    for component in components:
        if len(component) == 4:
            what, name, path, excludes = component
        else:
            what, name, path = component
            excludes = []

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
                subtar_obj.add(os.path.join(basedir, filename), arcname=filename,
                                filter=lambda x: filter_subtar_files(x, excludes))

            subtar_size = len(subtar_buffer.getvalue())
            subtar_buffer.seek(0)

            info = tarfile.TarInfo("%s.tar" % name)
            info.mtime = time.time()
            info.uid = 0
            info.gid = 0
            info.size = subtar_size
            info.mode = 0644
            info.type = tarfile.REGTYPE

            tar.addfile(info, subtar_buffer)


def filter_subtar_files(tarinfo, excludes):
    filename = os.path.basename(tarinfo.name)

    for exclude in excludes:
        if filename == exclude:
            return None
        elif fnmatch.fnmatchcase(filename, exclude):
            return None

    return tarinfo


def extract_from_buffer(buffer, elements):
    stream = cStringIO.StringIO()
    stream.write(buffer)
    stream.seek(0)
    if type(elements) == list:
        extract(tarfile.open(None, "r", stream), elements)
    elif type(elements) == dict:
        extract_domains(tarfile.open(None, "r", stream), elements)

def list_tar_content(the_tarfile):
    files = {}
    try:
        if type(the_tarfile) != str:
            the_tarfile.seek(0)
            tar = tarfile.open("r", fileobj = the_tarfile)
        else:
            tar = tarfile.open(the_tarfile, "r")
        map(lambda x: files.update({x.name: {"size": x.size}}), tar.getmembers())
    except Exception, e:
        return {}
    return files

def get_file_content(the_tarfile, filename):
    if type(the_tarfile) != str:
        the_tarfile.seek(0)
        tar = tarfile.open("r", fileobj = the_tarfile)
    else:
        tar = tarfile.open(the_tarfile, "r")
    return tar.extractfile(filename).read()


def extract_domains(tar, domains):
    tar_domains = {}
    for member in tar.getmembers():
        try:
            if member.name.endswith(".tar.gz"):
                tar_domains[member.name[:-7]] = member
        except Exception, e:
            pass

    # We are using the var_dir, because tmp_dir might not have enough space
    restore_dir = cmk.paths.var_dir + "/wato/snapshots/restore_snapshot"
    if not os.path.exists(restore_dir):
        os.makedirs(restore_dir)

    def check_domain(domain, tar_member):
        def can_write(path):
            return os.access(path, os.W_OK)
        errors = []

        prefix = domain["prefix"]

        def check_exists_or_writable(path_tokens):
            if not path_tokens:
                return False
            if os.path.exists("/".join(path_tokens)):
                if os.access("/".join(path_tokens), os.W_OK):
                    return True  # exists and writable
                else:
                    errors.append(_("Permission problem: Path not writable %s") % "/".join(path_tokens))
                    return False # not writable
            else:
                return check_exists_or_writable(path_tokens[:-1])

        # The complete tar file never fits in stringIO buffer..
        tar.extract(tar_member, restore_dir)

        # Older versions of python tarfile handle empty subtar archives :(
        # This won't work: subtar = tarfile.open("%s/%s" % (restore_dir, tar_member.name))
        p = subprocess.Popen(["tar", "tzf", "%s/%s" % (restore_dir, tar_member.name) ],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        if domain.get("cleanup") == False:
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

            command = [ "tar", "xzf", "%s/%s" % (restore_dir, tar_member.name),
                               "-C", target_dir ]
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            exit_code = p.wait()
            if exit_code:
                return [ "%s - %s" % (domain["title"], stderr) ]
        except Exception, e:
            return [ "%s - %s" % (domain["title"], str(e)) ]

        return []


    def execute_restore(domain, is_pre_restore = True):
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
                            ("Permissions",  True,  lambda domain, tar_member: check_domain(domain, tar_member)),
                            ("Pre-Restore",  True,  lambda domain, tar_member: execute_restore(domain, is_pre_restore = True)),
                            ("Cleanup",      False, lambda domain, tar_member: cleanup_domain(domain)),
                            ("Extract",      False, lambda domain, tar_member: extract_domain(domain, tar_member)),
                            ("Post-Restore", False, lambda domain, tar_member: execute_restore(domain, is_pre_restore = False))
                          ]:
        errors = []
        for name, tar_member in tar_domains.items():
            if name in domains:
                try:
                    dom_errors = handler(domains[name], tar_member)
                    errors.extend(dom_errors or [])
                except Exception, e:
                    # This should NEVER happen
                    err_info = "Restore-Phase: %s, Domain: %s\nError: %s" % (what, name, traceback.format_exc())
                    errors.append(err_info)
                    logger.critical(err_info)
                    if abort_on_error == False:
                        # At this state, the restored data is broken.
                        # We still try to apply the rest of the snapshot
                        # Hopefully the log entry helps in identifying the problem..
                        logger.critical("Snapshot restore FAILED! (possible loss of snapshot data)")
                        continue
                    break

        if errors:
            if what == "Permissions":
                errors = list(set(errors))
                errors.append(_("<br>If there are permission problems, please ensure the site user has write permissions."))
            if abort_on_error:
                raise MKGeneralException(_("%s - Unable to restore snapshot:<br>%s") % (what, "<br>".join(errors)))
            total_errors.extend(errors)

    # Cleanup
    wipe_directory(restore_dir)

    if total_errors:
        raise MKGeneralException(_("Errors on restoring snapshot:<br>%s") % "<br>".join(total_errors))


# Extract a tarball
def extract(tar, components):
    for component in components:
        if len(component) == 4:
            what, name, path, excludes = component
        else:
            what, name, path = component
            excludes = []

        try:
            try:
                subtarstream = tar.extractfile(name + ".tar")
            except:
                continue # may be missing, e.g. sites.tar is only present
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
            subtar = tarfile.open(fileobj = subtarstream)
            subtar.extractall(target_dir)
        except Exception, e:
            raise MKGeneralException('Failed to extract subtar %s: %s' % (name, traceback.format_exc()))

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
            shutil.rmtree(path)

    for filename in files_to_remove:
        if os.path.dirname(filename) not in paths_to_remove:
            os.remove(filename)

def wipe_directory(path):
    for entry in os.listdir(path):
        if entry not in [ '.', '..' ]:
            p = path + "/" + entry
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
		try:
                    os.remove(p)
                except OSError as e:
                    if e.errno == 2:  # no such file or directory
                        continue
                    else:
                        raise

