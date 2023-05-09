#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

        if request["site_id"] not in config.wato_slave_sites():
            raise MKUserError("site_id", _("This site is not a distributed WATO site."))

        return cmk.gui.watolib.automations.do_remote_automation(config.site(request["site_id"]),
                                                                request["command"],
                                                                request["command_args"])
