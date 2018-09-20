# -*- coding: utf-8 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
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

from typing import Dict  # pylint: disable=unused-import
import os
import re


def collect_context():
    # type: () -> Dict
    return {
        var[7:]: value.decode("utf-8")
        for (var, value) in os.environ.items()
        if var.startswith("NOTIFY_")
    }


def extend_context_with_link_urls(context, link_template):
    # type: (Dict, str) -> None
    if context.get("PARAMETER_URL_PREFIX"):
        url_prefix = context["PARAMETER_URL_PREFIX"]
    elif context.get("PARAMETER_URL_PREFIX_MANUAL"):
        url_prefix = context["PARAMETER_URL_PREFIX_MANUAL"]
    elif context.get("PARAMETER_URL_PREFIX_AUTOMATIC") == "http":
        url_prefix = "http://%s/%s" % (context["MONITORING_HOST"], context["OMD_SITE"])
    elif context.get("PARAMETER_URL_PREFIX_AUTOMATIC") == "https":
        url_prefix = "https://%s/%s" % (context["MONITORING_HOST"], context["OMD_SITE"])
    else:
        url_prefix = None

    if url_prefix:
        base_url = re.sub('/check_mk/?', '', url_prefix)
        host_url = base_url + context['HOSTURL']

        context['LINKEDHOSTNAME'] = link_template % (host_url, context['HOSTNAME'])

        if context['WHAT'] == 'SERVICE':
            service_url = base_url + context['SERVICEURL']
            context['LINKEDSERVICEDESC'] = link_template % (service_url, context['SERVICEDESC'])

    else:
        context['LINKEDHOSTNAME'] = context['HOSTNAME']
        context['LINKEDSERVICEDESC'] = context.get('SERVICEDESC', '')
