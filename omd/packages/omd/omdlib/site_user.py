#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import sys
from pathlib import Path

from omdlib.config_api import Config
from omdlib.config_hooks import create_config_environment, load_config
from omdlib.contexts import SiteContext
from omdlib.site_paths import SitePaths
from omdlib.users_and_groups import KEEP, switch_to_site_user


def _clear_environment() -> None:
    for key in os.environ:
        if key not in KEEP:
            del os.environ[key]


def set_environment(site_name: str, config: Config) -> None:
    site_home = SitePaths.from_site_name(site_name).home
    os.environ["OMD_SITE"] = site_name
    os.environ["OMD_ROOT"] = site_home
    os.environ["PATH"] = (
        f"{site_home}/local/bin:{site_home}/bin:/usr/local/bin:/bin:/usr/bin:/sbin:/usr/sbin"
    )
    os.environ["USER"] = site_name
    os.environ["HOME"] = site_home

    os.environ["LD_LIBRARY_PATH"] = f"{site_home}/local/lib"

    # Special agents / active checks environment
    os.environ["PASSWORD_STORE_SECRET_FILE"] = f"{site_home}/etc/password_store.secret"
    os.environ["SERVER_SIDE_PROGRAM_STORAGE_PATH"] = (
        f"{site_home}/var/check_mk/server_side_program_storage"
    )
    os.environ["SERVER_SIDE_PROGRAM_CRASHES_PATH"] = f"{site_home}/var/check_mk/crashes"

    # allow user to define further environment variable in ~/etc/environment
    envfile = Path(site_home, "etc", "environment")
    if envfile.exists():
        lineno = 0
        with envfile.open() as opened_file:
            for line in opened_file:
                lineno += 1
                line = line.strip()
                if line == "" or line[0] == "#":
                    continue  # allow empty lines and comments
                parts = line.split("=")
                if len(parts) != 2:
                    sys.exit("%s: syntax error in line %d" % (envfile, lineno))
                varname = parts[0]
                value = parts[1]
                if value.startswith('"'):
                    value = value.strip('"')

                # Add the present environment when someone wants to append some
                if value.startswith("$%s:" % varname):
                    before = os.environ.get(varname)
                    if before:
                        value = before + ":" + value.replace("$%s:" % varname, "")

                if value.startswith("'"):
                    value = value.strip("'")
                os.environ[varname] = value

    create_config_environment(config)


def site_environment(site_name: str) -> SiteContext:
    switch_to_site_user(site_name)
    return site_environment_as_root(site_name)


def site_environment_as_root(site_name: str) -> SiteContext:
    site = SiteContext(site_name)
    config = load_config(site.name, site.hook_dir)
    # Make sure environment is in a defined state
    _clear_environment()
    set_environment(site.name, config)
    return site
