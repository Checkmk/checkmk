#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2016-04-16

# 2023-01-14: fixed missing import for declare_invtable_view
# 2023-06-14: removed declare_invtable_view from view definition on cmk 2.2 (see werk 15493)
#             changed inventory_displayhints import (see werk 15493)
# 2023-11-17: moved file back from local/lib/ structure to local/share/ structure to avoid errors in web.log
# 2023-12-21: streamlined LLDP and CDP view
# 2024-04-08: fixed wrong path in inventory_displayhints (missing neighbours)
#             changed "Cache Capabilities" to "Capabilities" and
#             "Capabilities map supported" to "Capabilities supported"
#             capitalized colum names

from cmk.gui.i18n import _
from cmk.gui.views.inventory.registry import inventory_displayhints

inventory_displayhints.update({
    '.networking.lldp_cache.': {
        'title': _('LLDP cache'),
        'keyorder': [
            'local_name',
            'local_id',
            'local_description',
            'local_cap_supported',
            'local_cap_enabled',
        ],
    },
    '.networking.lldp_cache.local_cap_supported': {'title': _('Capabilities supported'), },
    '.networking.lldp_cache.local_cap_enabled': {'title': _('Capabilities enabled'), },
    '.networking.lldp_cache.neighbours:': {
        'title': _('LLDP Neighbours'),
        'keyorder': [
            'neighbour_name',
            'neighbour_port',
            'local_port',
            'neighbour_address',
            'neighbour_id',
        ],
        'view': 'invlldpcache',
    },
    '.networking.lldp_cache.neighbours:*.capabilities': {'title': _('Capabilities'), },
    '.networking.lldp_cache.neighbours:*.capabilities_map_supported': {'title': _('Capabilities Supported'), },
    '.networking.lldp_cache.neighbours:*.local_port': {'title': _('Local Port'), },
    '.networking.lldp_cache.neighbours:*.neighbour_address': {'title': _('Neighbour Address'), },
    '.networking.lldp_cache.neighbours:*.neighbour_id': {'title': _('Neighbour ID'), },
    '.networking.lldp_cache.neighbours:*.neighbour_name': {'title': _('Neighbour Name'), },
    '.networking.lldp_cache.neighbours:*.neighbour_port': {'title': _('Neighbour Port'), },
    '.networking.lldp_cache.neighbours:*.port_description': {'title': _('Neighbour Port Description'), },
    '.networking.lldp_cache.neighbours:*.system_description': {'title': _('Neighbour Description'), },
})
