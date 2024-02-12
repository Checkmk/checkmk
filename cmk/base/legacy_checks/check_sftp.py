#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import active_check_info


def check_sftp_arguments(params):
    args = [
        "--host=%s" % params["host"],
        "--user=%s" % params["user"],
        passwordstore_get_cmdline("--secret=%s", params["secret"]),
    ]

    if "port" in params:
        args.append("--port=%s" % params["port"])

    if "timeout" in params:
        args.append("--timeout=%s" % params["timeout"])

    if "timestamp" in params:
        args.append("--get-timestamp=%s" % params["timestamp"])

    if "put" in params:
        args.append("--put-local=%s" % params["put"]["local"])
        args.append("--put-remote=%s" % params["put"]["remote"])

    if "get" in params:
        args.append("--get-remote=%s" % params["get"]["remote"])
        args.append("--get-local=%s" % params["get"]["local"])

    if params.get("look_for_keys", False):
        args.append("--look-for-keys")

    return args


def check_sftp_desc(params):
    return params.get("description") or f"SFTP {params['host']}"


active_check_info["sftp"] = {
    "command_line": "check_sftp $ARG1$",
    "argument_function": check_sftp_arguments,
    "service_description": check_sftp_desc,
}
