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
#   |         ___                  ___                                     |
#   |        |_ _|___ ___  _ __   |_ _|_ __ ___   __ _  __ _  ___          |
#   |         | |/ __/ _ \| '_ \   | || '_ ` _ \ / _` |/ _` |/ _ \         |
#   |         | | (_| (_) | | | |  | || | | | | | (_| | (_| |  __/         |
#   |        |___\___\___/|_| |_| |___|_| |_| |_|\__,_|\__, |\___|         |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+

def paint_icon_image(what, row, tags, custom_vars):
    if row[what + '_icon_image']:
        return '<img class=icon src="images/icons/%s">' % row[what + '_icon_image']

multisite_icons.append({
    'columns':         [ 'icon_image' ],
    'paint':           paint_icon_image,
})


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
        txt         = _('Reschedule an immediate check of this %s') % _(what)

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
               '<img class=icon title="%s" src="images/%s.gif" /></a>' % \
                (row["site"], row["host_name"], htmllib.urlencode(servicedesc), htmllib.urlencode(wait_svc), txt, icon)

multisite_icons.append({
    'columns':         [ 'active_checks_enabled' ],
    'paint':           paint_reschedule,
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
        return '<img class=icon title="' + _('This problem has been acknowledged') \
             + '" src="images/icon_ack.gif">'

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
        return link_to_view("<img class=icon title='" + _("Detailed host infos")
                          + "' src='images/icon_detail.gif'>", newrow, 'host')

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
            (how, htmllib.urlencode(host), htmllib.urlencode(svc)))
    else:
        url = site["url_prefix"] + ("pnp4nagios/index.php/%s?host=%s&srv=%s" % \
            (how, htmllib.urlencode(host), htmllib.urlencode(svc)))

    if how == 'graph':
        url += "&theme=multisite&baseurl=%scheck_mk/" % \
                        htmllib.urlencode(site["url_prefix"])
    return url

def pnp_popup_url(row, what):
    return pnp_url(row, what, 'popup')

def pnp_icon(row, what):
    if 'X' in html.display_options:
        url = pnp_url(row, what)
    else:
        url = ""
    return '<a href="%s" onmouseover="displayHoverMenu(event, pnp_hover_contents(\'%s\'))" ' \
           'onmouseout="hoverHide()"><img class=icon src="images/icon_pnp.png"></a>' % \
                                                        (url, pnp_popup_url(row, what))

def paint_pnp_graph(what, row, tags, custom_vars):
    pnpgraph_present = row[what + "_pnpgraph_present"]
    if pnpgraph_present == 1:
        return pnp_icon(row, what)

multisite_icons.append({
    'columns':         [ 'pnpgraph_present' ],
    'paint':           paint_pnp_graph,
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
            return '<a href="%s"><img class=icon ' \
                   'src="images/icon_action.gif"></a>' % action_url

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

# Adds the url_prefix of the services site to the notes url configured in this site.
# It also adds the master_url which will be used to link back to the source site
# in multi site environments.
def logwatch_url(sitename, notes_url):
    i = notes_url.index("check_mk/logwatch.py")
    site = html.site_status[sitename]["site"]

    master_url = ''
    if config.is_multisite():
        master_url = '&master_url=' + defaults.url_prefix + 'check_mk/'

    return site["url_prefix"] + notes_url[i:] + master_url

def paint_notes(what, row, tags, custom_vars):
    if 'X' in html.display_options:
        # notes_url (only, if not a Check_MK logwatch check pointing to
        # logwatch.py. These is done by a special icon)
        notes_url = row[what + "_notes_url_expanded"]
        check_command = row[what + "_check_command"]
        if notes_url:
            # unmodified original logwatch link
            # -> translate into more intelligent icon
            if check_command == 'check_mk-logwatch' \
               and "/check_mk/logwatch.py" in notes_url:
                return '<a href="%s"><img class=icon ' \
                       'src="images/icon_logwatch.png\"></a>' % \
                           logwatch_url(row["site"], notes_url)
            else:
                return '<a href="%s"><img class=icon ' \
                       'src="images/icon_notes.gif"></a>' % notes_url

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
        return link_to_view('<img class=icon title="%s" src="images/icon_%s.png">' %
        (_("Currently in downtime"), icon), row, 'downtimes_of_' + what)
    elif what == "service" and row["host_scheduled_downtime_depth"] > 0:
        return link_to_view('<img class=icon title="%s" src="images/icon_hostdowntime.png">' %
        _("The host is currently in downtime"), row, 'downtimes_of_host')



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
    comments = row[what+ "_comments_with_extra_info"]
    if len(comments) > 0:
        text = ""
        for c in comments:
            id, author, comment, ty, timestamp = c
            text += "%s %s: \"%s\" \n" % (paint_age(timestamp, True, 0, 'abs')[1], author, comment)
        return link_to_view('<img class=icon title=\'%s\' ' \
                            'src="images/icon_comment.gif">' %
                                 text, row, 'comments_of_' + what)

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
    if not row[what + "_notifications_enabled"]:
        return '<img class=icon title="%s" src="images/icon_ndisabled.gif">' % \
                         _('Notifications are disabled for this %s') % what

multisite_icons.append({
    'columns':         [ 'notifications_enabled' ],
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
        return '<img class=icon title="%s" src="images/icon_flapping.gif">' % title

multisite_icons.append({
    'columns':         [ 'is_flapping' ],
    'paint':           paint_flapping,
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
            return '<img class=icon title="%s" src="images/icon_disabled.gif">' % \
                    _('Active checks have been manually disabled for this %s!') % what
        else:
            return '<img class=icon title="%s" src="images/icon_enabled.gif">' % \
                     _('Active checks have been manually enabled for this %s!') % what


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
            return '<img class=icon title="%s" src="images/icon_npassive.gif">' % \
                    _('Passive checks have been manually disabled for this %s!') % what


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
        return '<img class=icon title="%s" src="images/icon_outofnot.gif">' % \
                                           _('Out of notification period')


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
         return link_to_view('<img class=icon src="images/icon_aggr.gif" title="%s">' %
                  _('Aggregations containing this %s') % what, row, 'aggr_' + what)

multisite_icons.append({
    'paint':           paint_aggregations,
})
