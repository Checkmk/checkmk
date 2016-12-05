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

#.
#   .--Dataset-------------------------------------------------------------.
#   |                  ____        _                 _                     |
#   |                 |  _ \  __ _| |_ __ _ ___  ___| |_                   |
#   |                 | | | |/ _` | __/ _` / __|/ _ \ __|                  |
#   |                 | |_| | (_| | || (_| \__ \  __/ |_                   |
#   |                 |____/ \__,_|\__\__,_|___/\___|\__|                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Layout designed for showing one single dataset with the column      |
#   |  headers left and the values on the right. It is able to handle      |
#   |  more than on dataset however.
#   '----------------------------------------------------------------------'
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



#.
#   .--Boxed---------------------------------------------------------------.
#   |                      ____                    _                       |
#   |                     | __ )  _____  _____  __| |                      |
#   |                     |  _ \ / _ \ \/ / _ \/ _` |                      |
#   |                     | |_) | (_) >  <  __/ (_| |                      |
#   |                     |____/ \___/_/\_\___|\__,_|                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  The boxed layout is useful in views with a width > 1, boxes are     |
#   |  stacked in columns and can have different sizes.                    |
#   '----------------------------------------------------------------------'
def render_grouped_boxes(rows, view, group_painters, painters, num_columns, show_checkboxes, css_class=None):

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
        if column_headers != "off":
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
            state = saveint(row.get("service_state"))
            if state == None:
                state = saveint(row.get("host_state", 0))
                if state > 0: state +=1 # 1 is critical for hosts
            stale = ''
            if is_stale(row):
                stale = ' stale'
            html.write('<tr class="data %s%d%s">' % (trclass, state, stale))
            if show_checkboxes:
                render_checkbox_td(view, row, len(painters))
            for p in painters:
                paint(p, row)
            html.write("</tr>\n")

        html.write("</table>\n")
        init_rowselect(view)

    # render table
    html.write("<table class=\"boxlayout%s\"><tr>" % (css_class and " "+css_class or ""))
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

#.
#   .--Graph Boxes---------------------------------------------------------.
#   |        ____                 _       ____                             |
#   |       / ___|_ __ __ _ _ __ | |__   | __ )  _____  _____  ___         |
#   |      | |  _| '__/ _` | '_ \| '_ \  |  _ \ / _ \ \/ / _ \/ __|        |
#   |      | |_| | | | (_| | |_) | | | | | |_) | (_) >  <  __/\__ \        |
#   |       \____|_|  \__,_| .__/|_| |_| |____/ \___/_/\_\___||___/        |
#   |                      |_|                                             |
#   +----------------------------------------------------------------------+
#   | Same as balanced boxes layout but adds a cs class graph to the box   |
#   '----------------------------------------------------------------------'


multisite_layouts["boxed_graph"] = {
    "title"      : _("Balanced graph boxes"),
    "render"     : lambda *args: render_grouped_boxes(*args + ("graph",)),
    "group"      : True,
    "checkboxes" : True,
}


#.
#   .--Tiled---------------------------------------------------------------.
#   |                        _____ _ _          _                          |
#   |                       |_   _(_) | ___  __| |                         |
#   |                         | | | | |/ _ \/ _` |                         |
#   |                         | | | | |  __/ (_| |                         |
#   |                         |_| |_|_|\___|\__,_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  The tiled layout puts each dataset into one box with a fixed size.  |
#   '----------------------------------------------------------------------'

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


#.
#   .--Table---------------------------------------------------------------.
#   |                       _____     _     _                              |
#   |                      |_   _|_ _| |__ | | ___                         |
#   |                        | |/ _` | '_ \| |/ _ \                        |
#   |                        | | (_| | |_) | |  __/                        |
#   |                        |_|\__,_|_.__/|_|\___|                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Most common layout: render all datasets in one big table. Groups    |
#   |  are shown in what seems to be separate tables but they share the    |
#   |  width of the columns.                                               |
#   '----------------------------------------------------------------------'

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

            last_painter = painters[-1]
            for painter in painters:
                is_last_column_header = painter == last_painter
                paint_header(view, painter, is_last_column_header)

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
                if row.get('service_description', '') == '' or row.get("service_state") == None:
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

        last_painter = painters[-1]
        for painter in painters:
            paint(painter, row, is_last_painter=last_painter==painter)

        column += 1

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


