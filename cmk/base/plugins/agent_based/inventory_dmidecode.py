#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Tuple
from .agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register

Section = List[Tuple[str, StringTable]]


def parse_dmidecode(string_table: StringTable) -> Section:
    """Parse the output of `dmidecode -q | sed 's/\t/:/g'` with sep(58)

    This is a *massively* reduced example:

        >>> from pprint import pprint
        >>> string_table = [line.split(':') for line in [
        ...     'Processor Information',
        ...     ':Type: Central Processor',
        ...     ':Family: Core i7',
        ...     ':Manufacturer: Intel(R) Corporation',
        ...     ':ID: 61 06 04 00 FF FB EB BF',
        ...     ':Flags:',
        ...     '::FPU (Floating-point unit on-chip)',
        ...     '::VME (Virtual mode extension)',
        ...     '::DE (Debugging extension)',
        ...     '',
        ...     'Chassis Information',
        ...     ':Manufacturer: Apple Inc.',
        ...     ':Type: Laptop',
        ...     '',
        ...     'Onboard Device',
        ...     ':Reference Designation: Integrated Video Controller',
        ...     ':Type: Video',
        ...     ':Status: Enabled',
        ...     ':Type Instance: 1',
        ...     ':Bus Address: 0000:00:00.0',
        ...     '',
        ...     'Physical Memory Array',
        ...     ':Location: System Board Or Motherboard',
        ...     ':Number Of Devices: 2',
        ...     '',
        ...     'Memory Device',
        ...     ':Bank Locator: BANK 0',
        ...     '',
        ...     'Memory Device',
        ...     ':Bank Locator: BANK 1',
        ... ] if line]
        >>> pprint(parse_dmidecode(string_table))
        [('Processor Information',
          [['Type', 'Central Processor'],
           ['Family', 'Core i7'],
           ['Manufacturer', 'Intel(R) Corporation'],
           ['ID', '61 06 04 00 FF FB EB BF'],
           ['Flags', ''],
           ['', 'FPU (Floating-point unit on-chip)'],
           ['', 'VME (Virtual mode extension)'],
           ['', 'DE (Debugging extension)']]),
         ('Chassis Information', [['Manufacturer', 'Apple Inc.'], ['Type', 'Laptop']]),
         ('Onboard Device',
          [['Reference Designation', 'Integrated Video Controller'],
           ['Type', 'Video'],
           ['Status', 'Enabled'],
           ['Type Instance', '1'],
           ['Bus Address', '0000', '00', '00.0']]),
         ('Physical Memory Array',
          [['Location', 'System Board Or Motherboard'], ['Number Of Devices', '2']]),
         ('Memory Device', [['Bank Locator', 'BANK 0']]),
         ('Memory Device', [['Bank Locator', 'BANK 1']])]


    Note: on Linux \t is replaced by : and then the split is done by :.
    On Windows the \t comes 1:1 and no splitting is being done.
    So we need to split manually here.
    """
    # We cannot use a dict here, we may have multiple
    # subsections with the same title and the order matters!
    subsections = []
    current_lines: StringTable = []  # these will not be used
    for line in string_table:
        # Windows plugin keeps tabs and has no separator
        if len(line) == 1:
            parts = line[0].replace("\t", ":").split(":")
            line = [x.strip() for x in parts]

        if len(line) == 1:
            current_lines = []
            subsections.append((line[0], current_lines))
        else:
            current_lines.append([w.strip() for w in line[1:]])

    return subsections


register.agent_section(
    name="dmidecode",
    parse_function=parse_dmidecode,
)
