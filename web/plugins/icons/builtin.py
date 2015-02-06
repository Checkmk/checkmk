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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# An icon painter is a python function which gets four parameters and
# returns one string of rendered HTML code or None.
#
# The parameters are shown below:
#
#    def paint_icon_image(what, row, tags, custom_vars):
#        """
#        what:        The type of the current object
#        row:         The livestatus row for the current object
#        tags:        List of cmk tags for this object
#        custom_vars: Dict of objects custom variables
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


#   +----------------------------------------------------------------------+
#   |          ____                _              _       _                |
#   |         |  _ \ ___  ___  ___| |__   ___  __| |_   _| | ___           |
#   |         | |_) / _ \/ __|/ __| '_ \ / _ \/ _` | | | | |/ _ \          |
#   |         |  _ <  __/\__ \ (__| | | |  __/ (_| | |_| | |  __/          |
#   |         |_| \_\___||___/\___|_| |_|\___|\__,_|\__,_|_|\___|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_reschedule(what, row, tags, custom_vars):
    # Reschedule button
    if (row[what + "_active_checks_enabled"] == 1
        or row[what + '_check_command'].startswith('check_mk-')) \
       and config.may('action.reschedule'):

        servicedesc = ''
        wait_svc    = ''
        icon        = 'icon_reload'
        txt         = _('Reschedule an immediate check')

        if what == 'service':
            servicedesc = row['service_description'].replace("\\","\\\\")
            wait_svc = servicedesc

            # Use Check_MK service for cmk based services
            if row[what + '_check_command'].startswith('check_mk-'):
                servicedesc = 'Check_MK'
                icon        = 'icon_reload_cmk'
                txt         = _('Reschedule an immediate check of the \'Check_MK\' service')

        return '<a href=\"javascript:void(0);\" ' \
               'onclick="performAction(this, \'reschedule\', \'%s\', \'%s\', \'%s\', \'%s\');">' \
               '<img align=absmiddle class=icon title="%s" src="images/%s.gif" /></a>' % \
                (row["site"], row["host_name"], html.urlencode(servicedesc), html.urlencode(wait_svc), txt, icon)

multisite_icons.append({
    'columns':         [ 'active_checks_enabled' ],
    'paint':           paint_reschedule,
})


def paint_rule_editor(what, row, tags, custom_vars):
    if config.wato_enabled and config.may("wato.rulesets") and config.multisite_draw_ruleicon:
        urlvars = [("mode", "object_parameters"),
                   ("host", row["host_name"])]

        if what == 'service':
            urlvars.append(("service", row["service_description"]))
            title = _("View and edit parameters for this service")
        else:
            title = _("View and edit parameters for this host")

        return 'rulesets', html.makeuri_contextless(urlvars, "wato.py"), title

multisite_icons.append({
    'service_columns': [ 'description', 'check_command', "host_name" ],
    'paint':           paint_rule_editor,
})

#   +----------------------------------------------------------------------+
#   |       _        _                        _          _                 |
#   |      / \   ___| | ___ __   _____      _| | ___  __| | __ _  ___      |
#   |     / _ \ / __| |/ / '_ \ / _ \ \ /\ / / |/ _ \/ _` |/ _` |/ _ \     |
#   |    / ___ \ (__|   <| | | | (_) \ V  V /| |  __/ (_| | (_| |  __/     |
#   |   /_/   \_\___|_|\_\_| |_|\___/ \_/\_/ |_|\___|\__,_|\__, |\___|     |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+

def paint_ack_image(what, row, tags, custom_vars):
    if row[what + "_acknowledged"]:
        return html.render_icon('ack', _('This problem has been acknowledged'))

multisite_icons.append({
    'columns':         [ 'acknowledged' ],
    'paint':           paint_ack_image,
})

#   +----------------------------------------------------------------------+
#   |             ____            _       _   _           _                |
#   |            |  _ \ ___  __ _| |     | | | | ___  ___| |_              |
#   |            | |_) / _ \/ _` | |_____| |_| |/ _ \/ __| __|             |
#   |            |  _ <  __/ (_| | |_____|  _  | (_) \__ \ |_              |
#   |            |_| \_\___|\__,_|_|     |_| |_|\___/|___/\__|             |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_realhost_link_image(what, row, tags, custom_vars):
    # Link to detail host if this is a summary host
    if "_REALNAME" in custom_vars:
        newrow = row.copy()
        newrow["host_name"] = custom_vars["_REALNAME"]
        return link_to_view(html.render_icon('detail', _("Detailed host infos")), newrow, 'host')

