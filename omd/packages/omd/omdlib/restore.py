#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
import subprocess
import sys
from pathlib import Path

from omdlib.console import ok
from omdlib.contexts import SiteContext
from omdlib.init_scripts import call_init_scripts
from omdlib.options import CommandOptions
from omdlib.site_name import sitename_must_be_valid
from omdlib.site_paths import SitePaths
from omdlib.tmpfs import fstab_verify, unmount_tmpfs
from omdlib.user_processes import kill_site_user_processes
from omdlib.users_and_groups import user_verify, useradd
from omdlib.version_info import VersionInfo


def prepare_restore_as_root(
    version_info: VersionInfo, site: SiteContext, options: CommandOptions, verbose: bool
) -> None:
    reuse = False
    if "reuse" in options:
        reuse = True
        if not user_verify(version_info, site, allow_populated=True):
            sys.exit("Error verifying site user.")
        fstab_verify(site.name, site.tmp_dir)

    site_home = SitePaths.from_site_name(site.name).home
    sitename_must_be_valid(site.name, Path(site_home), reuse)

    if reuse:
        if not site.is_stopped(verbose) and "kill" not in options:
            sys.exit("Cannot restore '%s' while it is running." % (site.name))
        else:
            with subprocess.Popen(["omd", "stop", site.name]):
                pass
        unmount_tmpfs(site.name, site_home, site.tmp_dir, kill="kill" in options)

    if not reuse:
        uid = options.get("uid")
        gid = options.get("gid")
        useradd(version_info, site, uid, gid)  # None for uid/gid means: let Linux decide
    else:
        sys.stdout.write("Deleting existing site data...\n")
        shutil.rmtree(site_home)
        ok()

    os.mkdir(site_home)


def prepare_restore_as_site_user(site: SiteContext, options: CommandOptions, verbose: bool) -> None:
    if not site.is_stopped(verbose) and "kill" not in options:
        sys.exit("Cannot restore site while it is running.")
    site_home = SitePaths.from_site_name(site.name).home
    _verify_directory_write_access(site_home)

    sys.stdout.write("Stopping site processes...\n")
    call_init_scripts(site_home, "stop")
    kill_site_user_processes(site.name, verbose)
    ok()

    unmount_tmpfs(site.name, site_home, site.tmp_dir)

    sys.stdout.write("Deleting existing site data...")
    for f in os.listdir(site_home):
        path = site_home + "/" + f
        if os.path.islink(path) or os.path.isfile(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)
    ok()


# Scans all site directories and ensures the site user is able to write all directories.
# This is needed to prevent eventual permission issues during the rmtree process.
def _verify_directory_write_access(site_home: str) -> None:
    wrong = []
    for dirpath, dirnames, _filenames in os.walk(site_home):
        for dirname in dirnames:
            path = dirpath + "/" + dirname
            if os.path.islink(path):
                continue

            if not os.access(path, os.W_OK):
                wrong.append(path)

    if wrong:
        sys.exit(
            "Unable to start restore because of a permission issue.\n\n"
            "The restore needs to be able to clean the whole site to be able to restore "
            "the backup. Missing write access on the following paths:\n\n"
            "    %s" % "\n    ".join(wrong)
        )
