#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "domino_mailqueues"


info = [
    ["1", "4711", "815", "1", "12"],
]


discovery = {
    "": [
        ("lnDeadMail", {}),
        ("lnWaitingMail", {}),
        ("lnMailHold", {}),
        ("lnMailTotalPending", {}),
        ("InMailWaitingforDNS", {}),
    ],
}


checks = {
    "": [
        (
            "lnDeadMail",
            {"queue_length": (300, 350)},
            [
                (
                    0,
                    "Dead mails: 1",
                    [
                        ("mails", 1, 300, 350, None, None),
                    ],
                ),
            ],
        ),
        (
            "lnWaitingMail",
            {"queue_length": (300, 350)},
            [
                (
                    2,
                    "Waiting mails: 4711 (warn/crit at 300/350)",
                    [
                        ("mails", 4711, 300, 350, None, None),
                    ],
                ),
            ],
        ),
        (
            "lnMailHold",
            {"queue_length": (300, 350)},
            [
                (
                    2,
                    "Mails on hold: 815 (warn/crit at 300/350)",
                    [
                        ("mails", 815, 300, 350, None, None),
                    ],
                ),
            ],
        ),
        (
            "lnMailTotalPending",
            {"queue_length": (300, 350)},
            [
                (
                    0,
                    "Total pending mails: 1",
                    [
                        ("mails", 1, 300, 350, None, None),
                    ],
                ),
            ],
        ),
        (
            "InMailWaitingforDNS",
            {"queue_length": (300, 350)},
            [
                (
                    0,
                    "Mails waiting for DNS: 12",
                    [
                        ("mails", 12, 300, 350, None, None),
                    ],
                )
            ],
        ),
    ],
}
