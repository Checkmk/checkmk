#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="list-item"

from cmk.base.config import active_check_info


def check_tcp_arguments(params):  # pylint: disable=too-many-branches
    args = []

    args += ["-p", str(params["port"])]

    if "response_time" in params:
        warn, crit = params["response_time"]
        args += ["-w", "%f" % (warn / 1000.0)]
        args += ["-c", "%f" % (crit / 1000.0)]

    if "timeout" in params:
        args += ["-t", params["timeout"]]

    if "refuse_state" in params:
        args += ["-r", params["refuse_state"]]

    if params.get("escape_send_string"):
        args.append("--escape")

    if "send_string" in params:
        args += ["-s", params["send_string"]]

    if "expect" in params:
        for s in params["expect"]:
            args += ["-e", s]

    if params.get("expect_all"):
        args.append("-A")

    if params.get("jail"):
        args.append("--jail")

    if "mismatch_state" in params:
        args += ["-M", params["mismatch_state"]]

    if "delay" in params:
        args += ["-d", params["delay"]]

    if "maxbytes" in params:
        args += ["-m", params["maxbytes"]]

    if params.get("ssl"):
        args.append("--ssl")

    if "cert_days" in params:
        # legacy behavior
        if isinstance(params["cert_days"], int):
            args += ["-D", params["cert_days"]]
        else:
            warn, crit = params["cert_days"]
            args += ["-D", "%d,%d" % (warn, crit)]

    if "quit_string" in params:
        args += ["-q", params["quit_string"]]

    if "hostname" in params:
        args += ["-H", params["hostname"]]
    else:
        args += ["-H", "$HOSTADDRESS$"]

    return args


active_check_info["tcp"] = {
    "command_line": "check_tcp $ARG1$",
    "argument_function": check_tcp_arguments,
    "service_description": lambda args: args.get("svc_description", "TCP Port %d" % args["port"]),
}
