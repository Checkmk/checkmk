#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
""" Check_MK comes with a simple backup and restore of the current
configuration and cache files (cmk --backup and cmk --restore). This
is implemented here. """

import io
import os
import shutil
import tarfile
import time
from pathlib import Path
from typing import List, Tuple

import cmk.utils.paths
import cmk.utils.render as render
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console

BackupPath = Tuple[str, str, str, str, bool]


def backup_paths() -> List[BackupPath]:
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


def do_backup(tarname: str) -> None:
    console.verbose("Creating backup file '%s'...\n", tarname)
    with tarfile.open(tarname, "w:gz") as tar:

        for (
            name,
            path,
            canonical_name,
            descr,
            is_dir,
        ) in backup_paths():

            absdir = os.path.abspath(path)
            if os.path.exists(path):
                if is_dir:
                    subtarname = name + ".tar"
                    subfile = io.BytesIO()
                    with tarfile.open(mode="w", fileobj=subfile, dereference=True) as subtar:
                        subtar.add(path, arcname=".")
                    subdata = subfile.getvalue()
                else:
                    subtarname = canonical_name
                    subdata = Path(absdir).read_bytes()

                info = tarfile.TarInfo(subtarname)
                info.mtime = int(time.time())
                info.uid = 0
                info.gid = 0
                info.size = len(subdata)
                info.mode = 0o644
                info.type = tarfile.REGTYPE
                info.name = subtarname
                console.verbose(
                    "  Added %s (%s) with a size of %s\n",
                    descr,
                    absdir,
                    render.fmt_bytes(info.size),
                )
                tar.addfile(info, io.BytesIO(subdata))

    console.verbose("Successfully created backup.\n")


def do_restore(tarname: str) -> None:
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
                    if f not in [".", ".."]:
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
        with tarfile.open(tarname, "r:gz") as tar:
            if is_dir:
                with tarfile.open(fileobj=tar.extractfile(name + ".tar")) as subtar:
                    if filename == ".":
                        subtar.extractall(basedir)
                    elif filename in subtar.getnames():
                        subtar.extract(filename, basedir)
            elif filename in tar.getnames():
                tar.extract(filename, basedir)

    console.verbose("Successfully restored backup.\n")
