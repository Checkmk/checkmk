#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""View for HW/SW inventory data of HPE devices"""

# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

from cmk.gui.views.inventory.registry import inventory_displayhints
from cmk.gui.i18n import _l


inventory_displayhints.update(
    {
        ".hardware.firmware.": {"title": _l("Firmware")},
        ".hardware.firmware.redfish:": {
            "title": _l("Redfish"),
            "keyorder": ["component", "version", "location", "description"],
            "view": "invfirmwareredfish",
        },
        ".hardware.firmware.redfish:*.component": {"title": _l("Component")},
        ".hardware.firmware.redfish:*.version": {"title": _l("Version")},
        ".hardware.firmware.redfish:*.location": {"title": _l("Location")},
        ".hardware.firmware.redfish:*.description": {"title": _l("Description")},
        ".hardware.firmware.redfish:*.updateable": {
            "title": _l("Update possible"),
            "paint": "bool",
        },
    }
)
