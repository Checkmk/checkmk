#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="arg-type"


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import active_check_info


def check_sql_arguments(
    params: Mapping[str, Any]
) -> Sequence[str]:  # pylint: disable=too-many-branches
    args = []

    if "host" in params:
        args += ["--hostname=%s" % params["host"]]
    else:
        args += ["--hostname=$HOSTADDRESS$"]

    args.append("--dbms=%s" % params["dbms"])
    args.append("--name=%s" % params["name"])
    args.append("--user=%s" % params["user"])
    args.append(passwordstore_get_cmdline("--password=%s", params["password"]))

    if "port" in params:
        args.append("--port=%s" % params["port"])

    if "procedure" in params:
        if "procedure" in params and "useprocs" in params["procedure"]:
            args.append("--procedure")
            if "input" in params["procedure"]:
                args.append("--inputvars=%s" % params["procedure"]["input"])

    upper = _extract_levels(params, "levels")
    lower = _extract_levels(params, "levels_low")

    if "perfdata" in params:
        if (metrics := params.get("perfdata")) is not None:
            args.append(f"--metrics={metrics}")

    if "levels" in params or "levels_low" in params:
        warn_low, crit_low = lower
        warn_high, crit_high = upper
        args.append(f"-w{warn_low}:{warn_high}")
        args.append(f"-c{crit_low}:{crit_high}")

    if "text" in params:
        args.append("--text=%s" % params["text"])

    if isinstance(params["sql"], tuple):
        sql_tmp = params["sql"][-1]
    else:
        sql_tmp = params["sql"]

    args.append("%s" % sql_tmp.replace("\n", r"\n").replace(";", r"\;"))

    return args


def _extract_levels(params: Mapping[str, Any], levels_key: str) -> tuple[str, str]:
    if levels_key in params:
        extracted = params[levels_key]
        if extracted[0] == "no_levels":
            return "", ""
        if extracted[0] == "fixed":
            return extracted[1]
        raise NotImplementedError(extracted)
    return "", ""


active_check_info["sql"] = {
    "command_line": "check_sql $ARG1$",
    "argument_function": check_sql_arguments,
    "service_description": lambda args: args["description"],
}