#.
#   .--Matrix--------------------------------------------------------------.
#   |                    __  __       _        _                           |
#   |                   |  \/  | __ _| |_ _ __(_)_  __                     |
#   |                   | |\/| |/ _` | __| '__| \ \/ /                     |
#   |                   | |  | | (_| | |_| |  | |>  <                      |
#   |                   |_|  |_|\__,_|\__|_|  |_/_/\_\                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  The Matrix is similar to what is called "Mine Map" in other GUIs.   |
#   |  It create a matrix whose columns are single datasets and whole rows |
#   |  are entities with the same value in all those datasets. Typicall    |
#   |  The columns are hosts and the rows are services.                    |
#   '----------------------------------------------------------------------'

def render_matrix(rows, view, group_painters, painters, num_columns, _ignore_show_checkboxes):

    header_majorities = matrix_find_majorities(rows, group_painters, True)
    value_counts, row_majorities = matrix_find_majorities(rows, painters, False)

    for groups, unique_row_ids, matrix_cells in \
             create_matrices(rows, group_painters, painters, num_columns):

        # Paint the matrix. Begin with the group headers
        html.write('<table class="data matrix">')
        odd = "odd"
        for painter_nr, painter in enumerate(group_painters):
            odd = odd == "odd" and "even" or "odd"
            html.write('<tr class="data %s0">' % odd)
            html.write('<td class=matrixhead>%s</td>' % painter[0]["title"])
            for group, group_row in groups:
                tdclass, content = prepare_paint(painter, group_row)
                if painter_nr > 0:
                    gv = group_value(group_row, [painter])
                    majority_value = header_majorities.get(painter_nr-1, None)
                    if majority_value != None and majority_value != gv:
                        tdclass += " minority"
                html.write('<td class="left %s">%s</td>' % (tdclass, content))
            html.write("</tr>")

        # Now for each unique service^H^H^H^H^H^H ID column paint one row
        for row_id in unique_row_ids:
            # Omit rows where all cells have the same values
            if get_painter_option("matrix_omit_uniform"):
                at_least_one_different = False
                for counts in value_counts[row_id].values():
                    if len(counts) > 1:
                        at_least_one_different = True
                        break
                if not at_least_one_different:
                    continue

            odd = odd == "odd" and "even" or "odd"
            html.write('<tr class="data %s0">' % odd)
            tdclass, content = prepare_paint(painters[0], matrix_cells[row_id].values()[0])
            html.write('<td class="left %s">%s</td>' % (tdclass, content))

            # Now go through the groups and paint the rest of the
            # columns
            for group_id, group_row in groups:
                cell_row = matrix_cells[row_id].get(group_id)
                if cell_row == None:
                    html.write("<td></td>")
                else:
                    if len(painters) > 2:
                        html.write("<td class=cell><table>")
                    for painter_nr, p in enumerate(painters[1:]):
                        tdclass, content = prepare_paint(p, cell_row)
                        gv = group_value(cell_row, [p])
                        majority_value =  row_majorities[row_id].get(painter_nr, None)
                        if majority_value != None and majority_value != gv:
                            tdclass += " minority"
                        if len(painters) > 2:
                            html.write("<tr>")
                        html.write('<td class="%s">%s</td>' % (tdclass, content))
                        if len(painters) > 2:
                            html.write("</tr>")
                    if len(painters) > 2:
                        html.write("</table></td>")
            html.write('</tr>')

        html.write("</table>")


