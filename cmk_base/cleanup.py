#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

"""Hacky module to avoid cyclic imports. This should die..."""

# Reset some global variable to their original value. This is needed in
# keepalive mode. We could in fact do some positive caching in keepalive mode,
# e.g. the counters of the hosts could be saved in memory.
def cleanup_globals():
    # THIS IS HORRIBLE! We can't move the imports to the global scope because of cycles...
    import cmk_base.checks
    cmk_base.checks.set_hostname("unknown")
    import cmk_base.item_state
    cmk_base.item_state.cleanup_item_states()
    import cmk_base.core
    cmk_base.core.cleanup_timeperiod_caches()
    import cmk_base.snmp
    cmk_base.snmp.cleanup_host_caches()
