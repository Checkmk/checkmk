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


