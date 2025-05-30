#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
from pathlib import Path

from omdlib.init_scripts import check_status
from omdlib.site_paths import SitePaths
from omdlib.skel_permissions import (
    load_skel_permissions_from,
    Permissions,
    skel_permissions_file_path,
)
from omdlib.type_defs import Config, Replacements
from omdlib.version import version_from_site_dir

from cmk.ccc.exceptions import MKTerminate
from cmk.ccc.version import Edition


class SiteContext:
    def __init__(self, sitename: str) -> None:
        self._config_loaded = False
        self._config: Config = {}
        self._sitename = sitename
        self._paths = SitePaths.from_site_name(sitename)

    @property
    def conf(self) -> Config:
        """{ "CORE" : "nagios", ... } (contents of etc/omd/site.conf plus defaults from hooks)"""
        if not self._config_loaded:
            raise Exception("Config not loaded yet")
        return self._config

    @property
    def name(self) -> str:
        return self._sitename

    @property
    def tmp_dir(self) -> str:
        return "%s/tmp" % self._paths.home

    @property
    def real_dir(self) -> str:
        return "/opt/" + self._paths.home.lstrip("/")

    @property
    def real_tmp_dir(self) -> str:
        return "%s/tmp" % self.real_dir

    @property
    def hook_dir(self) -> str | None:
        if version_from_site_dir(Path(self._paths.home)) is None:
            return None
        return "/omd/versions/%s/lib/omd/hooks/" % version_from_site_dir(Path(self._paths.home))

    def replacements(self) -> Replacements:
        """Dictionary of key/value for replacing macros in skel files"""
        version = version_from_site_dir(Path(self._paths.home))
        if version is None:
            raise RuntimeError("Failed to determine site version")
        return {
            "###SITE###": self.name,
            "###ROOT###": self._paths.home,
            "###EDITION###": Edition[version.split(".")[-1].upper()].long,
        }

    def set_config(self, config: Config) -> None:
        self._config = config
        self._config_loaded = True

    def is_empty(self) -> bool:
        for entry in os.listdir(self._paths.home):
            if entry not in [".", ".."]:
                return False
        return True

    def is_stopped(self, verbose: bool) -> bool:
        """Check if site is completely stopped"""
        return check_status(self._paths.home, verbose, display=False) == 1

    @property
    def skel_permissions(self) -> Permissions:
        """Returns the skeleton permissions. Load either from version meta directory
        or from the original version skel.permissions file"""
        if not self._has_version_meta_data():
            version = version_from_site_dir(Path(self._paths.home))
            if version is None:
                raise MKTerminate("Failed to determine site version")
            return load_skel_permissions_from(skel_permissions_file_path(version))

        return load_skel_permissions_from(self.version_meta_dir + "/skel.permissions")

    @property
    def version_meta_dir(self) -> str:
        return f"{self._paths.home}/.version_meta"

    @property
    def version_skel_dir(self) -> str:
        """Returns the current version skel directory. In case the meta data is
        available and fits the sites version use that one instead of the version
        skel directory."""
        if not self._has_version_meta_data():
            return "/omd/versions/%s/skel" % version_from_site_dir(Path(self._paths.home))
        return self.version_meta_dir + "/skel"

    def _has_version_meta_data(self) -> bool:
        if not os.path.exists(self.version_meta_dir):
            return False

        if self._version_meta_data_version() != version_from_site_dir(Path(self._paths.home)):
            return False

        return True

    def _version_meta_data_version(self) -> str:
        with open(self.version_meta_dir + "/version") as f:
            return f.read().strip()


class RootContext:
    pass
