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

# An icon painter is a python function which gets four parameters and
# returns one string of rendered HTML code or None.
#
# The parameters are shown below:
#
#    def paint_icon_image(what, row, tags, host_custom_vars):
#        """
#        what:             The type of the current object
#        row:              The livestatus row for the current object
#        tags:             List of cmk tags for this object
#        host_custom_vars: Dict of the objects host custom variables
#        """
#        return repr(row)
#
# Each icon painter needs to be registered to multisite. To do this
# you need to add one dictionary to the multisite_icons list. The order
# of the multisite icons controls in the list controls the order in the
# GUI.
# The dictionary must at least contain the 'paint' attribute with the
# paint function as value. There are several other optional attributes
# as shown in this example:
#
#multisite_icons.append({
#    # List of columns to be used in this icon
#    'columns':         [ 'icon_image' ],
#    # List of columns to be used in this icon when rendering as host
#    'host_columns':    [],
#    # List of columns to be used in this icon when rendering as service
#    'service_columns': [],
#    # The paint function as mentioned above
#    'paint':           paint_icon_image,
#})

#   .--Action Menu---------------------------------------------------------.
#   |          _        _   _               __  __                         |
#   |         / \   ___| |_(_) ___  _ __   |  \/  | ___ _ __  _   _        |
#   |        / _ \ / __| __| |/ _ \| '_ \  | |\/| |/ _ \ '_ \| | | |       |
#   |       / ___ \ (__| |_| | (_) | | | | | |  | |  __/ | | | |_| |       |
#   |      /_/   \_\___|\__|_|\___/|_| |_| |_|  |_|\___|_| |_|\__,_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_action_menu(what, row, tags, host_custom_vars):
    url_vars = [
        ('host', row['host_name']),
    ]

    if row.get('site'):
        url_vars.append(('site', row['site']))

    if what == 'service':
        url_vars.append(('service', row['service_description']))

    if html.has_var('display_options'):
        url_vars.append(('display_options', html.var('display_options')))
    if html.has_var('_display_options'):
        url_vars.append(('_display_options', html.var('_display_options')))

    return html.render_popup_trigger(
        html.render_icon('menu', _('Open the action menu'), cssclass="iconbutton"),
        'action_menu', 'action_menu', url_vars=url_vars)

multisite_icons_and_actions['action_menu'] = {
    'columns':         [],
    'paint':           paint_action_menu,
    'toplevel':        True,
    'sort_index':      10,
}

#.
#   .--Icon-Image----------------------------------------------------------.
#   |       ___                     ___                                    |
#   |      |_ _|___ ___  _ __      |_ _|_ __ ___   __ _  __ _  ___         |
#   |       | |/ __/ _ \| '_ \ _____| || '_ ` _ \ / _` |/ _` |/ _ \        |
#   |       | | (_| (_) | | | |_____| || | | | | | (_| | (_| |  __/        |
#   |      |___\___\___/|_| |_|    |___|_| |_| |_|\__,_|\__, |\___|        |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_icon_image(what, row, tags, custom_vars):
    img = row[what + '_icon_image']
    if img:
        if img.endswith('.png'):
            img = img[:-4]
        return html.render_icon(img)

multisite_icons_and_actions['icon_image'] = {
    'columns':         [ 'icon_image' ],
    'paint':           paint_icon_image,
    'toplevel':        True,
    'sort_index':      25,
}

