#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# .------------------------------------------------------------------------.
# |                ____ _               _        __  __ _  __              |
# |               / ___| |__   ___  ___| | __   |  \/  | |/ /              |
# |              | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /               |
# |              | |___| | | |  __/ (__|   <    | |  | | . \               |
# |               \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\              |
# |                                        |_____|                         |
# |             _____       _                       _                      |
# |            | ____|_ __ | |_ ___ _ __ _ __  _ __(_)___  ___             |
# |            |  _| | '_ \| __/ _ \ '__| '_ \| '__| / __|/ _ \            |
# |            | |___| | | | ||  __/ |  | |_) | |  | \__ \  __/            |
# |            |_____|_| |_|\__\___|_|  | .__/|_|  |_|___/\___|            |
# |                                     |_|                                |
# |                     _____    _ _ _   _                                 |
# |                    | ____|__| (_) |_(_) ___  _ __                      |
# |                    |  _| / _` | | __| |/ _ \| '_ \                     |
# |                    | |__| (_| | | |_| | (_) | | | |                    |
# |                    |_____\__,_|_|\__|_|\___/|_| |_|                    |
# |                                                                        |
# | mathias-kettner.com                                 mathias-kettner.de |
# '------------------------------------------------------------------------'
#  This file is part of the Check_MK Enterprise Edition (CEE).
#  Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
#  Distributed under the Check_MK Enterprise License.
#
#  You should have  received  a copy of the Check_MK Enterprise License
#  along with Check_MK. If not, email to mk@mathias-kettner.de
#  or write to the postal address provided at www.mathias-kettner.de


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
            ("runas", TextAscii(
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
            ("command", TextAscii(
                title = _("Command to execute"),
                allow_empty = False,
            )),
        ],
        optional_keys = False,
    )
)