multisite_icons.append({
    'paint':           paint_realhost_link_image,
})

#   +----------------------------------------------------------------------+
#   |         ____  _   _ ____        ____                 _               |
#   |        |  _ \| \ | |  _ \      / ___|_ __ __ _ _ __ | |__            |
#   |        | |_) |  \| | |_) |____| |  _| '__/ _` | '_ \| '_ \           |
#   |        |  __/| |\  |  __/_____| |_| | | | (_| | |_) | | | |          |
#   |        |_|   |_| \_|_|         \____|_|  \__,_| .__/|_| |_|          |
#   |                                               |_|                    |
#   +----------------------------------------------------------------------+

# Intelligent Links to PNP4Nagios 0.6.X
def pnp_url(row, what, how = 'graph'):
    sitename = row["site"]
    host = pnp_cleanup(row["host_name"])
    if what == "host":
        svc = "_HOST_"
    else:
        svc = pnp_cleanup(row["service_description"])
    site = html.site_status[sitename]["site"]
    if html.mobile:
        url = site["url_prefix"] + ("pnp4nagios/index.php?kohana_uri=/mobile/%s/%s/%s" % \
            (how, html.urlencode(host), html.urlencode(svc)))
    else:
        url = site["url_prefix"] + ("pnp4nagios/index.php/%s?host=%s&srv=%s" % \
            (how, html.urlencode(host), html.urlencode(svc)))

    if how == 'graph':
        url += "&theme=multisite&baseurl=%scheck_mk/" % \
                        html.urlencode(site["url_prefix"])
    return url

def pnp_popup_url(row, what):
    return pnp_url(row, what, 'popup')

def pnp_icon(row, what):
    if 'X' in html.display_options:
        url = pnp_url(row, what)
    else:
        url = ""
    return '<a href="%s" onmouseover="displayHoverMenu(event, pnp_hover_contents(\'%s\'))" ' \
           'onmouseout="hoverHide()">%s</a>' % (url, pnp_popup_url(row, what), html.render_icon('pnp', ''))

def paint_pnp_graph(what, row, tags, custom_vars):
    pnpgraph_present = row[what + "_pnpgraph_present"]
    if pnpgraph_present == 1:
        return pnp_icon(row, what)

multisite_icons.append({
    'columns':         [ 'pnpgraph_present' ],
    'paint':           paint_pnp_graph,
})

#   +----------------------------------------------------------------------+
#   |            ____               _ _      _   _                         |
#   |           |  _ \ _ __ ___  __| (_) ___| |_(_) ___  _ __              |
#   |           | |_) | '__/ _ \/ _` | |/ __| __| |/ _ \| '_ \             |
#   |           |  __/| | |  __/ (_| | | (__| |_| | (_) | | | |            |
#   |           |_|   |_|  \___|\__,_|_|\___|\__|_|\___/|_| |_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
def paint_prediction_icon(what, row, tags, custom_vars):
    if what == "service":
        parts = row[what + "_perf_data"].split()
        for p in parts:
            if p.startswith("predict_"):
                varname, value = p.split("=")
                dsname = varname[8:]
                sitename = row["site"]
                site = html.site_status[sitename]["site"]
                url = site["url_prefix"] + "check_mk/prediction_graph.py?" + html.urlencode_vars([
                    ( "host", row["host_name"] ),
                    ( "service", row["service_description"] ),
                    ( "dsname", dsname ) ])
                title = _("Analyse predictive monitoring for this service")
                return '<a href="%s">%s</a>' % (url, html.render_icon('prediction', title))

multisite_icons.append({
    'columns' : [ 'perf_data' ],
    'paint'   : paint_prediction_icon,
})