def csv_export_matrix(rows, view, group_painters, painters):
    output_csv_headers(view)

    groups, unique_row_ids, matrix_cells = list(create_matrices(rows, group_painters, painters, num_columns=None))[0]
    value_counts, row_majorities = matrix_find_majorities(rows, painters, False)

    table.begin(output_format="csv")
    for painter_nr, painter in enumerate(group_painters):
        table.row()
        table.cell("", painter[0]["title"])
        for group, group_row in groups:
            tdclass, content = prepare_paint(painter, group_row)
            table.cell("", content)

    for row_id in unique_row_ids:
        # Omit rows where all cells have the same values
        if get_painter_option("matrix_omit_uniform"):
            at_least_one_different = False
            for counts in value_counts[row_id].values():
                if len(counts) > 1:
                    at_least_one_different = True
                    break
            if not at_least_one_different:
                continue

        table.row()
        tdclass, content = prepare_paint(painters[0], matrix_cells[row_id].values()[0])
        table.cell("", content)

        for group_id, group_row in groups:
            table.cell("")
            cell_row = matrix_cells[row_id].get(group_id)
            if cell_row != None:
                for painter_nr, p in enumerate(painters[1:]):
                    tdclass, content = prepare_paint(p, cell_row)
                    if painter_nr:
                        html.write(",")
                    html.write(content)

    table.end()


def matrix_find_majorities(rows, painters, for_header):
    counts = {} # dict row_id -> painter_nr -> value -> count

    for row in rows:
        if for_header:
            row_id = None
        else:
            row_id = tuple(group_value(row, [ painters[0] ]))
        for painter_nr, painter in enumerate(painters[1:]):
            value = group_value(row, [painter])
            row_entry = counts.setdefault(row_id, {})
            painter_entry = row_entry.setdefault(painter_nr, {})
            painter_entry.setdefault(value, 0)
            painter_entry[value] += 1


    # Now find majorities for each row
    majorities = {} # row_id -> painter_nr -> majority value
    for row_id, row_entry in counts.items():
        maj_entry = majorities.setdefault(row_id, {})
        for painter_nr, painter_entry in row_entry.items():
            maj_value = None
            max_count = 0  # Absolute maximum count
            max_non_unique = 0 # maximum count, but maybe non unique
            for value, count in painter_entry.items():
                if count > max_non_unique and count >= 2:
                    maj_value = value
                    max_non_unique = count
                    max_count = count
                elif count == max_non_unique:
                    maj_value = None
                    max_count = None
            maj_entry[painter_nr] = maj_value


    if for_header:
        return majorities.get(None, {})
    else:
        return counts, majorities

# Create list of matrices to render
def create_matrices(rows, group_painters, painters, num_columns):

    if len(painters) < 2:
        raise MKGeneralException(_("Cannot display this view in matrix layout. You need at least two columns!"))

    if not group_painters:
        raise MKGeneralException(_("Cannot display this view in matrix layout. You need at least one group column!"))

    # First find the groups - all rows that have the same values for
    # all group columns. Usually these should correspond with the hosts
    # in the matrix
    groups = []
    last_group_id = None
    unique_row_ids = [] # not a set, but a list. Need to keep sort order!
    matrix_cells = {} # Dict from row_id -> group_id -> row
    col_num = 0

    for row in rows:
        register_events(row) # needed for playing sounds
        group_id = group_value(row, group_painters)
        if group_id != last_group_id:
            col_num += 1
            if num_columns != None and col_num > num_columns:
                yield (groups, unique_row_ids, matrix_cells)
                groups = []
                unique_row_ids = [] # not a set, but a list. Need to keep sort order!
                matrix_cells = {} # Dict from row_id -> group_id -> row
                col_num = 1

            last_group_id = group_id
            groups.append((group_id, row))

        # Now the rule is that the *first* column painter (usually the service
        # description) will define the left legend of the matrix. It defines
        # the set of possible rows.
        row_id = group_value(row, [ painters[0] ])
        if row_id not in matrix_cells:
            unique_row_ids.append(row_id)
            matrix_cells[row_id] = {}
        matrix_cells[row_id][group_id] = row

    if col_num:
        yield (groups, unique_row_ids, matrix_cells)



multisite_layouts["matrix"] = {
    "title"      : _("Matrix"),
    "render"     : render_matrix,
    "csv_export" : csv_export_matrix,
    "group"      : True,
    "checkboxes" : False,
    "options"    : [ "matrix_omit_uniform" ],
}
