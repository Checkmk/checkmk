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

import config, defaults, htmllib, pprint, time
from lib import *
import wato

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

loaded_with_language = False
builtin_dashboards = {}

# Declare constants to be used in the definitions of the dashboards
GROW = 0
MAX = -1

# These settings might go into the config module, sometime in future,
# in order to allow the user to customize this.

header_height   = 60             # Distance from top of the screen to the lower border of the heading
screen_margin   = 5              # Distance from the left border of the main-frame to the dashboard area
dashlet_padding = 21, 5, 5, 0 # Margin (N, E, S, W) between outer border of dashlet and its content
corner_overlap  = 22
title_height    = 0             # Height of dashlet title-box
raster          = 10, 10        # Raster the dashlet choords are measured in

# Load plugins in web/plugins/dashboard and declare permissions,
# note: these operations produce language-specific results and
# thus must be reinitialized everytime a language-change has
# been detected.
def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
        return

    # Permissions are currently not being defined. That will be the
    # case as soon as dashboards become editable.


    # Load plugins for dashboards. Currently these files
    # just may add custom dashboards by adding to builtin_dashboards.
    load_web_plugins("dashboard", globals())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language

    # In future there will be user editable dashboards just like
    # views which will be loaded. Currently we only use the builtin
    # dashboads.
    global dashboards
    dashboards = builtin_dashboards

# HTML page handler for generating the (a) dashboard. The name
# of the dashboard to render is given in the HTML variable 'name'.
# This defaults to "main".
def page_dashboard():
    name = html.var("name", "main")
    if name not in dashboards:
        raise MKGeneralException("No such dashboard: '<b>%s</b>'" % name)

    render_dashboard(name)

def add_wato_folder_to_url(url, wato_folder):
    if not wato_folder:
        return url
    elif '/' in url:
        return url # do not append wato_folder to non-Check_MK-urls
    elif '?' in url:
        return url + "&wato_folder=" + htmllib.urlencode(wato_folder)
    else:
        return url + "?wato_folder=" + htmllib.urlencode(wato_folder)


# Actual rendering function
def render_dashboard(name):
    board = dashboards[name]

    # The dashboard may be called with "wato_folder" set. In that case
    # the dashboard is assumed to restrict the shown data to a specific
    # WATO subfolder or file. This could be a configurable feature in
    # future, but currently we assume, that *all* dashboards are filename
    # sensitive.

    wato_folder = html.var("wato_folder")

    # When an empty wato_folder attribute is given a user really wants
    # to see only the hosts contained in the root folder. So don't ignore
    # the root folder anymore.
    #if not wato_folder: # ignore wato folder in case of root folder
    #    wato_folder = None

    # The title of the dashboard needs to be prefixed with the WATO path,
    # in order to make it clear to the user, that he is seeing only partial
    # data.
    title = board["title"]

    global header_height
    if title is None:
        # If the title is none, hide the header line
        html.set_render_headfoot(False)
        header_height = 0
        title = ''

    elif wato_folder is not None:
        title = wato.api.get_folder_title(wato_folder) + " - " + title

    html.header(title, javascripts=["dashboard"], stylesheets=["pages", "dashboard", "status", "views"])

    html.write("<div id=dashboard class=\"dashboard_%s\">\n" % name) # Container of all dashlets

    refresh_dashlets = [] # Dashlets with automatic refresh, for Javascript
    for nr, dashlet in enumerate(board["dashlets"]):
        # dashlets using the 'urlfunc' method will dynamically compute
        # an url (using HTML context variables at their wish).
        if "urlfunc" in dashlet:
            dashlet["url"] = dashlet["urlfunc"]()

        # dashlets using the 'url' method will be refreshed by us. Those
        # dashlets using static content (such as an iframe) will not be
        # refreshed by us but need to do that themselves.
        if "url" in dashlet:
            refresh_dashlets.append([nr, dashlet.get("refresh", 0),
              str(add_wato_folder_to_url(dashlet["url"], wato_folder))])

        # Paint the dashlet's HTML code
        render_dashlet(nr, dashlet, wato_folder)

    html.write("</div>\n")

    # Put list of all autorefresh-dashlets into Javascript and also make sure,
    # that the dashbaord is painted initially. The resize handler will make sure
    # that every time the user resizes the browser window the layout will be re-computed
    # and all dashlets resized to their new positions and sizes.
    html.javascript("""
var header_height = %d;
var screen_margin = %d;
var title_height = %d;
var dashlet_padding = Array%s;
var corner_overlap = %d;
var refresh_dashlets = %r;
var dashboard_name = '%s';
set_dashboard_size();
window.onresize = function () { set_dashboard_size(); }
window.onload = function () { set_dashboard_size(); }
dashboard_scheduler(1);
    """ % (header_height, screen_margin, title_height, dashlet_padding,
           corner_overlap, refresh_dashlets, name))

    html.body_end() # omit regular footer with status icons, etc.

