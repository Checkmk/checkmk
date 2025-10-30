#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.gui.i18n import _l
from cmk.gui.views.inventory.registry import inventory_displayhints

inventory_displayhints.update({
    '.networking.uplinks:': {
        'title': _l('Device uplinks'),
        'view': 'invciscomerakideviceuplinksinfo_of_host',
        'keyorder': ['interface', 'protocol', 'address', 'gateway', 'public_address']
    },

    '.software.applications.cisco_meraki.': {'title': _l('Cisco Meraki Cloud'), },
    '.software.applications.cisco_meraki.licenses:': {
        'title': _l('Licensed devices overview'),
        'keyorder': ['org_id', 'org_name', 'summary'],
        'view': 'invciscomerakilicensesoverview_of_host',
    },
    '.software.applications.cisco_meraki.licenses:*.org_id': {'title': _l('Organisation ID'), 'short': _l('Org ID')},
    '.software.applications.cisco_meraki.licenses:*.org_name': {
        'title': _l('Organisation Name'),
        'short': _l('Org Name')
    },
    '.software.applications.cisco_meraki.licenses:*.sm': {'title': _l('Systems Manager (SM)'), 'short': _l('SM')},
    '.software.applications.cisco_meraki.licenses:*.mg': {'title': _l('Gateways (MG)'), 'short': _l('MG')},
    '.software.applications.cisco_meraki.licenses:*.ms': {'title': _l('Switches (MS)'), 'short': _l('MS')},
    '.software.applications.cisco_meraki.licenses:*.mx': {'title': _l('Security/SD-WAN (MX)'), 'short': _l('MX')},
    '.software.applications.cisco_meraki.licenses:*.mv': {'title': _l('Video (MV)'), 'short': _l('MV')},
    '.software.applications.cisco_meraki.licenses:*.mt': {'title': _l('Sensor (MT)'), 'short': _l('MT')},
    '.software.applications.cisco_meraki.licenses:*.mr': {
        'title': _l('Access Points/Wireless (MR)'),
        'short': _l('MR')
    },
    '.software.applications.cisco_meraki.licenses:*.summary': {'title': _l('Summary'), },

    '.software.applications.cisco_meraki.device_info.': {
        'title': _l('Device Info'),
        'keyorder': [
            'organisation_id',
            'organisation_name',
            'network_id',
            'network_name',
            'address',
        ],
    },
    '.software.applications.cisco_meraki.device_info.organisation_id': {'title': _l('Organisation ID')},
    '.software.applications.cisco_meraki.device_info.organisation_name': {'title': _l('Organisation Name')},
    '.software.applications.cisco_meraki.device_info.network_id': {'title': _l('Network ID')},
    '.software.applications.cisco_meraki.device_info.network_name': {'title': _l('Network Name')},
    '.software.applications.cisco_meraki.device_info.address': {'title': _l('Address')},

    '.software.applications.cisco_meraki.organisations:': {
        'title': _l('Organisation overview'),
        'keyorder': ['org_id', 'org_name', 'api', 'licensing', 'cloud', 'url'],
        'view': 'invciscomerakiorganisationoverview_of_host',
    },
    '.software.applications.cisco_meraki.organisations:*.org_id': {
        'title': _l('Organisation ID'),
        'short': _l('Org ID')
    },
    '.software.applications.cisco_meraki.organisations:*.org_name': {
        'title': _l('Organisation name'),
        'short': _l('Org name')
    },
    '.software.applications.cisco_meraki.organisations:*.api': {'title': _l('API status'), 'short': _l('API')},
    '.software.applications.cisco_meraki.organisations:*.licensing': {
        'title': _l('Licensing model'),
        'short': _l('Licensing')
    },
    '.software.applications.cisco_meraki.organisations:*.cloud': {'title': _l('Cloud region'), 'short': _l('Cloud')},
    '.software.applications.cisco_meraki.organisations:*.url': {'title': _l('URL'), 'short': _l('URL')},

    '.software.applications.cisco_meraki.networks:': {
        'title': _l('Networks overview'),
        'keyorder': [
            'organisation_id',
            'organisation_name',
            'network_id',
            'network_name',
            'time_zone',
            'product_types',
            'tags',
            'notes',
            # 'url',
            # 'is_bound_to_template',
            # 'enrollment_string',
        ],
        'view': 'invciscomerakinetworksoverview_of_host',
    },
    '.software.applications.cisco_meraki.networks:*.organisation_id': {
        'title': _l('Organisation ID'),
        'short': _l('Org ID'),
    },
    '.software.applications.cisco_meraki.networks:*.organisation_name': {
        'title': _l('Organisation Name'),
        'short': _l('Org name'),
    },
    '.software.applications.cisco_meraki.networks:*.network_id': {'title': _l('Network ID')},
    '.software.applications.cisco_meraki.networks:*.network_name': {'title': _l('Network Name')},
    '.software.applications.cisco_meraki.networks:*.time_zone': {'title': _l('Time Zone')},
    '.software.applications.cisco_meraki.networks:*.product_types': {'title': _l('Product types')},

    '.software.applications.cisco_meraki.networks:*.url': {'title': _l('URL'), 'short': _l('URL')},
    '.software.applications.cisco_meraki.networks:*.notes': {'title': _l('Notes')},
    '.software.applications.cisco_meraki.networks:*.enrollment_string': {'title': _l('Enrollment string')},
    '.software.applications.cisco_meraki.networks:*.tags': {'title': _l('Tags')},
    '.software.applications.cisco_meraki.networks:*.is_bound_to_template': {'title': _l('Is bound to template')},
})
