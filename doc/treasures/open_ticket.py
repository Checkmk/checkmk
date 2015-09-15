#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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

#!/usr/bin/python

# Custom command for creating support tickets

config.declare_permission("action.sap_openticket",
        _("Open Support Ticket"),
        _("Open a support ticket for this host/service"),
        [ "user", "admin" ])

def command_open_ticket(cmdtag, spec, row):
    if html.var("_sap_openticket"):
        comment = u"OPENTICKET:" + html.var_utf8("_sap_ticket_comment")
        broadcast = 0
        forced = 2
        command = "SEND_CUSTOM_%s_NOTIFICATION;%s;%s;%s;%s" % \
                ( cmdtag, spec, broadcast + forced, config.user_id, lqencode(comment))
        title = _("<b>open a support ticket</b> regarding")
        return command, title


multisite_commands.append({
    "tables"      : [ "host", "service" ],
    "permission"  : "action.sap_openticket",
    "title"       : _("Open support ticket"),
    "render"      : lambda: \
        html.write(_('Comment') + ": ") == \
        html.text_input("_sap_ticket_comment", "", size=50, submit="_sap_openticket") == \
        html.write(" &nbsp; ") == \
        html.button("_sap_openticket", _('Open Ticket')),
    "action"      : command_open_ticket,
    "group"       : _("SAP Ticket"),
})


