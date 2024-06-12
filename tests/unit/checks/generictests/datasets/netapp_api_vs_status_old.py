#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "netapp_api_vs_status"


info = [["kermit1_ng-mc", "running"], ["bill_vm", "stopped"]]


discovery = {"": [("bill_vm", {}), ("kermit1_ng-mc", {})]}


checks = {
    "": [
        ("bill_vm", {}, [(2, "State: stopped", [])]),
        ("kermit1_ng-mc", {}, [(0, "State: running", [])]),
    ]
}