#   +----------------------------------------------------------------------+
#   |           _        _   _                   _   _ ____  _             |
#   |          / \   ___| |_(_) ___  _ __       | | | |  _ \| |            |
#   |         / _ \ / __| __| |/ _ \| '_ \ _____| | | | |_) | |            |
#   |        / ___ \ (__| |_| | (_) | | | |_____| |_| |  _ <| |___         |
#   |       /_/   \_\___|\__|_|\___/|_| |_|      \___/|_| \_\_____|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_action(what, row, tags, custom_vars):
    if 'X' in html.display_options:
        # action_url (only, if not a PNP-URL and pnp_graph is working!)
        action_url       = row[what + "_action_url_expanded"]
        pnpgraph_present = row[what + "_pnpgraph_present"]
        if action_url \
           and not ('/pnp4nagios/' in action_url and pnpgraph_present >= 0):
            return '<a href="%s">%s</a>' % (action_url, html.render_icon('action', _('Custom Action')))

multisite_icons.append({
    'columns':         [ 'action_url_expanded', 'pnpgraph_present' ],
    'paint':           paint_action,
})

#
#   +----------------------------------------------------------------------+
#   |          _   _       _                  _   _ ____  _                |
#   |         | \ | | ___ | |_ ___  ___      | | | |  _ \| |               |
#   |         |  \| |/ _ \| __/ _ \/ __|_____| | | | |_) | |               |
#   |         | |\  | (_) | ||  __/\__ \_____| |_| |  _ <| |___            |
#   |         |_| \_|\___/ \__\___||___/      \___/|_| \_\_____|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def logwatch_url(sitename, hostname, item):
    host_item_url = "check_mk/logwatch.py?host=%s&file=%s" % (html.urlencode(hostname), html.urlencode(item))
    site = html.site_status[sitename]["site"]
    master_url = ''
    if config.is_multisite():
        master_url = '&master_url=' + defaults.url_prefix + 'check_mk/'

    return site["url_prefix"] + host_item_url + master_url

def paint_logwatch(what, row, tags, custom_vars):
    if what != "service":
        return
    if row[what + "_check_command"] in [ 'check_mk-logwatch', 'check_mk-logwatch.groups' ]:
        return '<a href="%s">%s</a>' % (logwatch_url(row["site"], row['host_name'], row['service_description'][4:]),
                                        html.render_icon('logwatch', _('Open Log')))

multisite_icons.append({
    'service_columns': [ 'host_name', 'service_description', 'check_command' ],
    'paint':           paint_logwatch,
})


# Adds the url_prefix of the services site to the notes url configured in this site.
# It also adds the master_url which will be used to link back to the source site
# in multi site environments.
def paint_notes(what, row, tags, custom_vars):
    if 'X' in html.display_options:
        notes_url = row[what + "_notes_url_expanded"]
        check_command = row[what + "_check_command"]
        if check_command == 'check_mk-logwatch' and \
            "check_mk/logwatch.py?host" in notes_url:
            return
        if notes_url:
            return '<a href="%s">%s</a>' % (notes_url, html.render_icon('notes', _('Custom Notes')))

multisite_icons.append({
    'columns':         [ 'notes_url_expanded', 'check_command' ],
    'paint':           paint_notes,
})

#   +----------------------------------------------------------------------+
#   |         ____                      _   _                              |
#   |        |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___          |
#   |        | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|         |
#   |        | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \         |
#   |        |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_downtimes(what, row, tags, custom_vars):
    # Currently we are in a downtime + link to list of downtimes
    # for this host / service
    if row[what + "_scheduled_downtime_depth"] > 0:
        if what == "host":
            icon = "hostdowntime"
        else:
            icon = "downtime"
        return link_to_view(html.render_icon(icon, _("Currently in downtime")),
                            row, 'downtimes_of_' + what)
    elif what == "service" and row["host_scheduled_downtime_depth"] > 0:
        return link_to_view(html.render_icon('hostdowntime', _("The host is currently in downtime")),
                            row, 'downtimes_of_host')

multisite_icons.append({
    'host_columns':    [ 'scheduled_downtime_depth' ],
    'columns':         [ 'scheduled_downtime_depth' ],
    'paint':           paint_downtimes,
})

