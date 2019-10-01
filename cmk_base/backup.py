#!/usr/bin/env python
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
""" Check_MK comes with a simple backup and restore of the current
configuration and cache files (cmk --backup and cmk --restore). This
is implemented here. """

import os
import shutil
import tarfile
import time
import cStringIO as StringIO

import cmk.utils.paths
import cmk.utils.render as render
from cmk.utils.exceptions import MKGeneralException

import cmk_base.console as console


def backup_paths():
    # TODO: Refactor to named tuples
    # yapf: disable
    return [
        # tarname               path                 canonical name   description                is_dir
        ('check_mk_configfile', cmk.utils.paths.main_config_file,    "main.mk",       "Main configuration file",           False, ),
        ('final_mk',            cmk.utils.paths.final_config_file,   "final.mk",      "Final configuration file final.mk", False, ),
        ('check_mk_configdir',  cmk.utils.paths.check_mk_config_dir, "",              "Configuration sub files",           True,  ),
        ('autochecksdir',       cmk.utils.paths.autochecks_dir,      "",              "Automatically inventorized checks", True,  ),
        ('counters_directory',  cmk.utils.paths.counters_dir,        "",              "Performance counters",              True,  ),
        ('tcp_cache_dir',       cmk.utils.paths.tcp_cache_dir,       "",              "Agent cache",                       True,  ),
        ('logwatch_dir',        cmk.utils.paths.logwatch_dir,        "",              "Logwatch",                          True,  ),
    ]
    # yapf: enable


def do_backup(tarname):
    console.verbose("Creating backup file '%s'...\n", tarname)
    tar = tarfile.open(tarname, "w:gz")

    for name, path, canonical_name, descr, is_dir, in backup_paths():

        absdir = os.path.abspath(path)
        if os.path.exists(path):
            if is_dir:
                subtarname = name + ".tar"
                subfile = StringIO.StringIO()
                subtar = tarfile.open(mode="w", fileobj=subfile, dereference=True)
                subtar.add(path, arcname=".")
                subdata = subfile.getvalue()
            else:
                subtarname = canonical_name
                subdata = open(absdir).read()

            info = tarfile.TarInfo(subtarname)
            info.mtime = time.time()
            info.uid = 0
            info.gid = 0
            info.size = len(subdata)
            info.mode = 0o644
            info.type = tarfile.REGTYPE
            info.name = subtarname
            console.verbose("  Added %s (%s) with a size of %s\n", descr, absdir,
                            render.fmt_bytes(info.size))
            tar.addfile(info, StringIO.StringIO(subdata))

    tar.close()
    console.verbose("Successfully created backup.\n")


def do_restore(tarname):
    console.verbose("Restoring from '%s'...\n", tarname)

    if not os.path.exists(tarname):
        raise MKGeneralException("Unable to restore: File does not exist")

    for name, path, canonical_name, descr, is_dir in backup_paths():
        absdir = os.path.abspath(path)
        if is_dir:
            basedir = absdir
            filename = "."
            if os.path.exists(absdir):
                console.verbose("  Deleting old contents of '%s'\n", absdir)
                # The path might point to a symbalic link. So it is no option
                # to call shutil.rmtree(). We must delete just the contents
                for f in os.listdir(absdir):
                    if f not in ['.', '..']:
                        try:
                            p = absdir + "/" + f
                            if os.path.isdir(p):
                                shutil.rmtree(p)
                            else:
                                os.remove(p)
                        except Exception as e:
                            console.warning("  Cannot delete %s: %s", p, e)
        else:
            basedir = os.path.dirname(absdir)
            filename = os.path.basename(absdir)
            canonical_path = basedir + "/" + canonical_name
            if os.path.exists(canonical_path):
                console.verbose("  Deleting old version of '%s'\n", canonical_path)
                os.remove(canonical_path)

        if not os.path.exists(basedir):
            console.verbose("  Creating directory %s\n", basedir)
            os.makedirs(basedir)

        console.verbose("  Extracting %s (%s)\n", descr, absdir)
        tar = tarfile.open(tarname, "r:gz")
        if is_dir:
            subtar = tarfile.open(fileobj=tar.extractfile(name + ".tar"))
            if filename == ".":
                subtar.extractall(basedir)
            elif filename in subtar.getnames():
                subtar.extract(filename, basedir)
            subtar.close()
        elif filename in tar.getnames():
            tar.extract(filename, basedir)
        tar.close()

    console.verbose("Successfully restored backup.\n")
