#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""HTTP setup shared by the legacy and the v4 Prism agent"""

import ipaddress

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from cmk.server_side_programs.v1 import HostnameValidationAdapter

USER_AGENT = "Checkmk special agent Nutanix Prism"


def base_url(server: str, port: int) -> str:
    try:
        is_ipv6 = ipaddress.ip_address(server).version == 6
    except ValueError:
        is_ipv6 = False
    return f"https://[{server}]:{port}" if is_ipv6 else f"https://{server}:{port}"


def new_session(url: str, cert_check: bool | str, retry: Retry | None = None) -> requests.Session:
    """A session for one Prism server

    The caller must still pass `verify=cert_check is not False` with every request, otherwise
    REQUESTS_CA_BUNDLE from the site environment overrides it.
    """
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    adapter = (
        HostnameValidationAdapter(cert_check) if isinstance(cert_check, str) else HTTPAdapter()
    )
    if retry is not None:
        adapter.max_retries = retry
    session.mount(url, adapter)
    return session
