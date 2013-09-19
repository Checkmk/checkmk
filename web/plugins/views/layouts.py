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

def init_rowselect(view):
    # Don't make rows selectable when no commands can be fired
    # Ignore "C" display option here. Otherwise the rows will not be selectable
    # after view reload.
    if not config.may("general.act"):
        return

    selected = weblib.get_rowselection('view-' + view['name'])
    html.javascript(
        'g_page_id = "view-%s";\n'
        'g_selection = "%s";\n'
        'g_selected_rows = %s;\n'
        'init_rowselect();' % (view['name'], weblib.selection_id(), repr(selected))
    )

def render_checkbox(view, row, num_tds):
    # value contains the number of columns of this datarow. This is
    # needed for hiliting the correct number of TDs
    html.write("<input type=checkbox name=\"%s\" value=%d />" %
                                    (row_id(view, row), num_tds + 1))

def render_checkbox_td(view, row, num_tds):
    html.write("<td class=checkbox>")
    render_checkbox(view, row, num_tds)
    html.write("</td>")

def render_group_checkbox_th():
    html.write("<th><input type=button class=checkgroup name=_toggle_group"
               " onclick=\"toggle_group_rows(this);\" value=\"%s\" /></th>" % _('X'))

# -------------------------------------------------------------------------
#    ____  _             _
#   / ___|(_)_ __   __ _| | ___
#   \___ \| | '_ \ / _` | |/ _ \
#    ___) | | | | | (_| | |  __/
#   |____/|_|_| |_|\__, |_|\___|
#                  |___/
# -------------------------------------------------------------------------
def render_single_dataset(rows, view, group_painters, painters, num_columns, _ignore_show_checkboxes):
    for row in rows:
        register_events(row) # needed for playing sounds

    html.write('<table class="data single">\n')
    rownum = 0
    odd = "odd"
    while rownum < len(rows):
        if rownum > 0:
            html.write("<tr class=gap><td class=gap colspan=%d></td></tr>\n" % (1 + num_columns))
        thispart = rows[rownum:rownum + num_columns]
        for p in painters:
            painter, link = p[0:2]
            if len(p) >= 5 and p[4]:
                title = p[4] # Use custom title
            elif len(p) == 4 and p[3]:
                title = p[3] # Use the join index (service name) as title
            else:
                title = painter["title"]

            odd = odd == "odd" and "even" or "odd"
            html.write('<tr class="data %s0">' % odd)
            if view.get("column_headers") != "off":
                html.write("<td class=left>%s</td>" % title)
            for row in thispart:
                paint(p, row)
            if len(thispart) < num_columns:
                html.write("<td class=gap style=\"border-style: none;\" colspan=%d></td>" % (1 + num_columns - len(thispart)))
            html.write("</tr>\n")
        rownum += num_columns
    html.write("</table>\n")
    html.write("</div>\n")

multisite_layouts["dataset"] = {
    "title"  : _("Single dataset"),
    "render" : render_single_dataset,
    "group"  : False,
    "checkboxes" : False,
}

