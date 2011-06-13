#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

import config, defaults, htmllib, pprint
from lib import *

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

loaded_with_language = False
builtin_dashboards = {}

screen_margin = 10
header_height = 40
raster        = 20, 20

# Load plugins in web/plugins/dashboard and declare permissions,
# note: these operations produce language-specific results and
# thus must be reinitialized everytime a language-change has
# been detected.
def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
        return
    loaded_with_language = current_language

    # Permissions are currently not being defined. That will be the
    # case as soon as dashboards become editable.


    # Load plugins for dashboards. Currently these files
    # just may add custom dashboards by adding to builtin_dashboards.
    load_web_plugins("dashboard", globals())

    # In future there will be user editable dashboards just like
    # views which will be loaded. Currently we only use the builtin
    # dashboads.
    global dashboards
    dashboards = builtin_dashboards

def page_dashboard():
    name = html.var("name", "main")
    if name not in dashboards:
        raise MKGeneralException("No such dashboard: '<b>%s</b>'" % name)

    # Currently 
    render_dashboard(name)

def render_dashboard(name):
    board = dashboards[name]

    html.header(board["title"])
    html.javascript_file("dashboard")
    html.write("<div id=dashboard>\n")

    refresh_dashlets = []
    for nr, dashlet in enumerate(board["dashlets"]):
        if "url" in dashlet:
            refresh_dashlets.append(["dashlet_%d" % nr, dashlet.get("refresh", 5), dashlet["url"]])
        render_dashlet(nr, dashlet)

    html.write("</div>\n")
    html.javascript("""
        refresh_dashlets = %r;
        dashboard_name = '%s';
        set_dashboard_size();
        window.onresize = function () { set_dashboard_size(); }
        dashboard_scheduler();
    """ % (refresh_dashlets, name))

    html.footer()

def render_dashlet(nr, dashlet):
    html.write('<div class=dashlet id="dashlet_%d">' % nr)
    if "content" in dashlet: # fixed content
        html.write(dashlet["content"])
        url = ""
    else:
        url = dashlet.get("url", "")
    html.write("</div>\n")

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
                    n.append(size[i] - self._data[i] - 1)
                else:
                    n.append(self._data[i] - 1) # make begin from 0
            return vec(n)

        def compute_grow_by(self, size):
            n = []
            for i in [0, 1]:
                if size[i] != 0: # absolute size, no growth
                    n.append(0)
                elif self._data[i] < 0:
                    n.append(-1) # grow direction left, up
                else:
                    n.append(1) # grow direction right, down
            return n

        def __add__(self, b):
            return vec((self[0] + b[0], self[1] + b[1]))

    board = dashboards[html.var("name")]

    screensize = vec((int(html.var("width")) - 2*screen_margin, int(html.var("height")) - 2*screen_margin - header_height))
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
        used_size = ( max(1, size[0]), max(1, size[1]) )

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

        # Allocate used squares in matrix
        for x in range(left, right):
            for y in range(top, bottom):
                used_matrix[(x,y)] = True

        # Helper variable for how to grow, both x and y in [-1, 0, 1]
        grow_by = rel_position.compute_grow_by(size) 

        positions.append((nr, left, top, right, bottom, grow_by))

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
        for (nr, left, top, right, bottom, grow_by) in positions:
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

            new_positions.append((nr, left, top, right, bottom, grow_by))
        positions = new_positions

    resize_info = []
    for nr, left, top, right, bottom, grow_by in positions:
        # html.write(repr((nr, left, top, right, bottom, grow_by)))
        # html.write("<br>")
        resize_info.append(["dashlet_%d" % nr, 
                            left * raster[0] + screen_margin,
                            top * raster[1] + header_height + screen_margin,
                            (right - left) * raster[0],
                            (bottom - top) * raster[1]])

    html.write(repr(resize_info))


    # UND DANN NOCH DIE iFrames einbauen für den Fall, dass es sich
    # um URLs handelt, und dann diese asynchron nachladen.

    # Und den Refresh-Scheduler anwerfen.


# Javascript:
# 1. Refresh: Der Scheduler refresht alle Dashlets automatisch, die
# eine URL haben und eine Refreshzeit > 0. Dazu wird dir URL vorab
# in der dashlet_info gespeichert.
# 
# 2. Resize: Wenn per Javascript ein resize festgestellt wird, dann
# müssen die Positionen und Größen von allen Dashlets berechnet werden.
# Dazu wird eine Axax-Funktion aufgerufen, welche eine JSON-Tabelle
# von allen Dashlets mit deren genauen Positionen liefert. Dieser
# Ajaxaufruf muss auch beim ersten malen gleich gestartet werden.
# Er heisst set_dashboard_size().
# 




