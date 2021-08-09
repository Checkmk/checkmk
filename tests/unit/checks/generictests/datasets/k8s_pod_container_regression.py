#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


from cmk.base.discovered_labels import HostLabel

checkname = "k8s_pod_container"

parsed = {
    u"pi": {
        u"image_pull_policy": u"Always",
        u"state_reason": u"Completed",
        u"image": u"perl",
        u"container_id": u"94d698838e88b72fdaf7b48dd7c227f5d36915c3279af6b1da33d397cef0c276",
        u"restart_count": 0,
        u"image_id": u"docker-pullable://perl@sha256:5cada8a3709c245b0256a4d986801e598abf95576eb01767bde94d567e23104e",
        u"state": u"terminated",
        u"ready": False,
        u"state_exit_code": 0,
    }
}

discovery = {
    "": [(None, {})]
}

checks = {
    "": [(
        None,
        {},
        [
            (
                0,
                "Ready: 0/1",
                [
                    ("docker_all_containers", 1, None, None, 0, 1),
                    ("ready_containers", 0, None, None, 0, 1),
                ],
            ),
            (0, "Running: 0", []),
            (0, "Waiting: 0", []),
            (0, "Terminated: 1", []),
        ],
    )],
}