# Create the HTML code for one dashlet. Each dashlet has an id "dashlet_%d",
# where %d is its index (in board["dashlets"]). Javascript uses that id
# for the resizing. Within that div there is an inner div containing the
# actual dashlet content. The margin between the inner and outer div is
# used for stylish layout stuff (shadows, etc.)
def render_dashlet(nr, dashlet, wato_folder):

    html.write('<div class=dashlet id="dashlet_%d">' % nr)
    # render shadow
    if dashlet.get("shadow", True):
        for p in [ "nw", "ne", "sw", "se", "n", "s", "w", "e" ]:
            html.write('<img id="dashadow_%s_%d" class="shadow %s" src="images/dashadow-%s.png">' %
                (p, nr, p, p))

    if dashlet.get("title"):
        url = dashlet.get("title_url", None)
        if url:
            title = '<a href="%s">%s</a>' % (url, dashlet["title"])
        else:
            title = dashlet["title"]
        html.write('<div class="title" id="dashlet_title_%d">%s</div>' % (nr, title))
    if dashlet.get("background", True):
        bg = " background"
    else:
        bg = ""
    html.write('<div class="dashlet_inner%s" id="dashlet_inner_%d">' % (bg, nr))

    # Optional way to render a dynamic iframe URL
    if "iframefunc" in dashlet:
        dashlet["iframe"] = dashlet["iframefunc"]()

    # The method "view" is a shortcut for "iframe" with a certain url
    if "view" in dashlet:
        dashlet["iframe"] = "view.py?view_name=%s&_display_options=HRSIXL&_body_class=dashlet" % dashlet["view"]

    # The content is rendered only if it is fixed. In the
    # other cases the initial (re)-size will paint the content.
    if "content" in dashlet: # fixed content
        html.write(dashlet["content"])
    elif "iframe" in dashlet: # fixed content containing iframe
        # Fix of iPad >:-P
        html.write('<div style="width: 100%; height: 100%; -webkit-overflow-scrolling:touch; overflow: auto;">')
        html.write('<iframe allowTransparency="true" frameborder="0" width="100%%" height="100%%" src="%s"></iframe>' %
           add_wato_folder_to_url(dashlet["iframe"], wato_folder))
        html.write('</div>')
    html.write("</div></div>\n")

