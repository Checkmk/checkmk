#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2020-11-26

# 2023-06-14: removed declare_invtable_view from view definition on cmk 2.2 (see werk 15493)
#             changed inventory_displayhints import (see werk 15493)
# 2023-09-02: updated to match CMK 2.2.0p7 version of display hints for ".networking.interfaces:"
# 2023-11-17: moved file back from local/lib/ structure to local/share/ structure to avoid errors in web.log


from cmk.gui.i18n import _l
from cmk.gui.views.inventory.registry import inventory_displayhints


inventory_displayhints.update({
    '.networking.interfaces:': {
        'title': _l('Network interfaces'),
        'keyorder': [
            'index',
            'name',
            'description',
            'alias',
            'oper_status',
            'admin_status',
            'available',
            'speed',
            'last_change',
            'port_type',
            'phys_address',
            'vlantype',
            'vlans',
        ],
        'view': 'invinterface',
        'is_show_more': False,
    },
    '.networking.interfaces:*.name': {'title': _l('Name'), },
})
