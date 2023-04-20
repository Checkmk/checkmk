#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "k8s_daemon_pods"

parsed = {
    "collision_count": None,
    "conditions": None,
    "current_number_scheduled": 1,
    "desired_number_scheduled": 1,
    "number_available": 1,
    "number_misscheduled": 0,
    "number_ready": 1,
    "number_unavailable": None,
    "observed_generation": 1,
    "updated_number_scheduled": 1,
}

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {},
            [
                (0, "Ready: 1", [("k8s_daemon_pods_ready", 1, None, None, None, None)]),
                (
                    0,
                    "Scheduled: 1/1",
                    [
                        ("k8s_daemon_pods_scheduled_desired", 1, None, None, None, None),
                        ("k8s_daemon_pods_scheduled_current", 1, None, None, None, None),
                    ],
                ),
                (
                    0,
                    "Up to date: 1",
                    [("k8s_daemon_pods_scheduled_updated", 1, None, None, None, None)],
                ),
                (
                    0,
                    "Available: 1/1",
                    [
                        ("k8s_daemon_pods_available", 1, None, None, None, None),
                        ("k8s_daemon_pods_unavailable", 0, None, None, None, None),
                    ],
                ),
            ],
        )
    ],
}