#   +----------------------------------------------------------------------+
#   |           ____                                     _                 |
#   |          / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___           |
#   |         | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|          |
#   |         | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \          |
#   |          \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_comments(what, row, tags, custom_vars):
    comments = row[what + "_comments_with_extra_info"]
    if len(comments) > 0:
        text = ""
        for c in comments:
            id, author, comment, ty, timestamp = c
            comment = comment.replace("\n", "<br>").replace("'","&#39;")
            text += "%s %s: \"%s\" \n" % (paint_age(timestamp, True, 0, 'abs')[1], author, comment)
        return link_to_view(html.render_icon('comment', text), row, 'comments_of_' + what)

multisite_icons.append({
    'columns':         [ 'comments_with_extra_info' ],
    'paint':           paint_comments,
})

#   +----------------------------------------------------------------------+
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_notifications(what, row, tags, custom_vars):
    # Notifications disabled
    enabled = row[what + "_notifications_enabled"]
    modified = "notifications_enabled" in row[what + "_modified_attributes_list"]
    if modified and enabled:
        return html.render_icon('notif_enabled',
                _('Notifications are manually enabled for this %s') % what)
    elif modified and not enabled:
        return html.render_icon('notif_man_disabled',
                _('Notifications are manually disabled for this %s') % what)
    elif not enabled:
        return html.render_icon('notif_disabled',
                _('Notifications are disabled for this %s') % what)


multisite_icons.append({
    'columns':         [ 'modified_attributes_list', 'notifications_enabled' ],
    'paint':           paint_notifications,
})

#   +----------------------------------------------------------------------+
#   |               _____ _                   _                            |
#   |              |  ___| | __ _ _ __  _ __ (_)_ __   __ _                |
#   |              | |_  | |/ _` | '_ \| '_ \| | '_ \ / _` |               |
#   |              |  _| | | (_| | |_) | |_) | | | | | (_| |               |
#   |              |_|   |_|\__,_| .__/| .__/|_|_| |_|\__, |               |
#   |                            |_|   |_|            |___/                |
#   +----------------------------------------------------------------------+

def paint_flapping(what, row, tags, custom_vars):
    if row[what + "_is_flapping"]:
        if what == "host":
            title = _("This host is flapping")
        else:
            title = _("This service is flapping")
        return html.render_icon('flapping', title)

multisite_icons.append({
    'columns':         [ 'is_flapping' ],
    'paint':           paint_flapping,
})

#.
#   .--Staleness-----------------------------------------------------------.
#   |              ____  _        _                                        |
#   |             / ___|| |_ __ _| | ___ _ __   ___  ___ ___               |
#   |             \___ \| __/ _` | |/ _ \ '_ \ / _ \/ __/ __|              |
#   |              ___) | || (_| | |  __/ | | |  __/\__ \__ \              |
#   |             |____/ \__\__,_|_|\___|_| |_|\___||___/___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_is_stale(what, row, tags, custom_vars):
    if is_stale(row):
        if what == "host":
            title = _("This host is stale")
        else:
            title = _("This service is stale")
        title += _(", no data has been received within the last %.1f check periods") % config.staleness_threshold
        return html.render_icon('stale', title)

multisite_icons.append({
    'columns':         [ 'staleness' ],
    'paint':           paint_is_stale,
})

#   +----------------------------------------------------------------------+
#   |     _        _   _                  ____ _               _           |
#   |    / \   ___| |_(_)_   _____       / ___| |__   ___  ___| | _____    |
#   |   / _ \ / __| __| \ \ / / _ \_____| |   | '_ \ / _ \/ __| |/ / __|   |
#   |  / ___ \ (__| |_| |\ V /  __/_____| |___| | | |  __/ (__|   <\__ \   |
#   | /_/   \_\___|\__|_| \_/ \___|      \____|_| |_|\___|\___|_|\_\___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_active_checks(what, row, tags, custom_vars):
    # Setting of active checks modified by user
    if "active_checks_enabled" in row[what + "_modified_attributes_list"]:
        if row[what + "_active_checks_enabled"] == 0:
            return html.render_icon('disabled', _('Active checks have been manually disabled for this %s!') % what)
        else:
            return html.render_icon('enabled', _('Active checks have been manually enabled for this %s!') % what)

multisite_icons.append({
    'columns':         [ 'modified_attributes_list', 'active_checks_enabled' ],
    'paint':           paint_active_checks,
})

