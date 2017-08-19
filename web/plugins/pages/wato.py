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

import wato
import watolib

register_handlers({
    "wato"                      : wato.page_handler,

    "ajax_start_activation"     : lambda: wato.ModeAjaxStartActivation().handle_page(),
    "ajax_activation_state"     : lambda: wato.ModeAjaxActivationState().handle_page(),

    "automation_login"          : wato.page_automation_login,
    "noauth:automation"         : wato.page_automation,
    "user_profile"              : wato.page_user_profile,
    "user_change_pw"            : lambda: wato.page_user_profile(change_pw=True),
    "ajax_set_foldertree"       : wato.ajax_set_foldertree,
    "wato_ajax_diag_host"       : wato.ajax_diag_host,
    "wato_ajax_profile_repl"    : watolib.ajax_profile_repl,
    "wato_ajax_execute_check"   : lambda: wato.ModeAjaxExecuteCheck().handle_page(),
    "download_agent_output"     : wato.page_download_agent_output,
    "ajax_popup_move_to_folder" : wato.ajax_popup_move_to_folder,
    "ajax_backup_job_state"     : lambda: wato.ModeAjaxBackupJobState().page(),
})
