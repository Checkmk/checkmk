#!/usr/bin/python
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
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

def sync_pre_activate_changes(_unused):
    # In some rare cases for still unknown reasons at this time the
    # variable config sometimes has the value None. This could or could
    # not be a mod_python problem. But it makes the activation of changes
    # in a D-WATO setup break. So better handle this case here.
    try:
        do_sync = 'wato_pre_activate_changes' in config.userdb_automatic_sync
    except:
        do_sync = False
    if do_sync:
        userdb.hook_sync()

register_hook('pre-activate-changes', sync_pre_activate_changes)
