#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import math

def our_uptime():
    return float((file("/proc/uptime").read().split()[0]))

# replace simulator tags in output
def agent_simulator_process(output):
    try:
        while True:
            i = output.find('%{')
            if i == -1:
                break
            e = output.find('}', i)
            if e == -1:
                break
            simfunc = output[i+2 : e]
            replacement = str(eval("agentsim_" + simfunc))
            output = output[:i] + replacement + output[e+1:]
    except Exception, e:
        if opt_debug:
            raise

    return output

def agentsim_uptime(rate = 1.0, period = None): # period = sinus wave
    if period == None:
        return int(our_uptime() * rate)
    else:
        a = (rate * period) / (2.0 * math.pi)
        u = our_uptime()
        return int(u * rate + int(a * math.sin(u * 2.0 * math.pi / period)))

def agentsim_enum(values, period = 1): # period is in seconds
    hit = int(our_uptime()) / period % len(values)
    return values[hit]

def agentsim_sinus(base = 50, amplitude = 50, period = 300):
    return int(math.sin(our_uptime() * 2.0 * math.pi / period) * amplitude + base)

