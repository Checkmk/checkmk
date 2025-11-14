#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-12-27
# File  : inv_ip_addresses.py

from cmk.gui.views.inventory.registry import inventory_displayhints
# from cmk.gui.plugins.visuals.inventory import FilterInvtableIDRange
from cmk.gui.i18n import _l

inventory_displayhints.update({
    '.networking.addresses:': {
        'title': _l('IP Addresses'),
        'keyorder': [
            'address', 
            'device', 
            'type',
            'network',
            'netmask',
            'cidr',
            'broadcast',
        ],
        'view': 'invipaddresses_of_host',
    },
    '.networking.addresses:*.address': {'title': _l('Address')},
    '.networking.addresses:*.broadcast': {'title': _l('Broadcast')},
    '.networking.addresses:*.cidr': {'title': _l('Prefix Length'), },  # 'filter': FilterInvtableIDRange},
    '.networking.addresses:*.device': {'title': _l('Device')},
    '.networking.addresses:*.netmask': {'title': _l('Netmask')},
    '.networking.addresses:*.network': {'title': _l('Network')},
    '.networking.addresses:*.type': {'title': _l('Type'), 'paint': 'ip_address_type'},
    '.networking.addresses:*.scope_id': {'title': _l('Scope ID')},
})
