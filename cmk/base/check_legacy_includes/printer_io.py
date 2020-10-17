#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=consider-using-in

from cmk.base.check_api import saveint
printer_io_units = {
    '-1': 'unknown',
    '0': 'unknown',
    '2': 'unknown',  # defined by PrtCapacityUnitTC used in newer revs.
    '3': '1/10000 in',
    '4': 'micrometers',
    '8': 'sheets',
    '16': 'feet',
    '17': 'meters',
    '18': 'items',
    '19': 'percent',
}

printer_io_states = {
    # PrtSubUnitStatusTC   monitoring-state   label

    # Availability
    0: (0, 'Available and Idle'),
    2: (0, 'Available and Standby'),
    4: (0, 'Available and Active'),
    6: (0, 'Available and Busy'),
    1: (1, 'Unavailable and OnRequest'),
    3: (2, 'Unavailable because Broken'),
    5: (3, 'Unknown'),

    # Non-critical alerts
    8: (1, 'Non-Critical Alerts'),

    # Critical alerts
    16: (2, 'Critical Alerts'),

    # On-Line state
    32: (2, 'Off-Line'),
    64: (0, 'Transitioning to intended state'),
}


def inventory_printer_io(info):
    for line in info:
        index, name, descr, status = line[:4]
        if descr == '':
            continue
        snmp_status, _capacity_unit, capacity_max, _level = line[3:]
        if capacity_max == '0':  # useless
            continue

        ignore = False
        snmp_status = saveint(status)
        for state_val in sorted(printer_io_states, reverse=True):
            if state_val > 0 and snmp_status - state_val >= 0:
                snmp_status -= state_val
                # Skip sub units where it does not seem to make sense to monitor them
                if state_val in (1, 3, 5):
                    ignore = True
        if ignore is True:
            continue

        # When no name is set
        # a) try to use the description
        # b) try to use the type otherwise use the index
        if name == "unknown" or not name:
            name = descr if descr else index.split('.')[-1]

        yield (name, {})


def check_printer_io(item, params, info, what):
    for line in info:
        index, name, descr = line[:3]

        if name == item or descr == item or index.split('.')[-1] == item:
            snmp_status, capacity_unit, capacity_max, level = line[3:]
            snmp_status, level, capacity_max = saveint(snmp_status), saveint(level), saveint(
                capacity_max)
            if capacity_unit != '':
                capacity_unit = ' ' + printer_io_units[capacity_unit]

            state_txt = []
            state_state = 0

            yield 0, descr
            if snmp_status == 0:
                state_txt.append(printer_io_states[0][1])
            else:
                for state_val in sorted(printer_io_states, reverse=True):
                    if state_val > 0 and snmp_status - state_val >= 0:
                        mon_state, text = printer_io_states[state_val]
                        state_state = max(mon_state, state_state)
                        state_txt.append(text)
                        snmp_status -= state_val

            yield state_state, 'Status: %s' % ', '.join(state_txt)

            if level in [-1, -2] or level < -3:
                pass  # totally skip this info when level is unknown or not limited

            elif capacity_max in (-2, -1, 0):
                # -2: unknown, -1: no restriction, 0: due to saveint
                yield 0, 'Capacity: %s%s' % (level, capacity_unit)

            else:
                state = 0
                levels_txt = ''
                how = 'remaining' if what == 'input' else 'filled'
                if level == -3:
                    level_txt = "at least one"

                else:
                    level_perc = 100.0 * level / capacity_max  # to percent
                    level_txt = '%0.2f%%' % level_perc

                    if what == 'input':
                        warn, crit = params['capacity_levels']  # percentage levels
                        if crit is not None and level_perc <= crit:
                            state = 2
                            levels_txt = ' (<= %0.2f)' % crit
                        elif warn is not None and level_perc <= warn:
                            state = 1
                            levels_txt = ' (<= %0.2f%%)' % warn

                    else:  # output
                        warn, crit = params['capacity_levels']  # percentage levels
                        if crit is not None and level_perc >= crit:
                            state = 2
                            levels_txt = ' (>= %0.2f)' % crit
                        elif warn is not None and level_perc >= warn:
                            state = 1
                            levels_txt = ' (>= %0.2f%%)' % warn

                yield state, 'Capacity: %s of %s%s %s%s' % \
                    (level_txt, capacity_max, capacity_unit, how, levels_txt)