# Here comes the brain stuff: An intelligent liquid layout algorithm.
# It is called via ajax, mainly because I was not eager to code this
# directly in Javascript (though this would be possible and probably
# more lean.)
# Compute position and size of all dashlets
def ajax_resize():
    # computation with vectors
    class vec:
        def __init__(self, xy):
            self._data = xy

        def __div__(self, xy):
            return vec((self._data[0] / xy[0], self._data[1] / xy[1]))

        def __repr__(self):
            return repr(self._data)

        def __getitem__(self, i):
            return self._data[i]

        def make_absolute(self, size):
            n = []
            for i in [0, 1]:
                if self._data[i] < 0:
                    n.append(size[i] + self._data[i] + 1) # Here was a bug fixed by Markus Lengler
                else:
                    n.append(self._data[i] - 1) # make begin from 0
            return vec(n)

        # Compute the initial size of the dashlet. If MAX is used,
        # then the dashlet consumes all space in its growing direction,
        # regardless of any other dashlets.
        def initial_size(self, position, rastersize):
            n = []
            for i in [0, 1]:
                if self._data[i] == MAX:
                    n.append(rastersize[i] - abs(position[i]) + 1)
                elif self._data[i] == GROW:
                    n.append(1)
                else:
                    n.append(self._data[i])
            return n

        def compute_grow_by(self, size):
            n = []
            for i in [0, 1]:
                if size[i] != GROW: # absolute size, no growth
                    n.append(0)
                elif self._data[i] < 0:
                    n.append(-1) # grow direction left, up
                else:
                    n.append(1) # grow direction right, down
            return n

        def __add__(self, b):
            return vec((self[0] + b[0], self[1] + b[1]))

    board = dashboards[html.var("name")]

    screensize = vec((int(html.var("width")), int(html.var("height"))))
    rastersize = screensize / raster
    used_matrix = {} # keep track of used raster elements

    # first place all dashlets at their absolute positions
    positions = []
    for nr, dashlet in enumerate(board["dashlets"]):
        # Relative position is as noted in the declaration. 1,1 => top left origin,
        # -1,-1 => bottom right origin, 0 is not allowed here
        rel_position = vec(dashlet["position"]) # starting from 1, negative means: from right/bottom

        # Compute the absolute position, this time from 0 to rastersize-1
        abs_position = rel_position.make_absolute(rastersize)

        # The size in raster-elements. A 0 for a dimension means growth. No negative values here.
        size = vec(dashlet["size"])

        # Compute the minimum used size for the dashlet. For growth-dimensions we start with 1
        used_size = size.initial_size(rel_position, rastersize)

        # Now compute the rectangle that is currently occupied. The choords
        # of bottomright are *not* included.
        if rel_position[0] > 0:
            left = abs_position[0]
            right = left + used_size[0]
        else:
            right = abs_position[0]
            left = right - used_size[0]

        if rel_position[1] > 0:
            top = abs_position[1]
            bottom = top + used_size[1]
        else:
            bottom = abs_position[1]
            top = bottom - used_size[1]

        # Allocate used squares in matrix. If not all squares we need are free,
        # then the dashboard is too small for all dashlets (as it seems).
        # TEST: Dashlet auf 0/0 setzen, wenn kein Platz dafür da ist.
        try:
            for x in range(left, right):
                for y in range(top, bottom):
                    if (x,y) in used_matrix:
                        raise Exception()
                    used_matrix[(x,y)] = True
            # Helper variable for how to grow, both x and y in [-1, 0, 1]
            grow_by = rel_position.compute_grow_by(size)

            positions.append((nr, True, left, top, right, bottom, grow_by))
        except:
            positions.append((nr, False, left, top, right, bottom, (0,0)))


    # now resize all elastic dashlets to the max, but only
    # by one raster at a time, in order to be fair
    def try_resize(x, y, width, height):
        return False
        if x + width >= xmax or y + height >= ymax:
            return False
        for xx in range(x, x + width):
            for yy in range(y, y + height):
                if used_matrix[xx][yy]:
                    return False
        for xx in range(x, x + width):
            for yy in range(y, y + height):
                used_matrix[xx][yy] = True
        return True

        # Das hier ist FALSCH! In Wirklichkeit muss ich nur prüfen,
        # ob der *Zuwachs* nicht in der Matrix belegt ist. Das jetzige
        # Rechteck muss ich ausklammern. Es ist ja schon belegt.

    def try_allocate(left, top, right, bottom):
        # Try if all needed squares are free
        for x in range(left, right):
            for y in range(top, bottom):
                if (x,y) in used_matrix:
                    return False

        # Allocate all needed squares
        for x in range(left, right):
            for y in range(top, bottom):
                used_matrix[(x,y)] = True
        return True


    # Now try to expand all elastic rectangles as far as possible
    at_least_one_expanded = True
    while at_least_one_expanded:
        at_least_one_expanded = False
        new_positions = []
        for (nr, visible, left, top, right, bottom, grow_by) in positions:
            if visible:
                # html.write(repr((nr, left, top, right, bottom, grow_by)))
                # try to grow in X direction by one
                if grow_by[0] > 0 and right < rastersize[0] and try_allocate(right, top, right+1, bottom):
                    at_least_one_expanded = True
                    right += 1
                elif grow_by[0] < 0 and left > 0 and try_allocate(left-1, top, left, bottom):
                    at_least_one_expanded = True
                    left -= 1

                # try to grow in Y direction by one
                if grow_by[1] > 0 and bottom < rastersize[1] and try_allocate(left, bottom, right, bottom+1):
                    at_least_one_expanded = True
                    bottom += 1
                elif grow_by[1] < 0 and top > 0 and try_allocate(left, top-1, right, top):
                    at_least_one_expanded = True
                    top -= 1
            new_positions.append((nr, visible, left, top, right, bottom, grow_by))
        positions = new_positions

    resize_info = []
    for nr, visible, left, top, right, bottom, grow_by in positions:
        # html.write(repr((nr, left, top, right, bottom, grow_by)))
        # html.write("<br>")
        title = board["dashlets"][nr].get("title")
        if title:
            th = title_height
        else:
            th = 0
        resize_info.append([nr,
                            visible and 1 or 0,
                            left * raster[0],
                            top * raster[1] + th,
                            (right - left) * raster[0],
                            (bottom - top) * raster[1] - th])

    html.write(repr(resize_info))


