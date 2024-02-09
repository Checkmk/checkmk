#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import active_check_info


def check_ldap_arguments(params):
    args = []

    if "hostname" in params:
        args += ["-H", params["hostname"]]
    else:
        args += ["-H", "$HOSTADDRESS$"]

    args += ["-b", params["base_dn"]]

    if "response_time" in params:
        warn, crit = params["response_time"]
        args += ["-w", "%f" % (warn / 1000.0), "-c", "%f" % (crit / 1000.0)]

    if "timeout" in params:
        args += ["-t", params["timeout"]]

    if "attribute" in params:
        args += ["-a", params["attribute"]]

    if "authentication" in params:
        binddn, password = params["authentication"]
        args += ["-D", binddn, "-P", passwordstore_get_cmdline("%s", password)]

    if "port" in params:
        args += ["-p", params["port"]]

    if "version" in params:
        args += {
            "v2": ["-2"],
            "v3": ["-3"],
            "v3tls": ["-3", "-T"],
        }[params["version"]]

    if params.get("ssl"):
        args.append("--ssl")

    return args


def check_ldap_desc(params):
    if (name := params["name"]).startswith("^"):
        return name[1:]
    return f"LDAP {name}"


active_check_info["ldap"] = {
    "command_line": "check_ldap $ARG1$",
    "argument_function": check_ldap_arguments,
    "service_description": check_ldap_desc,
}