#.
#   .--Reschedule----------------------------------------------------------.
#   |          ____                _              _       _                |
#   |         |  _ \ ___  ___  ___| |__   ___  __| |_   _| | ___           |
#   |         | |_) / _ \/ __|/ __| '_ \ / _ \/ _` | | | | |/ _ \          |
#   |         |  _ <  __/\__ \ (__| | | |  __/ (_| | |_| | |  __/          |
#   |         |_| \_\___||___/\___|_| |_|\___|\__,_|\__,_|_|\___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_reschedule(what, row, tags, host_custom_vars):
    if what == "service" and row["service_cached_at"]:
        output = _("This service is based on cached agent data and cannot be rescheduled.")
        output += " %s" % render_cache_info(what, row)

        return "cannot_reschedule", output, None

    # Reschedule button
    if row[what + "_check_type"] == 2:
        return # shadow hosts/services cannot be rescheduled

    if (row[what + "_active_checks_enabled"] == 1
        or row[what + '_check_command'].startswith('check_mk-')) \
       and config.user.may('action.reschedule'):

        servicedesc = ''
        wait_svc    = ''
        icon        = 'reload'
        txt         = _('Reschedule check')

        if what == 'service':
            servicedesc = row['service_description'].replace("\\","\\\\")
            wait_svc = servicedesc

            # Use Check_MK service for cmk based services
            if row[what + '_check_command'].startswith('check_mk-'):
                servicedesc = 'Check_MK'
                icon        = 'reload_cmk'
                txt         = _('Reschedule \'Check_MK\' service')

        url = 'onclick:reschedule_check(this, \'%s\', \'%s\', \'%s\', \'%s\');' % \
                (row["site"], row["host_name"], html.urlencode(servicedesc), html.urlencode(wait_svc))
        return icon, txt, url

multisite_icons_and_actions['reschedule'] = {
    'columns':         [ 'check_type', 'active_checks_enabled', 'check_command' ],
    'service_columns': [ 'cached_at', 'cache_interval' ],
    'paint':           paint_reschedule,
    'toplevel':        False,
}

#.
#   .--Rule-Editor---------------------------------------------------------.
#   |         ____        _            _____    _ _ _                      |
#   |        |  _ \ _   _| | ___      | ____|__| (_) |_ ___  _ __          |
#   |        | |_) | | | | |/ _ \_____|  _| / _` | | __/ _ \| '__|         |
#   |        |  _ <| |_| | |  __/_____| |__| (_| | | || (_) | |            |
#   |        |_| \_\\__,_|_|\___|     |_____\__,_|_|\__\___/|_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Icon to the parameters of a host or service                         |
#   '----------------------------------------------------------------------'

def paint_rule_editor(what, row, tags, host_custom_vars):
    if row[what + "_check_type"] == 2:
        return # shadow services have no parameters

    if config.wato_enabled and config.user.may("wato.rulesets") and config.multisite_draw_ruleicon:
        urlvars = [("mode", "object_parameters"),
                   ("host", row["host_name"])]

        if what == 'service':
            urlvars.append(("service", row["service_description"]))
            title = _("Parameters for this service")
        else:
            title = _("Parameters for this host")

        return 'rulesets', title, html.makeuri_contextless(urlvars, "wato.py")

multisite_icons_and_actions['rule_editor'] = {
    'columns':         [ 'check_type' ],
    'host_columns'   : [ 'name' ],
    'service_columns': [ 'description' ],
    'paint':           paint_rule_editor,
}

#.
#   .--Manpage-------------------------------------------------------------.
#   |              __  __                                                  |
#   |             |  \/  | __ _ _ __  _ __   __ _  __ _  ___               |
#   |             | |\/| |/ _` | '_ \| '_ \ / _` |/ _` |/ _ \              |
#   |             | |  | | (_| | | | | |_) | (_| | (_| |  __/              |
#   |             |_|  |_|\__,_|_| |_| .__/ \__,_|\__, |\___|              |
#   |                                |_|          |___/                    |
#   +----------------------------------------------------------------------+
#   |  Link to the check manpage                                           |
#   '----------------------------------------------------------------------'

def paint_manpage_icon(what, row, tags, host_custom_vars):
    if what == "service" and config.wato_enabled and config.user.may("wato.use"):
        command = row["service_check_command"]
        if command.startswith("check_mk-"):
            check_type = command[9:]
        elif command.startswith("check_mk_active-"):
            check_name = command[16:].split("!")[0]
            if check_name == "cmk_inv":
                return
            check_type = "check_" + check_name
        else:
            return
        urlvars = [("mode", "check_manpage"), ("check_type", check_type)]
        return 'check_plugins', _("Manual page for this check type"), html.makeuri_contextless(urlvars, "wato.py")


multisite_icons_and_actions['check_manpage'] = {
    'service_columns': [ 'check_command' ],
    'paint':           paint_manpage_icon,
}


