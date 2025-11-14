#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2016-04-08
# File  : cmk/gui/plugins/views/inv_cdp_cache.py

# 2023-02-17: moved from ~/local/share/check_mk/web/plugins/views -> ~7local/lib/check_mk/gui/plugins/views
# 2023-06-14: removed declare_invtable_view from view definition on cmk 2.2 (see werk 15493)
#             changed inventory_displayhints import (see werk 15493)
# 2023-11-17: moved file back from local/lib/ structure to local/share/ structure to avoid errors in web.log
# 2023-12-21: streamlined LLDP and CDP view
# 2024-04-08: fixed typo in "Capabilities"
#             capitalized colum names

from cmk.gui.i18n import _
from cmk.gui.views.inventory.registry import inventory_displayhints

inventory_displayhints.update({
    '.networking.cdp_cache.': {
        'title': _('CDP cache'),
        'keyorder': ['enabled', 'local_name', 'message_interval', 'hold_time'],
    },
    '.networking.cdp_cache.neighbours:': {
        'title': _('CDP Neighbours'),
        'keyorder': [
            'neighbour_name',
            'neighbour_port',
            'local_port',
            'neighbour_address',
            'neighbour_id',
        ],
        'view': 'invcdpcache',
        },
    '.networking.cdp_cache.neighbours:*.capabilities': {'title': _('Capabilities'), },
    '.networking.cdp_cache.neighbours:*.duplex': {'title': _('Duplex'), },
    '.networking.cdp_cache.neighbours:*.local_port': {'title': _('Local Port'), },
    '.networking.cdp_cache.neighbours:*.native_vlan': {'title': _('Native VLAN'), },
    '.networking.cdp_cache.neighbours:*.neighbour_address': {'title': _('Neighbour Address'), },
    '.networking.cdp_cache.neighbours:*.neighbour_id': {'title': _('Neighbour ID'), },
    '.networking.cdp_cache.neighbours:*.neighbour_name': {'title': _('Neighbour Name'), },
    '.networking.cdp_cache.neighbours:*.neighbour_port': {'title': _('Neighbour Port'), },
    '.networking.cdp_cache.neighbours:*.platform': {'title': _('Neighbour Platform'), },
    '.networking.cdp_cache.neighbours:*.platform_details': {'title': _('Neighbour Platform Details'), },
    '.networking.cdp_cache.neighbours:*.power_consumption': {'title': _('Power Level'), },
    '.networking.cdp_cache.neighbours:*.vtp_mgmt_domain': {'title': _('VTP Domain'), },
    })
