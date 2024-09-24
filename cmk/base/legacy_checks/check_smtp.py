#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.hostaddress import HostName  # pylint: disable=cmk-module-layer-violation

from cmk.base.check_api import host_name, is_ipv6_primary, passwordstore_get_cmdline
from cmk.base.config import active_check_info


def check_smtp_arguments(params):  # pylint: disable=too-many-branches
    args = []

    if "expect" in params:
        args += ["-e", params["expect"]]

    if "port" in params:
        args += ["-p", params["port"]]

    # Use the address family of the monitored host by default
    address_family = params.get("address_family")
    if address_family is None:
        address_family = "ipv6" if is_ipv6_primary(HostName(host_name())) else "ipv4"

    if address_family == "ipv6":
        args.append("-6")
        address = "$_HOSTADDRESS_6$"
    else:
        args.append("-4")
        address = "$_HOSTADDRESS_4$"

    for s in params.get("commands", []):
        args += ["-C", s]

    for s in params.get("command_responses", []):
        args += ["-R", s]

    if params.get("from_address"):
        args += ["-f", params["from_address"]]

    if "response_time" in params:
        warn, crit = params["response_time"]
        args += ["-w", "%0.4f" % warn]
        args += ["-c", "%0.4f" % crit]

    if "timeout" in params:
        args += ["-t", params["timeout"]]

    if "auth" in params:
        username, password = params["auth"]
        args += [
            "-A",
            "LOGIN",
            "-U",
            username,
            "-P",
            passwordstore_get_cmdline("%s", password),
        ]

    if params.get("starttls", False):
        args.append("-S")

    if "fqdn" in params:
        args += ["-F", params["fqdn"]]

    if "cert_days" in params:
        warn, crit = params["cert_days"]
        args += ["-D", "%d,%d" % (warn, crit)]

    if "hostname" in params:
        args += ["-H", params["hostname"]]
    else:
        args += ["-H", address]

    return args


def check_smtp_desc(params):
    if (name := params["name"]).startswith("^"):
        return name[1:]
    return f"SMTP {name}"


active_check_info["smtp"] = {
    "command_line": "check_smtp $ARG1$",
    "argument_function": check_smtp_arguments,
    "service_description": check_smtp_desc,
}