#   +----------------------------------------------------------------------+
#   |   ____               _             ____ _               _            |
#   |  |  _ \ __ _ ___ ___(_)_   __     / ___| |__   ___  ___| | _____     |
#   |  | |_) / _` / __/ __| \ \ / /____| |   | '_ \ / _ \/ __| |/ / __|    |
#   |  |  __/ (_| \__ \__ \ |\ V /_____| |___| | | |  __/ (__|   <\__ \    |
#   |  |_|   \__,_|___/___/_| \_/       \____|_| |_|\___|\___|_|\_\___/    |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_passive_checks(what, row, tags, custom_vars):
    # Passive checks disabled manually?
    if "passive_checks_enabled" in row[what + "_modified_attributes_list"]:
        if row[what + "_accept_passive_checks"] == 0:
            return html.render_icon('npassive', _('Passive checks have been manually disabled for this %s!') % what)

multisite_icons.append({
    'columns':         [ 'modified_attributes_list', 'accept_passive_checks' ],
    'paint':           paint_passive_checks,
})

#   +----------------------------------------------------------------------+
#   |    _   _       _   _  __       ____           _           _          |
#   |   | \ | | ___ | |_(_)/ _|     |  _ \ ___ _ __(_) ___   __| |___      |
#   |   |  \| |/ _ \| __| | |_ _____| |_) / _ \ '__| |/ _ \ / _` / __|     |
#   |   | |\  | (_) | |_| |  _|_____|  __/  __/ |  | | (_) | (_| \__ \     |
#   |   |_| \_|\___/ \__|_|_|(_)    |_|   \___|_|  |_|\___/ \__,_|___/     |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def paint_notification_periods(what, row, tags, custom_vars):
    if not row[what + "_in_notification_period"]:
        return html.render_icon('outofnot', _('Out of notification period'))

multisite_icons.append({
    'columns':         [ 'in_notification_period' ],
    'paint':           paint_notification_periods,
})

#   +----------------------------------------------------------------------+
#   |       _                                    _   _                     |
#   |      / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __  ___     |
#   |     / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \/ __|    |
#   |    / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | \__ \    |
#   |   /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|___/    |
#   |           |___/ |___/          |___/                                 |
#   +----------------------------------------------------------------------+

# Link to aggregations of the host/service
# When precompile on demand is enabled, this icon is displayed for all hosts/services
# otherwise only for the hosts/services which are part of aggregations.
def paint_aggregations(what, row, tags, custom_vars):
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
        url = html.makeuri_contextless(urivars)
        return '<a href="%s">%s</a>' % (url, html.render_icon('aggr',
                _("BI Aggregations containing this %s") % (what == "host" and _("Host") or _("Service"))))


multisite_icons.append({
    'paint':           paint_aggregations,
})

#.
#   .--Stars *-------------------------------------------------------------.
#   |                   ____  _                                            |
#   |                  / ___|| |_ __ _ _ __ ___  __/\__                    |
#   |                  \___ \| __/ _` | '__/ __| \    /                    |
#   |                   ___) | || (_| | |  \__ \ /_  _\                    |
#   |                  |____/ \__\__,_|_|  |___/   \/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def paint_stars(what, row, tags, custom_vars):
    try:
        stars = html.stars
    except:
        stars = set(config.load_user_file("favorites", []))
        html.stars = stars

    if what == "host":
        starred = row["host_name"] in stars
    else:
        starred = (row["host_name"] + ";" + row["service_description"]) in stars
    if starred:
        return html.render_icon('starred', _("This %s is one of your favorites") % _(what))

multisite_icons.append({
    'columns': [],
    'paint': paint_stars,
})

def paint_icon_check_bi_aggr(what, row, tags, custom_vars):
    if what == "service" and row.get("service_check_command","").startswith("check_mk_active-bi_aggr!"):
        args = row['service_check_command']
        start = args.find('-b \'') + 4
        end   = args.find('\' ', start)
        base_url = args[start:end]
        base_url = base_url.replace('$HOSTADDRESS$', row['host_address'])
        base_url = base_url.replace('$HOSTNAME$', row['host_name'])

        start = args.find('-a \'') + 4
        end   = args.find('\' ', start)
        aggr_name = args[start:end]

        url = "%s/check_mk/view.py?view_name=aggr_single&aggr_name=%s" % \
              (base_url, html.urlencode(aggr_name))

        return '<a href="%s">%s</a>' % (html.attrencode(url), html.render_icon('aggr', _('Open this Aggregation')))


