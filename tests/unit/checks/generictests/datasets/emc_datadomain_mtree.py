#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "emc_datadomain_mtree"


info = [
    ["/data/col1/boost_vmware", "3943.3", "3"],
    ["/data/col1/repl_cms_dc1", "33.3", "2"],
    ["/data/col1/nfs_cms_dc1", "0.0", "1"],
    ["something", "0.0", "-1"],
]


discovery = {
    "": [
        ("/data/col1/boost_vmware", {}),
        ("/data/col1/repl_cms_dc1", {}),
        ("/data/col1/nfs_cms_dc1", {}),
        ("something", {}),
    ]
}


_defeault_params = {
    "deleted": 2,
    "read-only": 1,
    "read-write": 0,
    "replication destination": 0,
    "retention lock disabled": 0,
    "retention lock enabled": 0,
    "unknown": 3,
}

checks = {
    "": [
        (
            "/data/col1/boost_vmware",
            _defeault_params,
            [(0, "Status: read-write, Precompiled: 3.85 TiB", [("precompiled", 4234086134579)])],
        ),
        (
            "/data/col1/repl_cms_dc1",
            _defeault_params,
            [(1, "Status: read-only, Precompiled: 33.3 GiB", [("precompiled", 35755602739)])],
        ),
        (
            "/data/col1/nfs_cms_dc1",
            _defeault_params,
            [(2, "Status: deleted, Precompiled: 0 B", [("precompiled", 0)])],
        ),
        (
            "something",
            _defeault_params,
            [(3, "Status: invalid code -1, Precompiled: 0 B", [("precompiled", 0)])],
        ),
    ]
}
