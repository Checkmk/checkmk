#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def ms_teams_tmpl_svc_title() -> str:
    return "Checkmk: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$"


def ms_teams_tmpl_svc_summary() -> str:
    return "Checkmk: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$"


def ms_teams_tmpl_svc_details() -> str:
    return """__Host__: $HOSTNAME$\n
__Service__:  $SERVICEDESC$\n
__Event__:    $EVENT_TXT$\n
__Output__:   $SERVICEOUTPUT$\n
__Perfdata__: $SERVICEPERFDATA$\n
\n
$LONGSERVICEOUTPUT$
"""


def ms_teams_tmpl_host_title() -> str:
    return "Checkmk: $HOSTNAME$ - $HOSTSHORTSTATE$"


def ms_teams_tmpl_host_summary() -> str:
    return "Checkmk: $HOSTNAME$ - $EVENT_TXT$"


def ms_teams_tmpl_host_details() -> str:
    return """__Host__: $HOSTNAME$\n
__Event__:    $EVENT_TXT$\n
__Output__:   $HOSTOUTPUT$\n
__Perfdata__: $HOSTPERFDATA$\n
\n
$LONGHOSTOUTPUT$
"""