multisite_icons.append({
    'host_columns' : [ 'check_command', 'name', 'address' ],
    'paint'        : paint_icon_check_bi_aggr,
})

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

def paint_icon_crashed_check(what, row, tags, custom_vars):
    if what == "service" \
        and row["service_state"] == 3 \
        and "check failed - please submit a crash report!" in row["service_plugin_output"] :
        crashurl = html.makeuri([("site", row["site"]), ("host", row["host_name"]), ("service", row["service_description"])], filename="crashed_check.py")
        return '<a href="%s">%s</a>' % (
            crashurl, html.render_icon('crash',
            _("This check crashed. Please click here for more information. You also can submit "
              "a crash report to the development team if you like.")))

multisite_icons.append({
    'service_columns' : [ 'plugin_output', 'state', 'host_name' ],
    'paint'   : paint_icon_crashed_check,
})

#.
#   .--Type Icons----------------------------------------------------------.
#   |           _____                   ___                                |
#   |          |_   _|   _ _ __   ___  |_ _|___ ___  _ __  ___             |
#   |            | || | | | '_ \ / _ \  | |/ __/ _ \| '_ \/ __|            |
#   |            | || |_| | |_) |  __/  | | (_| (_) | | | \__ \            |
#   |            |_| \__, | .__/ \___| |___\___\___/|_| |_|___/            |
#   |                |___/|_|                                              |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def paint_icon_image(what, row, tags, custom_vars):
    if row[what + '_icon_image']:
        return row[what + '_icon_image'][:-4]

# When an icon image is defined for a host/service, this is always used
# as type image for this object in advanced to the other (auto detected)
# type icons
multisite_icons.append({
    'columns' : [ 'icon_image' ],
    'paint'   : paint_icon_image,
    'type'    : 'type_icon',
})

def paint_basic_service_types(what, row, tags, custom_vars):
    if what == "service":
        svc_desc = row["service_description"]
        if svc_desc.startswith('Check_MK'):
            return 'checkmk'
        elif svc_desc.startswith('Memory'):
            return 'memory'
        elif svc_desc.startswith('CPU'):
            return 'cpu'
        elif svc_desc.startswith('Filesystem'):
            return 'filesystem'
        elif svc_desc.startswith('Mount options'):
            return 'mount'
        elif svc_desc.startswith('Interface'):
            return 'interface'
        elif svc_desc.startswith('Log'):
            return 'log'
        elif svc_desc.startswith('Temperature'):
            return 'temperature'
        elif svc_desc.startswith('CUPS'):
            return 'printer'
        elif svc_desc.startswith('Disk IO'):
            return 'disk_io'
        elif svc_desc.startswith('Uptime'):
            return 'uptime'
        elif svc_desc.startswith('Kernel'):
            return 'kernel'
        elif svc_desc.startswith('Events'):
            return 'events'
        elif svc_desc.startswith('TCP Connections'):
            return 'connections'
        elif svc_desc.startswith('Postfix'):
            return 'mail_queue'
        elif svc_desc.startswith('Job'):
            return 'job'
        elif svc_desc.startswith('NTP') or svc_desc == 'System Time':
            return 'time'

multisite_icons.append({
    'paint' : paint_basic_service_types,
    'type'  : 'type_icon',
})

def paint_basic_host_types(what, row, tags, custom_vars):
    if what == "host":
        services = dict([ (s[0], s[1:]) for s in row['host_services_with_info'] ])

        if 'CPU load' in services and 'Kernel Context Switches' in services:
            return 'linux'

        elif 'Pages' in services and 'SNMP Info' in services:
            return 'printer'

        elif 'SNMP Info' in services and 'Cisco IOS' in services['SNMP Info'][2]:
            return 'cisco'

        for service in services.keys():
            if service.startswith('Filesystem C:'):
                return 'windows'

multisite_icons.append({
    'host_columns' : ['services_with_info'],
    'paint'        : paint_basic_host_types,
    'type'         : 'type_icon',
})
