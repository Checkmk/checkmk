#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This is the command line generator for the `check_mailboxes` active check.
It defines active_check_info["mailboxes"]

"""

CHECK_IDENT = "check_mailboxes"

from cmk.base.check_legacy_includes.check_mail import general_check_mail_args_from_params
from cmk.base.config import active_check_info


def check_mailboxes_arguments(params):
    """
    >>> for l in check_mailboxes_arguments({  # v2.1.0 / EWS
    ...     'service_description': 'SD',
    ...     'fetch': ('EWS', {
    ...       'server': 'srv', 'connection': {},
    ...       'auth': ('basic', ('usr', 'pw')),
    ...       'email_address': 'usr@srv.com',
    ...       'connection': {'disable_tls': True, 'disable_cert_validation': False, 'port': 123}}),
    ...     'age': (1, 2), 'age_newest': (3, 4), 'count': (5, 6),
    ...     'mailboxes': ['abc', 'def']}):
    ...   print(l)
    --fetch-protocol=EWS
    --fetch-server=srv
    --fetch-port=123
    --fetch-username=usr
    --fetch-password=pw
    --fetch-email-address=usr@srv.com
    --warn-age-oldest=1
    --crit-age-oldest=2
    --warn-age-newest=3
    --crit-age-newest=4
    --warn-count=5
    --crit-count=6
    --mailbox=abc
    --mailbox=def
    """
    args: list[str | tuple[str, str, str]] = general_check_mail_args_from_params(
        CHECK_IDENT, params
    )

    if "retrieve_max" in params:
        args.append(f"--retrieve-max={params['retrieve_max']}")

    if "age" in params:
        warn, crit = params["age"]
        args += [f"--warn-age-oldest={warn}", f"--crit-age-oldest={crit}"]

    if "age_newest" in params:
        warn, crit = params["age_newest"]
        args += [f"--warn-age-newest={warn}", f"--crit-age-newest={crit}"]

    if "count" in params:
        warn, crit = params["count"]
        args += [f"--warn-count={warn}", f"--crit-count={crit}"]

    for mb in params.get("mailboxes", []):
        args.append(f"--mailbox={mb}")

    return args


active_check_info["mailboxes"] = {  # pylint: disable=undefined-variable
    "command_line": f"{CHECK_IDENT} $ARG1$",
    "argument_function": check_mailboxes_arguments,
    "service_description": lambda params: params["service_description"],
}
