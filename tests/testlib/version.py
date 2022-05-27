#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import time

logger = logging.getLogger()


# It's ok to make it currently only work on debian based distros
class CMKVersion:
    DEFAULT = "default"
    DAILY = "daily"
    GIT = "git"

    CEE = "cee"
    CRE = "cre"
    CPE = "cpe"
    CME = "cme"

    def __init__(self, version_spec, edition, branch):
        self.version_spec = version_spec
        self._branch = branch

        self._set_edition(edition)
        self.set_version(version_spec, branch)

    def _set_edition(self, edition):
        # Allow short (cre) and long (raw) notation as input
        if edition not in [CMKVersion.CRE, CMKVersion.CEE, CMKVersion.CME, CMKVersion.CPE]:
            edition_short = self._get_short_edition(edition)
        else:
            edition_short = edition

        if edition_short not in [CMKVersion.CRE, CMKVersion.CEE, CMKVersion.CME, CMKVersion.CPE]:
            raise NotImplementedError("Unknown short edition: %s" % edition_short)

        self.edition_short = edition_short

    def _get_short_edition(self, edition):
        if edition == "raw":
            return "cre"
        if edition == "enterprise":
            return "cee"
        if edition == "managed":
            return "cme"
        if edition == "plus":
            return "cpe"
        raise NotImplementedError("Unknown edition: %s" % edition)

    def get_default_version(self):
        if os.path.exists("/etc/alternatives/omd"):
            path = os.readlink("/etc/alternatives/omd")
        else:
            path = os.readlink("/omd/versions/default")
        return os.path.split(path)[-1].rsplit(".", 1)[0]

    def set_version(self, version, branch):
        if version in [CMKVersion.DAILY, CMKVersion.GIT]:
            date_part = time.strftime("%Y.%m.%d")
            if branch != "master":
                self.version = "%s-%s" % (branch, date_part)
            else:
                self.version = date_part

        elif version == CMKVersion.DEFAULT:
            self.version = self.get_default_version()

        else:
            if ".cee" in version or ".cre" in version:
                raise Exception("Invalid version. Remove the edition suffix!")
            self.version = version

    def branch(self):
        return self._branch

    def edition(self):
        if self.edition_short == CMKVersion.CRE:
            return "raw"
        if self.edition_short == CMKVersion.CEE:
            return "enterprise"
        if self.edition_short == CMKVersion.CME:
            return "managed"
        if self.edition_short == CMKVersion.CPE:
            return "plus"
        raise NotImplementedError()

    def is_managed_edition(self):
        return self.edition_short == CMKVersion.CME

    def is_enterprise_edition(self):
        return self.edition_short == CMKVersion.CEE

    def is_raw_edition(self):
        return self.edition_short == CMKVersion.CRE

    def version_directory(self):
        return self.omd_version()

    def omd_version(self):
        return "%s.%s" % (self.version, self.edition_short)

    def version_path(self):
        return "/omd/versions/%s" % self.version_directory()

    def is_installed(self):
        return os.path.exists(self.version_path())