#.
#   .--Acknowledge---------------------------------------------------------.
#   |       _        _                        _          _                 |
#   |      / \   ___| | ___ __   _____      _| | ___  __| | __ _  ___      |
#   |     / _ \ / __| |/ / '_ \ / _ \ \ /\ / / |/ _ \/ _` |/ _` |/ _ \     |
#   |    / ___ \ (__|   <| | | | (_) \ V  V /| |  __/ (_| | (_| |  __/     |
#   |   /_/   \_\___|_|\_\_| |_|\___/ \_/\_/ |_|\___|\__,_|\__, |\___|     |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_ack_image(what, row, tags, host_custom_vars):
    if row[what + "_acknowledged"]:
        return 'ack', _('This problem has been acknowledged')

multisite_icons_and_actions['status_acknowledged'] = {
    'columns':         [ 'acknowledged' ],
    'paint':           paint_ack_image,
    'toplevel':        True,
}

#.
#   .--Real-Host-----------------------------------------------------------.
#   |             ____            _       _   _           _                |
#   |            |  _ \ ___  __ _| |     | | | | ___  ___| |_              |
#   |            | |_) / _ \/ _` | |_____| |_| |/ _ \/ __| __|             |
#   |            |  _ <  __/ (_| | |_____|  _  | (_) \__ \ |_              |
#   |            |_| \_\___|\__,_|_|     |_| |_|\___/|___/\__|             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_realhost_link_image(what, row, tags, host_custom_vars):
    # Link to detail host if this is a summary host
    if "_REALNAME" in host_custom_vars:
        newrow = row.copy()
        newrow["host_name"] = host_custom_vars["_REALNAME"]
        return 'detail', _("Detailed host infos"), url_to_view(newrow, 'host')

multisite_icons_and_actions['realhost'] = {
    'paint':           paint_realhost_link_image,
}

#.
#   .--Perfgraph-----------------------------------------------------------.
#   |           ____            __                       _                 |
#   |          |  _ \ ___ _ __ / _| __ _ _ __ __ _ _ __ | |__              |
#   |          | |_) / _ \ '__| |_ / _` | '__/ _` | '_ \| '_ \             |
#   |          |  __/  __/ |  |  _| (_| | | | (_| | |_) | | | |            |
#   |          |_|   \___|_|  |_|  \__, |_|  \__,_| .__/|_| |_|            |
#   |                              |___/          |_|                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


# Intelligent Links to PNP4Nagios 0.6.X
def pnp_url(row, what, how = 'graph'):
    sitename = row["site"]
    host = pnp_cleanup(row["host_name"])
    if what == "host":
        svc = "_HOST_"
    else:
        svc = pnp_cleanup(row["service_description"])
    url_prefix = config.site(sitename)["url_prefix"]
    if html.mobile:
        url = url_prefix + ("pnp4nagios/index.php?kohana_uri=/mobile/%s/%s/%s" % \
            (how, html.urlencode(host), html.urlencode(svc)))
    else:
        url = url_prefix + ("pnp4nagios/index.php/%s?host=%s&srv=%s" % \
            (how, html.urlencode(host), html.urlencode(svc)))

    if how == 'graph':
        url += "&theme=multisite&baseurl=%scheck_mk/" % \
                        html.urlencode(url_prefix)
    return url


def pnp_popup_url(row, what):
    return pnp_url(row, what, 'popup')


def new_graphing_url(row, what):
    site_id = row["site"]

    urivars = [
        ("siteopt",   site_id),
        ("host",      row["host_name"]),
    ]

    if what == "service":
        urivars += [
            ("service", row["service_description"]),
            ("view_name", "service_graphs"),
        ]
    else:
        urivars.append(("view_name", "host_graphs"))

    return html.makeuri_contextless(urivars, filename="view.py")


def pnp_graph_icon_link(row, what):
    if display_options.disabled(display_options.X):
        return ""

    if not metrics.cmk_graphs_possible(row["site"]):
        return pnp_url(row, what)
    else:
        return new_graphing_url(row, what)