# -------------------------------------------------------------------------
#    ____                    _
#   | __ )  _____  _____  __| |
#   |  _ \ / _ \ \/ / _ \/ _` |
#   | |_) | (_) >  <  __/ (_| |
#   |____/ \___/_/\_\___|\__,_|
#
# -------------------------------------------------------------------------
def render_grouped_boxes(rows, view, group_painters, painters, num_columns, show_checkboxes):

    repeat_heading_every = 20 # in case column_headers is "repeat"

    # N columns. Each should contain approx the same number of entries
    groups = []
    last_group = None
    for row in rows:
        register_events(row) # needed for playing sounds
        this_group = group_value(row, group_painters)
        if this_group != last_group:
            last_group = this_group
            current_group = []
            groups.append((this_group, current_group))
        current_group.append((row_id(view, row), row))

    def height_of(groups):
        # compute total space needed. I count the group header like two rows.
        return sum([ len(rows) for header, rows in groups ]) + 2 * len(groups)

    # Create empty columns
    columns = [ ]
    for x in range(0, num_columns):
        columns.append([])

    # First put everything into the first column
    for group in groups:
        columns[0].append(group)

    # shift from src to dst, if usefull
    def balance(src, dst):
        if len(src) == 0:
            return False
        hsrc = height_of(src)
        hdst = height_of(dst)
        shift = len(src[-1][1]) + 2
        if max(hsrc, hdst) > max(hsrc - shift, hdst + shift):
            dst[0:0] = [ src[-1] ]
            del src[-1]
            return True
        return False

    # Shift from left to right as long as useful
    did_something = True
    while did_something:
        did_something = False
        for i in range(0, num_columns - 1):
            if balance(columns[i], columns[i+1]):
                did_something = True


    # render one group
    def render_group(header, rows):
        html.write("<table class=groupheader cellspacing=0 cellpadding=0 border=0><tr class=groupheader>")
        painted = False
        for p in group_painters:
            if painted:
                html.write("<td>,</td>")
            painted = paint(p, rows[0][1])
        html.write("</tr></table>\n")

        html.write("<table class=data>")
        trclass = None

        def show_header_line():
            html.write("<tr>")
            if show_checkboxes:
                render_group_checkbox_th()
            for p in painters:
                paint_header(view, p)
                html.write("\n")
            html.write("</tr>\n")

        column_headers = view.get("column_headers")
        if column_headers:
            show_header_line()

        visible_row_number = 0
        for index, row in rows:
            if view.get("column_headers") == "repeat":
                if visible_row_number > 0 and visible_row_number % repeat_heading_every == 0:
                    show_header_line()
            visible_row_number += 1

            register_events(row) # needed for playing sounds
            if trclass == "odd":
                trclass = "even"
            else:
                trclass = "odd"
            # state = row.get("service_state", row.get("aggr_state"))
            state = row.get("service_state")
            if state == None:
                state = saveint(row.get("host_state", 0))
                if state > 0: state +=1 # 1 is critical for hosts
            html.write('<tr class="data %s%d">' % (trclass, state))
            if show_checkboxes:
                render_checkbox_td(view, row, len(painters))
            for p in painters:
                paint(p, row)
            html.write("</tr>\n")

        html.write("</table>\n")
        init_rowselect(view)

    # render table
    html.write("<table class=boxlayout><tr>")
    for column in columns:
        html.write("<td class=boxcolumn>")
        for header, rows in column:
            render_group(header, rows)
        html.write("</td>")
    html.write("</tr></table>\n")

multisite_layouts["boxed"] = {
    "title"  : _("Balanced boxes"),
    "render" : render_grouped_boxes,
    "group"  : True,
    "checkboxes" : True,
}

# -------------------------------------------------------------------------
#    _____ _ _          _
#   |_   _(_) | ___  __| |
#     | | | | |/ _ \/ _` |
#     | | | | |  __/ (_| |
#     |_| |_|_|\___|\__,_|
#
# -------------------------------------------------------------------------
def render_tiled(rows, view, group_painters, painters, _ignore_num_columns, show_checkboxes):
    html.write("<table class=\"data tiled\">\n")

    last_group = None
    group_open = False
    for row in rows:
        # Show group header
        if len(group_painters) > 0:
            this_group = group_value(row, group_painters)
            if this_group != last_group:

                # paint group header
                if group_open:
                    html.write("</td></tr>\n")
                html.write("<tr><td><table class=groupheader><tr class=groupheader>")
                painted = False
                for p in group_painters:
                    if painted:
                        html.write("<td>,</td>")
                    painted = paint(p, row)

                html.write('</tr></table></td></tr>'
                           '<tr><td class=tiles>\n')
                group_open = True
                last_group = this_group


        # background color of tile according to item state
        state = row.get("service_state", -1)
        if state == -1:
            hbc = row.get("host_has_been_checked", 1)
            if hbc:
                state = row.get("host_state", 0)
                sclass = "hhstate%d" % state
            else:
                sclass = "hhstatep"
        else:
            hbc = row.get("service_has_been_checked", 1)
            if hbc:
                sclass = "sstate%d" % state
            else:
                sclass = "sstatep"

        if not group_open:
            html.write("<tr><td class=tiles>")
            group_open = True
        html.write('<div class="tile %s"><table>' % sclass)

        # We need at least five painters.
        empty_painter = { "paint" : (lambda row: ("", "")) }

        if len(painters) < 5:
            painters = painters + ([ (empty_painter, None) ] * (5 - len(painters)))

        rendered = [ prepare_paint(p, row) for p in painters ]

        html.write("<tr><td class=\"tl %s\">" % (rendered[1][0],))
        if show_checkboxes:
            render_checkbox(view, row, len(painters)-1)
        html.write("%s</td><td class=\"tr %s\">%s</td></tr>\n" % \
                    (rendered[1][1], rendered[2][0], rendered[2][1]))
        html.write("<tr><td colspan=2 class=\"center %s\">%s</td></tr>\n" % \
                    (rendered[0][0], rendered[0][1]))
        for css, cont in rendered[5:]:
            html.write("<tr><td colspan=2 class=\"cont %s\">%s</td></tr>\n" % \
                        (css, cont))
        html.write("<tr><td class=\"bl %s\">%s</td><td class=\"br %s\">%s</td></tr>\n" % \
                    (rendered[3][0], rendered[3][1], rendered[4][0], rendered[4][1]))
        html.write("</table></div>\n")
    if group_open:
        html.write("</td></tr>\n")
    html.write("</table>\n")
    init_rowselect(view)


