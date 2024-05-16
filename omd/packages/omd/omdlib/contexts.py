#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import os
import sys
from pathlib import Path
from typing import cast

from omdlib.init_scripts import check_status
from omdlib.skel_permissions import (
    load_skel_permissions_from,
    Permissions,
    skel_permissions_file_path,
)
from omdlib.type_defs import Config, Replacements
from omdlib.version import version_from_site_dir

from cmk.utils.exceptions import MKTerminate
from cmk.utils.version import Edition


class AbstractSiteContext(abc.ABC):
    """Object wrapping site specific information"""

    def __init__(self, sitename: str | None) -> None:
        super().__init__()
        self._sitename = sitename
        self._config_loaded = False
        self._config: Config = {}

    @property
    def name(self) -> str | None:
        return self._sitename

    @property
    @abc.abstractmethod
    def dir(self) -> str:
        raise NotImplementedError()

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
    def version_meta_dir(self) -> str:
        return "%s/.version_meta" % self.dir

    @property
    def conf(self) -> Config:
        """{ "CORE" : "nagios", ... } (contents of etc/omd/site.conf plus defaults from hooks)"""
        if not self._config_loaded:
            raise Exception("Config not loaded yet")
        return self._config

    @abc.abstractmethod
    def load_config(self, defaults: dict[str, str]) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def is_empty(self) -> bool:
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def is_site_context() -> bool:
        raise NotImplementedError()


class SiteContext(AbstractSiteContext):
    @property
    def name(self) -> str:
        return cast(str, self._sitename)

    @property
    def dir(self) -> str:
        return os.path.join("/omd/sites", cast(str, self._sitename))

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

    def load_config(self, defaults: dict[str, str]) -> None:
        """Load all variables from omd/sites.conf. These variables always begin with
        CONFIG_. The reason is that this file can be sources with the shell.

        Puts these variables into the config dict without the CONFIG_. Also
        puts the variables into the process environment."""
        self._config = {**defaults, **self.read_site_config()}
        self._config_loaded = True

    def read_site_config(self) -> Config:
        """Read and parse the file site.conf of a site into a dictionary and returns it"""
        config: Config = {}
        if not (confpath := Path(self.dir, "etc/omd/site.conf")).exists():
            return {}

        with confpath.open() as conf_file:
            for line in conf_file:
                line = line.strip()
                if line == "" or line[0] == "#":
                    continue
                var, value = line.split("=", 1)
                if not var.startswith("CONFIG_"):
                    sys.stderr.write("Ignoring invalid variable %s.\n" % var)
                else:
                    config[var[7:].strip()] = value.strip().strip("'")

        return config

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

    @staticmethod
    def is_site_context() -> bool:
        return True

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
    def __init__(self) -> None:
        super().__init__(sitename=None)

    @property
    def dir(self) -> str:
        """Absolute base path (without trailing slash)"""
        return "/"

    @property
    def tmp_dir(self) -> str:
        return "/tmp"  # nosec B108 # BNS:13b2c8

    @property
    def real_dir(self) -> str:
        """Absolute base path (without trailing slash)"""
        return "/" + self.dir.lstrip("/")

    @property
    def real_tmp_dir(self) -> str:
        return "%s/tmp" % self.real_dir

    def load_config(self, defaults: dict[str, str]) -> None:
        pass

    def is_empty(self) -> bool:
        return False

    @staticmethod
    def is_site_context() -> bool:
        return False
