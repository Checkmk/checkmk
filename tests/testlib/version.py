#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import time
from typing import Final

from cmk.utils.version import Edition

logger = logging.getLogger()


# It's ok to make it currently only work on debian based distros
class CMKVersion:
    DEFAULT = "default"
    DAILY = "daily"
    GIT = "git"

    def __init__(self, version_spec: str, edition: Edition, branch: str) -> None:
        self.version_spec = version_spec
        self._branch = branch

        self.edition: Final = edition
        self.set_version(version_spec, branch)

    def get_default_version(self) -> str:
        if os.path.exists("/etc/alternatives/omd"):
            path = os.readlink("/etc/alternatives/omd")
        else:
            path = os.readlink("/omd/versions/default")
        return os.path.split(path)[-1].rsplit(".", 1)[0]

    def set_version(self, version: str, branch: str) -> None:
        if version in [CMKVersion.DAILY, CMKVersion.GIT]:
            date_part = time.strftime("%Y.%m.%d")
            if branch != "master":
                self.version = f"{branch}-{date_part}"
            else:
                self.version = date_part

        elif version == CMKVersion.DEFAULT:
            self.version = self.get_default_version()

        else:
            if ".cee" in version or ".cre" in version:
                raise Exception("Invalid version. Remove the edition suffix!")
            self.version = version

    def branch(self) -> str:
        return self._branch

    def is_managed_edition(self) -> bool:
        return self.edition is Edition.CME

    def is_enterprise_edition(self) -> bool:
        return self.edition is Edition.CEE

    def is_raw_edition(self) -> bool:
        return self.edition is Edition.CRE

    def is_plus_edition(self) -> bool:
        return self.edition is Edition.CPE

    def version_directory(self) -> str:
        return self.omd_version()

    def omd_version(self) -> str:
        return f"{self.version}.{self.edition.short}"

    def version_path(self) -> str:
        return "/omd/versions/%s" % self.version_directory()

    def is_installed(self) -> bool:
        return os.path.exists(self.version_path())
