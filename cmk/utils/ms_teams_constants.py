#!/usr/bin/env python3
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2022             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Checkmk.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.


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
\u00A0\n
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
\u00A0\n
$LONGHOSTOUTPUT$
"""
