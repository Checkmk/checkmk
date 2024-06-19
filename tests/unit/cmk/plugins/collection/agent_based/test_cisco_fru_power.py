#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.collection.agent_based.cisco_fru_power import FRU, parse_cisco_fru_power


def test_parse_cisco_fru_power() -> None:
    """This is just a test with made up data that covers properties that I am afraid of braking.

    This does not necessarily mean that these properties are required or correct.
    It's just the status quo.
    """
    states_and_currents = [
        ["1.2.1", "2", "23"],
        ["1.2.2", "2", "23"],
        ["1.2.3", "5", "23"],  # we don't like this state
        ["1.2.4", "10", "0"],
        ["1.2.5", "5", "0"],  # we don't like this current
        ["1.2.6", "2", "23"],
        ["1.2.7", "2", "23"],  # not in the names!
        ["1.2.99", "", ""],  # why is this empty?
    ]
    names = [
        ["1.2.1", "sepp"],
        ["1.2.2", "michl"],
        ["1.2.3", "stofferl"],
        ["1.2.4", "schorsch"],
        ["1.2.5", "resl"],
        ["1.2.6", "sepp"],  # apparently they can repeat.
        ["1.2.8", "sepp"],  # not in states
    ]

    section = {
        "michl": FRU(2, 23),
        "resl": FRU(5, 0),
        "stofferl": FRU(5, 23),
        "schorsch": FRU(10, 0),
        "sepp-1": FRU(2, 23),
        "sepp-2": FRU(2, 23),
    }

    assert parse_cisco_fru_power([states_and_currents, names]) == section