def pnp_icon(row, what):
    url = pnp_graph_icon_link(row, what)

    if not metrics.cmk_graphs_possible(row["site"]):
        # Directly ask PNP for all data, don't try to use the new graph fetching mechanism
        # to keep the number of single requests low
        hover_content_func = 'fetch_pnp_hover_contents(\'%s\')' % pnp_popup_url(row, what)
    else:
        # Don't show the icon with Check_MK graphing. The hover makes no sense and there is no
        # mobile view for graphs, so the graphs on the bottom of the host/service view are enough
        # for the moment.
        if html.is_mobile():
            return

        hover_content_func = 'hover_graph(\'%s\', \'%s\', \'%s\')' % \
                                (row['site'], row['host_name'], row.get('service_description', '_HOST_').replace("\\", "\\\\"))

    return '<a href="%s" onmouseover="show_hover_menu(event, %s)" ' \
           'onmouseout="hide_hover_menu()">%s</a>' % (url, hover_content_func, html.render_icon('pnp', ''))


def paint_pnp_graph(what, row, tags, host_custom_vars):
    pnpgraph_present = row[what + "_pnpgraph_present"]
    if pnpgraph_present == 1:
        return pnp_icon(row, what)


multisite_icons_and_actions['perfgraph'] = {
    'columns':         [ 'pnpgraph_present' ],
    'paint':           paint_pnp_graph,
    'toplevel':        True,
    'sort_index':      20,
}

#.
#   .--Prediction----------------------------------------------------------.
#   |            ____               _ _      _   _                         |
#   |           |  _ \ _ __ ___  __| (_) ___| |_(_) ___  _ __              |
#   |           | |_) | '__/ _ \/ _` | |/ __| __| |/ _ \| '_ \             |
#   |           |  __/| | |  __/ (_| | | (__| |_| | (_) | | | |            |
#   |           |_|   |_|  \___|\__,_|_|\___|\__|_|\___/|_| |_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# TODO: At least for interfaces we have 2 predictive values. But this icon
# only creates a link to the first one. Add multiple icons or add a navigation
# element to the prediction page.
def paint_prediction_icon(what, row, tags, host_custom_vars):
    if what == "service":
        parts = row[what + "_perf_data"].split()
        for p in parts:
            if p.startswith("predict_"):
                varname, value = p.split("=")
                dsname = varname[8:]
                sitename = row["site"]
                url_prefix = config.site(sitename)["url_prefix"]
                url = url_prefix + "check_mk/prediction_graph.py?" + html.urlencode_vars([
                    ( "host", row["host_name"] ),
                    ( "service", row["service_description"] ),
                    ( "dsname", dsname ) ])
                title = _("Analyse predictive monitoring for this service")
                return 'prediction', title, url

multisite_icons_and_actions['prediction'] = {
    'columns' : [ 'perf_data' ],
    'paint'   : paint_prediction_icon,
}

#.
#   .--Action-URL----------------------------------------------------------.
#   |           _        _   _                   _   _ ____  _             |
#   |          / \   ___| |_(_) ___  _ __       | | | |  _ \| |            |
#   |         / _ \ / __| __| |/ _ \| '_ \ _____| | | | |_) | |            |
#   |        / ___ \ (__| |_| | (_) | | | |_____| |_| |  _ <| |___         |
#   |       /_/   \_\___|\__|_|\___/|_| |_|      \___/|_| \_\_____|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_action(what, row, tags, host_custom_vars):
    if display_options.enabled(display_options.X):
        # action_url (only, if not a PNP-URL and pnp_graph is working!)
        action_url       = row[what + "_action_url_expanded"]
        pnpgraph_present = row[what + "_pnpgraph_present"]
        if action_url \
           and not ('/pnp4nagios/' in action_url and pnpgraph_present >= 0):
            return 'action', _('Custom Action'), action_url

multisite_icons_and_actions['custom_action'] = {
    'columns':         [ 'action_url_expanded', 'pnpgraph_present' ],
    'paint':           paint_action,
}

#.
#   .--Logwatch------------------------------------------------------------.
#   |            _                              _       _                  |
#   |           | |    ___   __ ___      ____ _| |_ ___| |__               |
#   |           | |   / _ \ / _` \ \ /\ / / _` | __/ __| '_ \              |
#   |           | |__| (_) | (_| |\ V  V / (_| | || (__| | | |             |
#   |           |_____\___/ \__, | \_/\_/ \__,_|\__\___|_| |_|             |
#   |                       |___/                                          |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def logwatch_url(sitename, hostname, item):
    return html.makeuri_contextless([("site", sitename), ("host", hostname), ("file", item)], filename="logwatch.py")

