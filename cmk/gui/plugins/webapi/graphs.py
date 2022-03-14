#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.metrics.graph_images import graph_spec_from_request
from cmk.gui.plugins.webapi.utils import api_call_collection_registry, APICallCollection

# Request:
# {
#     "specification": ["template", {...}],
#     "data_range": {
#         "time_range" : [..., ...],
#     }
# }

# curl "http://127.0.0.1/heute/check_mk/webapi.py?action=get_graph&_username=automation&_secret=af665c15-5728-4541-b5bf-04d1d98deee8" -d 'request={"specification": ["template", {"service_description": "Check_MK", "site": "heute", "graph_index": 0, "host_name": "heute" }], "data_range": {"time_range": [1480653120, 1480667520]}}'

# curl "http://127.0.0.1/heute/check_mk/webapi.py?action=get_graph&_username=automation&_secret=af665c15-5728-4541-b5bf-04d1d98deee8" -d 'request={"specification": ["custom", "custom_graph_1"], "data_range": {"time_range": [1480653120, 1480667520]}}'


@api_call_collection_registry.register
class APICallGraph(APICallCollection):
    def get_api_calls(self):
        return {
            "get_graph": {
                "handler": self._get_graph,
                "optional_keys": ["specification", "data_range", "consolidation_function"],
                "locking": False,
            },
        }

    def _get_graph(self, request):
        return graph_spec_from_request(request)
