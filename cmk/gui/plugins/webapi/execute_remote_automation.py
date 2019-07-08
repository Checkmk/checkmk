#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

from typing import Dict, List  # pylint: disable=unused-import

import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.webapi import (
    APICallCollection,
    api_call_collection_registry,
)

import cmk.gui.watolib.automations


@api_call_collection_registry.register
class APICallExecuteRemoteAutomation(APICallCollection):
    def get_api_calls(self):
        return {
            "execute_remote_automation": {
                "handler": self._execute_remote_automation,
                "required_keys": ["site_id", "command", "command_args"],
                # TODO: Add a dedicated permission for this
                "required_permissions": ["wato.dcd_connections"],
            },
        }

    def _execute_remote_automation(self, request):
        if request["site_id"] not in config.sitenames():
            raise MKUserError("site_id", _("This site does not exist."))

        if request["site_id"] not in dict(config.wato_slave_sites()):
            raise MKUserError("site_id", _("This site is not a distributed WATO site."))

        return cmk.gui.watolib.automations.do_remote_automation(config.site(request["site_id"]),
                                                                request["command"],
                                                                request["command_args"])
