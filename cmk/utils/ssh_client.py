#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""helper function to safely configure paramiko.SSHClient"""

from pathlib import Path

import paramiko

from cmk.utils.paths import omd_root


def _get_known_hosts_file_path() -> Path:
    return omd_root / ".ssh" / "known_hosts"


def _assure_known_hosts_file_exists() -> None:
    _get_known_hosts_file_path().parent.mkdir(parents=True, exist_ok=True)
    _get_known_hosts_file_path().touch(exist_ok=True)


def get_ssh_client() -> paramiko.SSHClient:
    """Return a configured paramiko.SSHClient instance"""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507 # BNS:f159c1

    _assure_known_hosts_file_exists()
    client.load_host_keys(str(_get_known_hosts_file_path()))
    return client
