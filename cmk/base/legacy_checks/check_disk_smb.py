#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import active_check_info


def check_disk_smb_arguments(params):
    args = [
        params["share"],
        "-H",
        "$HOSTADDRESS$" if params["host"] == "use_parent_host" else params["host"][1],
    ]

    warn, crit = params["levels"]
    args += ["--levels", warn, crit]

    if "workgroup" in params:
        args += ["-W", params["workgroup"]]

    if "port" in params:
        args += ["-P", params["port"]]

    if "auth" in params:
        username, password = params["auth"]
        args += [
            "-u",
            username,
            "-p",
            passwordstore_get_cmdline("%s", password),
        ]

    if "ip_address" in params:
        args += ["-a", params["ip_address"]]

    return args


active_check_info["disk_smb"] = {
    "command_line": "check_disk_smb $ARG1$",
    "argument_function": check_disk_smb_arguments,
    "service_description": lambda params: "SMB Share " + params["share"].replace("$", ""),
}
