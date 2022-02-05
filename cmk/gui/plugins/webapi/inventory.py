#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.inventory import inventory_of_host
from cmk.gui.plugins.webapi.utils import api_call_collection_registry, APICallCollection


@api_call_collection_registry.register
class APICallInventory(APICallCollection):
    def get_api_calls(self):
        return {
            "get_inventory": {
                "handler": self._get_inventory,
                "required_keys": ["hosts"],
                "optional_keys": ["site", "paths"],
                "locking": False,
            }
        }

    def _get_inventory(self, request):
        return {
            host_name: inventory_of_host(host_name, request)  #
            for host_name in request.get("hosts")
        }
