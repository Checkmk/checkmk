#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from cmk.gui.valuespec import (
    Dictionary,
    TextInput,
)
from cmk.gui.plugins.wato.utils import PasswordFromStore

from cmk.gui.cee.plugins.wato.alert_handling import register_alert_handler_parameters

register_alert_handler_parameters(
    "windows_remote",
    Dictionary(
        title = _("Remote execution on Windows via WMI"),
        help = _("This alert handler allows the remote execution of scripts and programs "
                 "on Windows systems via WMI. Please note that this configuration is saved "
                 "in clear text (including the password!). We have not made any influence on "
                 "the security settings of the target Window hosts. If you don't secure the "
                 "WMI access, the credentials might be used to execute arbitrary commands on "
                 "the remote system. Use with caution!"),
        elements = [
            ("runas", TextInput(
                  title = _("User to run handler as"),
                  allow_empty = False,
                  regex = re.compile('^[a-zA-Z_][-/a-zA-Z0-9_\\\\]*$'),
                  regex_error = _("Your input does not match the required format.") \
                              + " " + _("Expected syntax: [domain/]username")
            )),
            ("password", PasswordFromStore(
                  title = _("Password of the user"),
                  allow_empty = False,
            )),
            ("command", TextInput(
                title = _("Command to execute"),
                allow_empty = False,
            )),
        ],
        optional_keys = False,
    )
)