def dashlet_overview():
    html.write(
        '<table class=dashlet_overview>'
        '<tr><td valign=top>'
        '<a href="http://mathias-kettner.de/check_mk.html"><img style="margin-right: 30px;" src="images/check_mk.trans.120.png"></a>'
        '</td>'
        '<td><h2>Check_MK Multisite</h2>'
        'Welcome to Check_MK Multisite. If you want to learn more about Multsite, please visit '
        'our <a href="http://mathias-kettner.de/checkmk_multisite.html">online documentation</a>. '
        'Multisite is part of <a href="http://mathias-kettner.de/check_mk.html">Check_MK</a> - an Open Source '
        'project by <a href="http://mathias-kettner.de">Mathias Kettner</a>.'
        '</td>'
    )

    html.write('</tr></table>')

def dashlet_mk_logo():
    html.write('<a href="http://mathias-kettner.de/check_mk.html">'
     '<img style="margin-right: 30px;" src="images/check_mk.trans.120.png"></a>')



def dashlet_hoststats():
    table = [
       ( _("Up"), "#0b3",
        "searchhost&is_host_scheduled_downtime_depth=0&hst0=on",
        "Stats: state = 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "StatsAnd: 2\n"),

       ( _("Down"), "#f00",
        "searchhost&is_host_scheduled_downtime_depth=0&hst1=on",
        "Stats: state = 1\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "StatsAnd: 2\n"),

       ( _("Unreachable"), "#f80",
        "searchhost&is_host_scheduled_downtime_depth=0&hst2=on",
        "Stats: state = 2\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "StatsAnd: 2\n"),

       ( _("In Downtime"), "#0af",
        "searchhost&search=1&is_host_scheduled_downtime_depth=1",
        "Stats: scheduled_downtime_depth > 0\n" \
       )
    ]
    filter = "Filter: custom_variable_names < _REALNAME\n"

    render_statistics("hoststats", "hosts", table, filter)

def dashlet_servicestats():
    table = [
       ( _("OK"), "#0b3",
        "searchsvc&hst0=on&st0=on&is_in_downtime=0",
        "Stats: state = 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: host_state = 0\n" \
        "Stats: host_has_been_checked = 1\n" \
        "StatsAnd: 5\n"),

       ( _("In Downtime"), "#0af",
        "searchsvc&is_in_downtime=1",
        "Stats: scheduled_downtime_depth > 0\n" \
        "Stats: host_scheduled_downtime_depth > 0\n" \
        "StatsOr: 2\n"),

       ( _("On Down host"), "#048",
        "searchsvc&hst1=on&hst2=on&hstp=on&is_in_downtime=0",
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: host_state != 0\n" \
        "StatsAnd: 3\n"),

       ( _("Warning"), "#ff0",
        "searchsvc&hst0=on&st1=on&is_in_downtime=0",
        "Stats: state = 1\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: host_state = 0\n" \
        "Stats: host_has_been_checked = 1\n" \
        "StatsAnd: 5\n"),

       ( _("Unknown"), "#f80",
        "searchsvc&hst0=on&st3=on&is_in_downtime=0",
        "Stats: state = 3\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: host_state = 0\n" \
        "Stats: host_has_been_checked = 1\n" \
        "StatsAnd: 5\n"),

       ( _("Critical"), "#f00",
        "searchsvc&hst0=on&st2=on&is_in_downtime=0",
        "Stats: state = 2\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: host_state = 0\n" \
        "Stats: host_has_been_checked = 1\n" \
        "StatsAnd: 5\n"),
    ]
    filter = "Filter: host_custom_variable_names < _REALNAME\n"

    render_statistics("servicestats", "services", table, filter)


def render_statistics(pie_id, what, table, filter):
    html.write("<div class=stats>")
    pie_diameter     = 130
    pie_left_aspect  = 0.5
    pie_right_aspect = 0.8

    # Is the query restricted to a certain WATO-path?
    wato_folder = html.var("wato_folder")
    if wato_folder:
        # filter += "Filter: host_state = 0"
        filter += "Filter: host_filename ~ ^/wato/%s/\n" % wato_folder.replace("\n", "")

    # Is the query restricted to a host contact group?
    host_contact_group = html.var("host_contact_group")
    if host_contact_group:
        filter += "Filter: host_contact_groups >= %s\n" % host_contact_group.replace("\n", "")

    # Is the query restricted to a service contact group?
    service_contact_group = html.var("service_contact_group")
    if service_contact_group:
        filter += "Filter: service_contact_groups >= %s\n" % service_contact_group.replace("\n", "")

    query = "GET %s\n" % what
    for entry in table:
        query += entry[3]
    query += filter

    result = html.live.query_summed_stats(query)
    pies = zip(table, result)
    total = sum([x[1] for x in pies])

    html.write('<canvas class=pie width=%d height=%d id="%s_stats" style="float: left"></canvas>' %
            (pie_diameter, pie_diameter, pie_id))
    html.write('<img src="images/globe.png" class="globe">')

    html.write('<table class="hoststats%s" style="float:left">' % (
        len(pies) > 1 and " narrow" or ""))
    table_entries = pies
    while len(table_entries) < 6:
        table_entries = table_entries + [ (("", "#95BBCD", "", ""), "&nbsp;") ]
    table_entries.append(((_("Total"), "", "all%s" % what, ""), total))
    for (name, color, viewurl, query), count in table_entries:
        url = "view.py?view_name=" + viewurl + "&filled_in=filter&search=1&wato_folder=" \
              + htmllib.urlencode(html.var("wato_folder", ""))
        if host_contact_group:
            url += '&opthost_contactgroup=' + host_contact_group
        if service_contact_group:
            url += '&optservice_contactgroup=' + service_contact_group
        html.write('<tr><th><a href="%s">%s</a></th>' % (url, name))
        style = ''
        if color:
            style = ' style="background-color: %s"' % color
        html.write('<td class=color%s>'
                   '</td><td><a href="%s">%s</a></td></tr>' % (style, url, count))

    html.write("</table>")

    r = 0.0
    pie_parts = []
    if total > 0:
        # Count number of non-empty classes
        num_nonzero = 0
        for info, value in pies:
            if value > 0:
                num_nonzero += 1

        # Each non-zero class gets at least a view pixels of visible thickness.
        # We reserve that space right now. All computations are done in percent
        # of the radius.
        separator = 0.02                                    # 3% of radius
        remaining_separatorspace = num_nonzero * separator  # space for separators
        remaining_radius = 1 - remaining_separatorspace     # remaining space
        remaining_part = 1.0 # keep track of remaining part, 1.0 = 100%

        # Loop over classes, begin with most outer sphere. Inner spheres show
        # worse states and appear larger to the user (which is the reason we
        # are doing all this stuff in the first place)
        for (name, color, viewurl, q), value in pies[::1]:
            if value > 0 and remaining_part > 0: # skip empty classes

                # compute radius of this sphere *including all inner spheres!* The first
                # sphere always gets a radius of 1.0, of course.
                radius = remaining_separatorspace + remaining_radius * (remaining_part ** (1/3.0))
                pie_parts.append('chart_pie("%s", %f, %f, %r, true);' % (pie_id, pie_right_aspect, radius, color))
                pie_parts.append('chart_pie("%s", %f, %f, %r, false);' % (pie_id, pie_left_aspect, radius, color))

                # compute relative part of this class
                part = float(value) / total # ranges from 0 to 1
                remaining_part           -= part
                remaining_separatorspace -= separator


    html.write("</div>")
    html.javascript("""
function chart_pie(pie_id, x_scale, radius, color, right_side) {
    var context = document.getElementById(pie_id + "_stats").getContext('2d');
    if (!context)
        return;
    var pie_x = %(x)f;
    var pie_y = %(y)f;
    var pie_d = %(d)f;
    context.fillStyle = color;
    context.save();
    context.translate(pie_x, pie_y);
    context.scale(x_scale, 1);
    context.beginPath();
    if(right_side)
        context.arc(0, 0, (pie_d / 2) * radius, 1.5 * Math.PI, 0.5 * Math.PI, false);
    else
        context.arc(0, 0, (pie_d / 2) * radius, 0.5 * Math.PI, 1.5 * Math.PI, false);
    context.closePath();
    context.fill();
    context.restore();
    context = null;
}


if (has_canvas_support()) {
    %(p)s
}
""" % { "x" : pie_diameter / 2, "y": pie_diameter/2, "d" : pie_diameter, 'p': '\n'.join(pie_parts) })

def dashlet_pnpgraph():
    render_pnpgraph(
        html.var("site"), html.var("host"), html.var("service"),
        int(html.var("source", 0)), int(html.var("view", 0)),
    )

def dashlet_nodata():
    html.write("<div class=nograph><div class=msg>")
    html.write(html.var("message", _("No data available.")))
    html.write("</div></div>")

def render_pnpgraph(site, host, service = None, source = 0, view = 0):
    if not host:
        html.message("Invalid URL to this dashlet. Missing <tt>host</tt>")
        return;
    if not service:
        service = "_HOST_"

    if not site:
        base_url = defaults.url_prefix
    else:
        base_url = html.site_status[site]["site"]["url_prefix"]
    base_url += "pnp4nagios/index.php/"
    var_part = "?host=%s&srv=%s&view=0&source=%d&view=%d&theme=multisite&_t=%d" % \
            (pnp_cleanup(host), pnp_cleanup(service), source, view, int(time.time()))

    pnp_url = base_url + "graph" + var_part
    img_url = base_url + "image" + var_part
    html.write('<a href="%s"><img border=0 src="%s"></a>' % (pnp_url, img_url))

# load_plugins()
