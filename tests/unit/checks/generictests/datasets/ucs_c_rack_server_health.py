#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ucs_c_rack_server_health"


info = [
    [
        "storageControllerHealth",
        "dn sys/rack-unit-1/board/storage-SAS-SLOT-HBA/vd-0",
        "id SLOT-HBA",
        "health Good",
    ],
    [
        "storageControllerHealth",
        "dn sys/rack-unit-2/board/storage-SAS-SLOT-HBA/vd-0",
        "id SLOT-HBA",
        "health AnythingElse",
    ],
]


discovery = {
    "": [
        ("Rack unit 1 Storage SAS SLOT HBA vd 0", {}),
        ("Rack unit 2 Storage SAS SLOT HBA vd 0", {}),
    ]
}


checks = {
    "": [
        ("Rack unit 1 Storage SAS SLOT HBA vd 0", {}, [(0, "Status: good", [])]),
        ("Rack unit 2 Storage SAS SLOT HBA vd 0", {}, [(3, "Status: unknown[anythingelse]", [])]),
    ]
}
