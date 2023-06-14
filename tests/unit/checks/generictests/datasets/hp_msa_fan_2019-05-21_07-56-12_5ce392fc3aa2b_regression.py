#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "hp_msa_fan"


parsed = {
    "Enclosure 1 Left": {
        "extended-status": "16",
        "fw-revision": "",
        "health": "OK",
        "health-numeric": "0",
        "health-reason": "",
        "health-recommendation": "",
        "hw-revision": "",
        "item_type": "fan",
        "location": "Enclosure 1 - Left",
        "locator-led": "Aus",
        "locator-led-numeric": "0",
        "name": "Fan Loc:left-PSU 1",
        "position": "Links",
        "position-numeric": "0",
        "serial-number": "",
        "speed": "3950",
        "status": "Aktiv",
        "status-numeric": "0",
        "status-ses": "OK",
        "status-ses-numeric": "1",
    },
    "Enclosure 1 Right": {
        "extended-status": "16",
        "fw-revision": "",
        "health": "OK",
        "health-numeric": "0",
        "health-reason": "",
        "health-recommendation": "",
        "hw-revision": "",
        "item_type": "fan",
        "location": "Enclosure 1 - Right",
        "locator-led": "Aus",
        "locator-led-numeric": "0",
        "name": "Fan Loc:right-PSU 2",
        "position": "Rechts",
        "position-numeric": "1",
        "serial-number": "",
        "speed": "4020",
        "status": "Aktiv",
        "status-numeric": "0",
        "status-ses": "OK",
        "status-ses-numeric": "1",
    },
}


discovery = {"": [("Enclosure 1 Left", None), ("Enclosure 1 Right", None)]}


checks = {
    "": [
        ("Enclosure 1 Left", {}, [(0, "Status: up, speed: 3950 RPM", [])]),
        ("Enclosure 1 Right", {}, [(0, "Status: up, speed: 4020 RPM", [])]),
    ]
}