def paint_logwatch(what, row, tags, host_custom_vars):
    if what != "service":
        return
    if row[what + "_check_command"] in [ 'check_mk-logwatch', 'check_mk-logwatch.groups' ]:
        return 'logwatch', _('Open Log'), logwatch_url(row["site"], row['host_name'], row['service_description'][4:])

multisite_icons_and_actions['logwatch'] = {
    'service_columns': [ 'host_name', 'service_description', 'check_command' ],
    'paint':           paint_logwatch,
}

#.
#   .--Notes-URL-----------------------------------------------------------.
#   |          _   _       _                  _   _ ____  _                |
#   |         | \ | | ___ | |_ ___  ___      | | | |  _ \| |               |
#   |         |  \| |/ _ \| __/ _ \/ __|_____| | | | |_) | |               |
#   |         | |\  | (_) | ||  __/\__ \_____| |_| |  _ <| |___            |
#   |         |_| \_|\___/ \__\___||___/      \___/|_| \_\_____|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Adds the url_prefix of the services site to the notes url configured in this site.
# It also adds the master_url which will be used to link back to the source site
# in multi site environments.
def paint_notes(what, row, tags, host_custom_vars):
    if display_options.enabled(display_options.X):
        notes_url = row[what + "_notes_url_expanded"]
        check_command = row[what + "_check_command"]
        if notes_url:
            return 'notes', _('Custom Notes'), notes_url

multisite_icons_and_actions['notes'] = {
    'columns':         [ 'notes_url_expanded', 'check_command' ],
    'paint':           paint_notes,
}

#.
#   .--Downtimes-----------------------------------------------------------.
#   |         ____                      _   _                              |
#   |        |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___          |
#   |        | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|         |
#   |        | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \         |
#   |        |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_downtimes(what, row, tags, host_custom_vars):
    # Currently we are in a downtime + link to list of downtimes
    # for this host / service
    if row[what + "_scheduled_downtime_depth"] > 0:
        if what == "host":
            icon = "derived_downtime"
        else:
            icon = "downtime"
        return icon, _("Currently in downtime"), url_to_view(row, 'downtimes_of_' + what)
    elif what == "service" and row["host_scheduled_downtime_depth"] > 0:
        return 'derived_downtime', _("The host is currently in downtime"), url_to_view(row, 'downtimes_of_host')

multisite_icons_and_actions['status_downtimes'] = {
    'host_columns':    [ 'scheduled_downtime_depth' ],
    'columns':         [ 'scheduled_downtime_depth' ],
    'paint':           paint_downtimes,
    'toplevel':        True,
}

#.
#   .--Comments------------------------------------------------------------.
#   |           ____                                     _                 |
#   |          / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___           |
#   |         | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|          |
#   |         | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \          |
#   |          \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_comment_icon(what, row, tags, host_custom_vars):
    comments = row[what + "_comments_with_extra_info"]
    if len(comments) > 0:
        text = ""
        for c in sorted(comments, key=lambda x: x[4]):
            id, author, comment, ty, timestamp = c
            comment = comment.replace("\n", "<br>")
            text += "%s %s: \"%s\" \n" % (paint_age(timestamp, True, 0, 'abs')[1], author, comment)
        return 'comment', text, url_to_view(row, 'comments_of_' + what)

multisite_icons_and_actions['status_comments'] = {
    'columns':         [ 'comments_with_extra_info' ],
    'paint':           paint_comment_icon,
    'toplevel':        True,
}

#.
#   .--Notifications-------------------------------------------------------.
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_notifications(what, row, tags, host_custom_vars):
    # Notifications disabled
    enabled = row[what + "_notifications_enabled"]
    modified = "notifications_enabled" in row[what + "_modified_attributes_list"]
    if modified and enabled:
        return 'notif_enabled', _('Notifications are manually enabled for this %s') % what
    elif modified and not enabled:
        return 'notif_man_disabled', _('Notifications are manually disabled for this %s') % what
    elif not enabled:
        return 'notif_disabled', _('Notifications are disabled for this %s') % what

