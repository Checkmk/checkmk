#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import os
from pathlib import Path
from typing import override

from omdlib.init_scripts import check_status
from omdlib.skel_permissions import (
    load_skel_permissions_from,
    Permissions,
    skel_permissions_file_path,
)
from omdlib.type_defs import Config, Replacements
from omdlib.version import version_from_site_dir

from cmk.ccc.exceptions import MKTerminate
from cmk.ccc.version import Edition


class AbstractSiteContext(abc.ABC):
    """Object wrapping site specific information"""

    def __init__(self) -> None:
        super().__init__()
        self._config_loaded = False
        self._config: Config = {}

    @property
    @abc.abstractmethod
    def tmp_dir(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def real_dir(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def real_tmp_dir(self) -> str:
        raise NotImplementedError()

    @property
    def conf(self) -> Config:
        """{ "CORE" : "nagios", ... } (contents of etc/omd/site.conf plus defaults from hooks)"""
        if not self._config_loaded:
            raise Exception("Config not loaded yet")
        return self._config

    @abc.abstractmethod
    def set_config(self, config: Config) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def is_empty(self) -> bool:
        raise NotImplementedError()


class SiteContext(AbstractSiteContext):
    def __init__(self, sitename: str) -> None:
        super().__init__()
        self._sitename = sitename

    @property
    def name(self) -> str:
        return self._sitename

    @property
    def dir(self) -> str:
        return os.path.join("/omd/sites", self._sitename)

    @property
    def tmp_dir(self) -> str:
        return "%s/tmp" % self.dir

    @property
    def real_dir(self) -> str:
        return "/opt/" + self.dir.lstrip("/")

    @property
    def real_tmp_dir(self) -> str:
        return "%s/tmp" % self.real_dir

    @property
    def hook_dir(self) -> str | None:
        if version_from_site_dir(Path(self.dir)) is None:
            return None
        return "/omd/versions/%s/lib/omd/hooks/" % version_from_site_dir(Path(self.dir))

    def replacements(self) -> Replacements:
        """Dictionary of key/value for replacing macros in skel files"""
        version = version_from_site_dir(Path(self.dir))
        if version is None:
            raise RuntimeError("Failed to determine site version")
        return {
            "###SITE###": self.name,
            "###ROOT###": self.dir,
            "###EDITION###": Edition[version.split(".")[-1].upper()].long,
        }

    @override
    def set_config(self, config: Config) -> None:
        self._config = config
        self._config_loaded = True

    @override
    def is_empty(self) -> bool:
        for entry in os.listdir(self.dir):
            if entry not in [".", ".."]:
                return False
        return True

    def is_autostart(self) -> bool:
        """Determines whether a specific site is set to autostart."""
        return self.conf.get("AUTOSTART", "on") == "on"

    def is_stopped(self) -> bool:
        """Check if site is completely stopped"""
        return check_status(self.dir, display=False) == 1

    @property
    def skel_permissions(self) -> Permissions:
        """Returns the skeleton permissions. Load either from version meta directory
        or from the original version skel.permissions file"""
        if not self._has_version_meta_data():
            version = version_from_site_dir(Path(self.dir))
            if version is None:
                raise MKTerminate("Failed to determine site version")
            return load_skel_permissions_from(skel_permissions_file_path(version))

        return load_skel_permissions_from(self.version_meta_dir + "/skel.permissions")

    @property
    def version_meta_dir(self) -> str:
        return "%s/.version_meta" % self.dir

    @property
    def version_skel_dir(self) -> str:
        """Returns the current version skel directory. In case the meta data is
        available and fits the sites version use that one instead of the version
        skel directory."""
        if not self._has_version_meta_data():
            return "/omd/versions/%s/skel" % version_from_site_dir(Path(self.dir))
        return self.version_meta_dir + "/skel"

    def _has_version_meta_data(self) -> bool:
        if not os.path.exists(self.version_meta_dir):
            return False

        if self._version_meta_data_version() != version_from_site_dir(Path(self.dir)):
            return False

        return True

    def _version_meta_data_version(self) -> str:
        with open(self.version_meta_dir + "/version") as f:
            return f.read().strip()


class RootContext(AbstractSiteContext):
    @property
    @override
    def tmp_dir(self) -> str:
        return "/tmp"  # nosec B108 # BNS:13b2c8

    @property
    @override
    def real_dir(self) -> str:
        """Absolute base path (without trailing slash)"""
        return "/"

    @property
    @override
    def real_tmp_dir(self) -> str:
        return "%s/tmp" % self.real_dir

    @override
    def set_config(self, config: Config) -> None:
        pass

    @override
    def is_empty(self) -> bool:
        return False
