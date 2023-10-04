#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "fireeye_mail"

mock_item_state = {
    "": {
        "fireeye_mail.total" : (0, 0),
        "fireeye_mail.infected" : (0, 0),
        "fireeye_mail.analyzed" : (0, 0),
    },
    "attachment": {
        "fireeye_mail.total.attachment" : (0, 0),
        "fireeye_mail.infected.attachment" : (0, 0),
        "fireeye_mail.analyzed.attachment" : (0, 0),
    },
    "url": {
        "fireeye_mail.total.url" : (0, 0),
        "fireeye_mail.infected.url" : (0, 0),
        "fireeye_mail.analyzed.url" : (0, 0),
    },
    "statistics": {
        "fireeye.stat.attachment": (0, 0),
        "fireeye.stat.url": (0, 0),
        "fireeye.stat.maliciousattachment": (0, 0),
        "fireeye.stat.maliciousurl": (0, 0),
    },
}

info = [
    [
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "04/06/17 12:00:00",
        "04/06/17 12:01:00",
        "120",
    ]
]


discovery = {
    "": [(None, {})],
    "attachment": [(None, {})],
    "received": [(None, {})],
    "statistics": [(None, {})],
    "url": [(None, {})],
}


checks = {
    "": [
        (
            None,
            {},
            [
                (0, "Total: 0.00 mails/s", [("total_rate", 0.0, None, None, None, None)]),
                (0, "Infected: 0.00 mails/s", [("infected_rate", 0.0, None, None, None, None)]),
                (0, "Analyzed: 0.00 mails/s", [("analyzed_rate", 0.0, None, None, None, None)]),
            ],
        )
    ],
    "attachment": [
        (
            None,
            {},
            [
                (
                    0,
                    "Total Attachment: 0.00 mails/s",
                    [("total_rate", 0.0, None, None, None, None)],
                ),
                (
                    0,
                    "Infected Attachment: 0.00 mails/s",
                    [("infected_rate", 0.0, None, None, None, None)],
                ),
                (
                    0,
                    "Analyzed Attachment: 0.00 mails/s",
                    [("analyzed_rate", 0.0, None, None, None, None)],
                ),
            ],
        )
    ],
    "received": [
        (
            None,
            {"rate": (6000, 7000)},
            [
                (0, "Mails received between 04/06/17 12:00:00 and 04/06/17 12:01:00: 120", []),
                (0, "Rate: 2.00/s", [("mail_received_rate", 2.0, 6000.0, 7000.0, None, None)]),
            ],
        )
    ],
    "statistics": [
        (
            None,
            {},
            [
                (
                    0,
                    "Emails containing Attachment: 0.00 per minute",
                    [("fireeye_stat_attachment", 0.0, None, None, None, None)],
                ),
                (
                    0,
                    "Emails containing URL: 0.00 per minute",
                    [("fireeye_stat_url", 0.0, None, None, None, None)],
                ),
                (
                    0,
                    "Emails containing malicious Attachment: 0.00 per minute",
                    [("fireeye_stat_maliciousattachment", 0.0, None, None, None, None)],
                ),
                (
                    0,
                    "Emails containing malicious URL: 0.00 per minute",
                    [("fireeye_stat_maliciousurl", 0.0, None, None, None, None)],
                ),
            ],
        )
    ],
    "url": [
        (
            None,
            {},
            [
                (0, "Total URL: 0.00 mails/s", [("total_rate", 0.0, None, None, None, None)]),
                (0, "Infected URL: 0.00 mails/s", [("infected_rate", 0.0, None, None, None, None)]),
                (0, "Analyzed URL: 0.00 mails/s", [("analyzed_rate", 0.0, None, None, None, None)]),
            ],
        )
    ],
}
