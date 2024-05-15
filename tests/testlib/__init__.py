#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import urllib3

from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import (
    current_branch_name,
    get_cmk_download_credentials,
    repo_path,
    site_id,
    virtualenv_path,
)
from tests.testlib.version import CMKVersion  # noqa: F401 # pylint: disable=unused-import
from tests.testlib.web_session import APIError, CMKWebSession

# Disable insecure requests warning message during SSL testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


__all__ = [
    "repo_path",
    "Site",
    "SiteFactory",
    "APIError",
    "CMKWebSession",
    "current_branch_name",
    "get_cmk_download_credentials",
    "site_id",
    "virtualenv_path",
]