multisite_icons_and_actions['status_notifications_enabled'] = {
    'columns':         [ 'modified_attributes_list', 'notifications_enabled' ],
    'paint':           paint_notifications,
    'toplevel':        True,
}

#.
#   .--Flapping------------------------------------------------------------.
#   |               _____ _                   _                            |
#   |              |  ___| | __ _ _ __  _ __ (_)_ __   __ _                |
#   |              | |_  | |/ _` | '_ \| '_ \| | '_ \ / _` |               |
#   |              |  _| | | (_| | |_) | |_) | | | | | (_| |               |
#   |              |_|   |_|\__,_| .__/| .__/|_|_| |_|\__, |               |
#   |                            |_|   |_|            |___/                |
#   '----------------------------------------------------------------------'

def paint_flapping(what, row, tags, host_custom_vars):
    if row[what + "_is_flapping"]:
        if what == "host":
            title = _("This host is flapping")
        else:
            title = _("This service is flapping")
        return 'flapping', title

multisite_icons_and_actions['status_flapping'] = {
    'columns':         [ 'is_flapping' ],
    'paint':           paint_flapping,
    'toplevel':        True,
}

#.
#   .--Staleness-----------------------------------------------------------.
#   |              ____  _        _                                        |
#   |             / ___|| |_ __ _| | ___ _ __   ___  ___ ___               |
#   |             \___ \| __/ _` | |/ _ \ '_ \ / _ \/ __/ __|              |
#   |              ___) | || (_| | |  __/ | | |  __/\__ \__ \              |
#   |             |____/ \__\__,_|_|\___|_| |_|\___||___/___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_is_stale_icon(what, row, tags, host_custom_vars):
    if is_stale(row):
        if what == "host":
            title = _("This host is stale")
        else:
            title = _("This service is stale")
        title += _(", no data has been received within the last %.1f check periods") % config.staleness_threshold
        return 'stale', title

multisite_icons_and_actions['status_stale'] = {
    'columns':         [ 'staleness' ],
    'paint':           paint_is_stale_icon,
    'toplevel':        True,
}

#.
#   .--Active-Checks-------------------------------------------------------.
#   |     _        _   _                  ____ _               _           |
#   |    / \   ___| |_(_)_   _____       / ___| |__   ___  ___| | _____    |
#   |   / _ \ / __| __| \ \ / / _ \_____| |   | '_ \ / _ \/ __| |/ / __|   |
#   |  / ___ \ (__| |_| |\ V /  __/_____| |___| | | |  __/ (__|   <\__ \   |
#   | /_/   \_\___|\__|_| \_/ \___|      \____|_| |_|\___|\___|_|\_\___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_active_checks(what, row, tags, host_custom_vars):
    # Setting of active checks modified by user
    if "active_checks_enabled" in row[what + "_modified_attributes_list"]:
        if row[what + "_active_checks_enabled"] == 0:
            return 'disabled', _('Active checks have been manually disabled for this %s!') % what
        else:
            return 'enabled', _('Active checks have been manually enabled for this %s!') % what

multisite_icons_and_actions['status_active_checks'] = {
    'columns':         [ 'modified_attributes_list', 'active_checks_enabled' ],
    'paint':           paint_active_checks,
    'toplevel':        True,
}

#.
#   .--Passiv-Checks-------------------------------------------------------.
#   |   ____               _             ____ _               _            |
#   |  |  _ \ __ _ ___ ___(_)_   __     / ___| |__   ___  ___| | _____     |
#   |  | |_) / _` / __/ __| \ \ / /____| |   | '_ \ / _ \/ __| |/ / __|    |
#   |  |  __/ (_| \__ \__ \ |\ V /_____| |___| | | |  __/ (__|   <\__ \    |
#   |  |_|   \__,_|___/___/_| \_/       \____|_| |_|\___|\___|_|\_\___/    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_passive_checks(what, row, tags, host_custom_vars):
    # Passive checks disabled manually?
    if "passive_checks_enabled" in row[what + "_modified_attributes_list"]:
        if row[what + "_accept_passive_checks"] == 0:
            return 'npassive', _('Passive checks have been manually disabled for this %s!') % what