multisite_layouts["tiled"] = {
    "title"  : _("Tiles"),
    "render" : render_tiled,
    "group"  : True,
    "checkboxes" : True,
}

# -------------------------------------------------------------------------
#    _____     _     _
#   |_   _|_ _| |__ | | ___
#     | |/ _` | '_ \| |/ _ \
#     | | (_| | |_) | |  __/
#     |_|\__,_|_.__/|_|\___|
#
# ------------------------------------------------------------------------
def render_grouped_list(rows, view, group_painters, painters, num_columns, show_checkboxes):

    repeat_heading_every = 20 # in case column_headers is "repeat"

    html.write("<table class='data table'>\n")
    last_group = None
    odd = "even"
    column = 1
    group_open = False
    num_painters = len(painters)
    if show_checkboxes:
        num_painters += 1

    def show_header_line():
        html.write("<tr>")
        for n in range(1, num_columns + 1):
            if show_checkboxes:
                if n == 1:
                    render_group_checkbox_th()
                else:
                    html.write('<th></th>')

            for p in painters:
                paint_header(view, p)
            if n < num_columns:
                html.write('<td class=gap></td>')

        html.write("</tr>\n")

    if len(group_painters) == 0 and view.get("column_headers") != "off":
        show_header_line()

    # Helper function that counts the number of entries in
    # the current group
    def count_group_members(row, rows):
        this_group = group_value(row, group_painters)
        members = 1
        for row in rows[1:]:
            that_group = group_value(row, group_painters)
            if that_group == this_group:
                members += 1
            else:
                break
        return members


    index = 0
    visible_row_number = 0
    for row in rows:
        register_events(row) # needed for playing sounds
        # Show group header, if a new group begins. But only if grouping
        # is activated
        if len(group_painters) > 0:
            this_group = group_value(row, group_painters)
            if this_group != last_group:
                if column != 1: # not a the beginning of a new line
                    for i in range(column-1, num_columns):
                        html.write('<td class=gap></td>')
                        html.write("<td class=fillup colspan=%d></td>" % num_painters)
                    html.write("</tr>\n")
                    column = 1

                group_open = True
                visible_row_number = 0

                # paint group header, but only if it is non-empty
                header_is_empty = True
                for p in group_painters:
                    tdclass, content = prepare_paint(p, row)
                    if content:
                        header_is_empty = False
                        break

                if not header_is_empty:
                    html.write("<tr class=groupheader>")
                    html.write("<td class=groupheader colspan=%d><table class=groupheader cellspacing=0 cellpadding=0 border=0><tr>" %
                         (num_painters * (num_columns + 2) + (num_columns - 1)))
                    painted = False
                    for p in group_painters:
                        if painted:
                            html.write("<td>,</td>")
                        painted = paint(p, row)

                    html.write("</tr></table></td></tr>\n")

                # Table headers
                if view.get("column_headers") != "off":
                    show_header_line()
                trclass = "even"
                last_group = this_group

        # Should we wrap over to a new line?
        if column >= num_columns + 1:
            html.write("</tr>\n")
            column = 1

        # At the beginning of the line? Beginn new line
        if column == 1:
            if view.get("column_headers") == "repeat":
                if visible_row_number > 0 and visible_row_number % repeat_heading_every == 0:
                    show_header_line()
            visible_row_number += 1

            # In one-column layout we use the state of the service
            # or host - if available - to color the complete line
            if num_columns == 1:
                # render state, if available through whole tr
                if row.get('service_description', '') == '':
                    state = row.get("host_state", 0)
                    if state > 0: state +=1 # 1 is critical for hosts
                else:
                    state = row.get("service_state", 0)
            else:
                state = 0

            odd = odd == "odd" and "even" or "odd"
            html.write('<tr class="data %s %s%d">' % (num_columns > 1 and "multicolumn" or "", odd, state))

        # Not first columns: Create one empty column as separator
        else:
            html.write('<td class=gap></td>')


        if show_checkboxes:
            render_checkbox_td(view, row, num_painters)

        for p in painters:
            paint(p, row)

        column += 1
        index += 1

    if group_open:
        for i in range(column-1, num_columns):
            html.write('<td class=gap></td>')
            html.write("<td class=fillup colspan=%d></td>" % num_painters)
        html.write("</tr>\n")
    html.write("</table>\n")
    init_rowselect(view)

multisite_layouts["table"] = {
    "title"  : _("Table"),
    "render" : render_grouped_list,
    "group"  : True,
    "checkboxes" : True,
}

