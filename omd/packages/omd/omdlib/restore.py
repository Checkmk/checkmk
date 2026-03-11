#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
import sys
from pathlib import Path

from omdlib.console import ok
from omdlib.contexts import SiteContext
from omdlib.init_scripts import call_init_scripts
from omdlib.site_paths import SitePaths
from omdlib.tmpfs import unmount_tmpfs
from omdlib.user_processes import kill_site_user_processes


def prepare_restore_as_site_user(site: SiteContext, kill: bool, verbose: bool) -> None:
    site_home = SitePaths.from_site_name(site.name).home
    _verify_directory_write_access(site_home)
    if Path(site_home, "etc/init.d/").exists():
        Path(site_home, "var/log").mkdir(parents=True, exist_ok=True)
        if not site.is_stopped(verbose) and not kill:
            sys.exit("Cannot restore site while it is running.")
        sys.stdout.write("Stopping site processes...\n")
        call_init_scripts(site_home, "stop")
    else:
        sys.stdout.write("Stopping site processes...\n")
    kill_site_user_processes(site.name, verbose, exclude_current_and_parents=True)
    ok()

    unmount_tmpfs(site)

    sys.stdout.write("Deleting existing site data...")
    clear_site_home(site_home)
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


def clear_site_home(site_home: str) -> None:
    for f in os.listdir(site_home):
        path = site_home + "/" + f
        if os.path.islink(path) or not os.path.isdir(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)