multisite_icons_and_actions['status_passive_checks'] = {
    'columns':         [ 'modified_attributes_list', 'accept_passive_checks' ],
    'paint':           paint_passive_checks,
    'toplevel':        True,
}

#.
#   .--Notif.-Periods------------------------------------------------------.
#   |    _   _       _   _  __       ____           _           _          |
#   |   | \ | | ___ | |_(_)/ _|     |  _ \ ___ _ __(_) ___   __| |___      |
#   |   |  \| |/ _ \| __| | |_ _____| |_) / _ \ '__| |/ _ \ / _` / __|     |
#   |   | |\  | (_) | |_| |  _|_____|  __/  __/ |  | | (_) | (_| \__ \     |
#   |   |_| \_|\___/ \__|_|_|(_)    |_|   \___|_|  |_|\___/ \__,_|___/     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_notification_periods(what, row, tags, host_custom_vars):
    if not row[what + "_in_notification_period"]:
        return 'outofnot', _('Out of notification period')

multisite_icons_and_actions['status_notification_period'] = {
    'columns':         [ 'in_notification_period' ],
    'paint':           paint_notification_periods,
    'toplevel':        True,
}

#.
#   .--Service Period------------------------------------------------------.
#   |          ____                  _            ____                     |
#   |         / ___|  ___ _ ____   _(_) ___ ___  |  _ \ ___ _ __           |
#   |         \___ \ / _ \ '__\ \ / / |/ __/ _ \ | |_) / _ \ '__|          |
#   |          ___) |  __/ |   \ V /| | (_|  __/ |  __/  __/ | _           |
#   |         |____/ \___|_|    \_/ |_|\___\___| |_|   \___|_|(_)          |
#   |                                                                      |
#   '----------------------------------------------------------------------'
def paint_service_periods(what, row, tags, host_custom_vars):
    if not row[what + "_in_service_period"]:
        return 'outof_serviceperiod', _('Out of service period')

multisite_icons_and_actions['status_service_period'] = {
    'columns':         [ 'in_service_period' ],
    'paint':           paint_service_periods,
    'toplevel':        True,
}

#.
#   .--Aggregations--------------------------------------------------------.
#   |       _                                    _   _                     |
#   |      / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __  ___     |
#   |     / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \/ __|    |
#   |    / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | \__ \    |
#   |   /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|___/    |
#   |           |___/ |___/          |___/                                 |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Link to aggregations of the host/service
# When precompile on demand is enabled, this icon is displayed for all hosts/services
# otherwise only for the hosts/services which are part of aggregations.
def paint_aggregations(what, row, tags, host_custom_vars):
    if config.bi_precompile_on_demand \
       or bi.is_part_of_aggregation(what, row["site"], row["host_name"],
                                 row.get("service_description")):
        urivars = [
            ("view_name", "aggr_" + what),
            ("aggr_%s_site" % what, row["site"]),
            ("aggr_%s_host" % what, row["host_name"]),
        ]
        if what == "service":
            urivars += [
                ( "aggr_service_service", row["service_description"])
            ]
        url = html.makeuri_contextless(urivars, filename="view.py")
        return 'aggr', _("BI Aggregations containing this %s") % \
                            (what == "host" and _("Host") or _("Service")), url

multisite_icons_and_actions['aggregations'] = {
    'paint':           paint_aggregations,
}

#.
#   .--Stars *-------------------------------------------------------------.
#   |                   ____  _                                            |
#   |                  / ___|| |_ __ _ _ __ ___  __/\__                    |
#   |                  \___ \| __/ _` | '__/ __| \    /                    |
#   |                   ___) | || (_| | |  \__ \ /_  _\                    |
#   |                  |____/ \__\__,_|_|  |___/   \/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_stars(what, row, tags, host_custom_vars):
    stars = html.get_cached("stars")
    if stars is None:
        stars = set(config.user.load_file("favorites", []))
        html.set_cache("stars", stars)

    if what == "host":
        starred = row["host_name"] in stars
        title   = _("host")
    else:
        starred = (row["host_name"] + ";" + row["service_description"]) in stars
        title   = _("service")

    if starred:
        return 'starred', _("This %s is one of your favorites") % title

