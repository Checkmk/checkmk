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

import wato

pagehandlers.update({
    "wato"                    : wato.page_handler,
    "wato_ajax_replication"   : wato.ajax_replication,
    "wato_ajax_activation"    : wato.ajax_activation,
    "automation_login"        : wato.page_automation_login,
    "noauth:automation"       : wato.page_automation,
    "user_profile"            : wato.page_user_profile,
    "user_change_pw"          : lambda: wato.page_user_profile(change_pw=True),
    "ajax_set_foldertree"     : wato.ajax_set_foldertree,
    "wato_ajax_diag_host"     : wato.ajax_diag_host,
    "wato_ajax_profile_repl"  : wato.ajax_profile_repl,
    "wato_ajax_execute_check" : wato.ajax_execute_check,
})
