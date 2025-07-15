#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from cmk.ccc.hostaddress import HostName

from cmk.gui.config import Config
from cmk.gui.type_defs import Choices
from cmk.gui.utils.regex import validate_regex
from cmk.gui.valuespec import AjaxDropdownChoice

from .hosts_and_folders import Host


class ConfigHostname(AjaxDropdownChoice):
    """Hostname input with dropdown completion

    Renders an input field for entering a host name while providing an auto completion dropdown field.
    Fetching the choices from the current Setup config"""

    ident = "config_hostname"


def config_hostname_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """
    all_hosts: dict[HostName, Host] = Host.all()
    validate_regex(value, varname=None)
    match_pattern = re.compile(value, re.IGNORECASE)
    match_list: Choices = []
    for host_name, host_object in all_hosts.items():
        if match_pattern.search(host_name) is not None and host_object.permissions.may("read"):
            match_list.append((host_name, host_name))

    if not any(x[0] == value for x in match_list):
        match_list.insert(0, (value, value))  # User is allowed to enter anything they want

    return match_list
