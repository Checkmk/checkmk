#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import time
from collections.abc import Callable
from typing import Final

from tests.testlib.utils import branch_from_env, edition_from_env, version_spec_from_env

from cmk.utils.version import Edition

logger = logging.getLogger()


# It's ok to make it currently only work on debian based distros
class CMKVersion:
    DEFAULT = "default"
    DAILY = "daily"
    GIT = "git"

    def __init__(self, version_spec: str, edition: Edition, branch: str) -> None:
        self.version_spec: Final = version_spec
        self.version: Final = self._version(version_spec, branch)
        self.edition: Final = edition
        self.branch: Final = branch

    def _get_default_version(self) -> str:
        if os.path.exists("/etc/alternatives/omd"):
            path = os.readlink("/etc/alternatives/omd")
        else:
            path = os.readlink("/omd/versions/default")
        return os.path.split(path)[-1].rsplit(".", 1)[0]

    def _version(self, version_spec: str, branch: str) -> str:
        if version_spec in (self.DAILY, self.GIT):
            date_part = time.strftime("%Y.%m.%d")
            if branch != "master":
                return f"{branch}-{date_part}"
            return date_part

        if version_spec == self.DEFAULT:
            return self._get_default_version()

        if ".cee" in version_spec or ".cre" in version_spec:
            raise Exception("Invalid version. Remove the edition suffix!")
        return version_spec

    def is_managed_edition(self) -> bool:
        return self.edition is Edition.CME

    def is_enterprise_edition(self) -> bool:
        return self.edition is Edition.CEE

    def is_raw_edition(self) -> bool:
        return self.edition is Edition.CRE

    def is_cloud_edition(self) -> bool:
        return self.edition is Edition.CCE

    def version_directory(self) -> str:
        return self.omd_version()

    def omd_version(self) -> str:
        return f"{self.version}.{self.edition.short}"

    def version_path(self) -> str:
        return "/omd/versions/%s" % self.version_directory()

    def is_installed(self) -> bool:
        return os.path.exists(self.version_path())


def version_from_env(
    *,
    fallback_version_spec: str | None = None,
    fallback_edition: Edition | None = None,
    fallback_branch: str | Callable[[], str] | None = None,
) -> CMKVersion:
    return CMKVersion(
        version_spec_from_env(fallback_version_spec),
        edition_from_env(fallback_edition),
        branch_from_env(fallback_branch),
    )