multisite_icons_and_actions['stars'] = {
    'columns': [],
    'paint': paint_stars,
}

#.
#   .--BI-Aggr.------------------------------------------------------------.
#   |                ____ ___        _                                     |
#   |               | __ )_ _|      / \   __ _  __ _ _ __                  |
#   |               |  _ \| |_____ / _ \ / _` |/ _` | '__|                 |
#   |               | |_) | |_____/ ___ \ (_| | (_| | | _                  |
#   |               |____/___|   /_/   \_\__, |\__, |_|(_)                 |
#   |                                    |___/ |___/                       |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_icon_check_bi_aggr(what, row, tags, host_custom_vars):
    if what == "service" and row.get("service_check_command","").startswith("check_mk_active-bi_aggr!"):
        args = row['service_check_command']
        start = args.find('-b \'') + 4
        end   = args.find('\' ', start)
        base_url = args[start:end].rstrip('/')
        base_url = base_url.replace('$HOSTADDRESS$', row['host_address'])
        base_url = base_url.replace('$HOSTNAME$', row['host_name'])

        start = args.find('-a \'') + 4
        end   = args.find('\' ', start)
        aggr_name = args[start:end]

        url = "%s/check_mk/view.py?view_name=aggr_single&aggr_name=%s" % \
              (base_url, html.urlencode(aggr_name))

        return 'aggr', _('Open this Aggregation'), url


multisite_icons_and_actions['aggregation_checks'] = {
    'host_columns' : [ 'check_command', 'name', 'address' ],
    'paint'        : paint_icon_check_bi_aggr,
}

#.
#   .--Crashdump-----------------------------------------------------------.
#   |         ____               _         _                               |
#   |        / ___|_ __ __ _ ___| |__   __| |_   _ _ __ ___  _ __          |
#   |       | |   | '__/ _` / __| '_ \ / _` | | | | '_ ` _ \| '_ \         |
#   |       | |___| | | (_| \__ \ | | | (_| | |_| | | | | | | |_) |        |
#   |        \____|_|  \__,_|___/_| |_|\__,_|\__,_|_| |_| |_| .__/         |
#   |                                                       |_|            |
#   +----------------------------------------------------------------------+
#   |  Icon for a crashed check with a link to the crash dump page.        |
#   '----------------------------------------------------------------------'

def paint_icon_crashed_check(what, row, tags, host_custom_vars):
    if what == "service" \
        and row["service_state"] == 3 \
        and "check failed - please submit a crash report!" in row["service_plugin_output"] :
        crashurl = html.makeuri([("site", row["site"]),
                                ("host", row["host_name"]),
                                ("service", row["service_description"])], filename="crashed_check.py")
        return 'crash', _("This check crashed. Please click here for more information. You also can submit "
                          "a crash report to the development team if you like."), crashurl

multisite_icons_and_actions['crashed_check'] = {
    'service_columns' : [ 'plugin_output', 'state', 'host_name' ],
    'paint'           : paint_icon_crashed_check,
    'toplevel'        : True,
}

#.
#   .--Check Period--------------------------------------------------------.
#   |       ____ _               _      ____           _           _       |
#   |      / ___| |__   ___  ___| | __ |  _ \ ___ _ __(_) ___   __| |      |
#   |     | |   | '_ \ / _ \/ __| |/ / | |_) / _ \ '__| |/ _ \ / _` |      |
#   |     | |___| | | |  __/ (__|   <  |  __/  __/ |  | | (_) | (_| |      |
#   |      \____|_| |_|\___|\___|_|\_\ |_|   \___|_|  |_|\___/ \__,_|      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Icon shown if the check is outside its check period                  |
#   '----------------------------------------------------------------------'


def paint_icon_check_period(what, row, tags, host_custom_vars):
    if what == "service":
        if row['%s_in_passive_check_period' % what] == 0\
                or row['%s_in_check_period' % what] == 0:
            return 'pause', _("This service is currently not being checked")


multisite_icons_and_actions['check_period'] = {
    'service_columns'  : ['in_passive_check_period', 'in_check_period'],
    'paint'    : paint_icon_check_period,
    'toplevel' : True,
}


#.
