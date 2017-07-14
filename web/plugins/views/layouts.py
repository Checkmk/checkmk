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
    if not config.user.may("general.act"):
        return

    selected = weblib.get_rowselection('view-' + view['name'])
    html.javascript(
        'g_page_id = "view-%s";\n'
        'g_selection = "%s";\n'
        'g_selected_rows = %s;\n'
        'init_rowselect();' % (view['name'], weblib.selection_id(), json.dumps(selected))
    )

def render_checkbox(view, row, num_tds):
    # value contains the number of columns of this datarow. This is
    # needed for hiliting the correct number of TDs
    html.input(type_="checkbox", name=row_id(view, row), value=(num_tds+1))
    html.label("", row_id(view, row))

def render_checkbox_td(view, row, num_tds):
    html.open_td(class_="checkbox")
    render_checkbox(view, row, num_tds)
    html.close_td()

def render_group_checkbox_th():
    html.open_th()
    html.input(type_="button", class_="checkgroup", name="_toggle_group",
               onclick="toggle_group_rows(this);", value='X')
    html.close_th()

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
def render_single_dataset(rows, view, group_cells, cells, num_columns, _ignore_show_checkboxes):
    for row in rows:
        save_state_for_playing_alarm_sounds(row)

    html.open_table(class_="data single")
    rownum = 0
    odd = "odd"
    while rownum < len(rows):
        if rownum > 0:
            html.open_tr(class_="gap")
            html.td("", class_="gap", colspan=(num_columns + 1))
            html.close_tr()
        thispart = rows[rownum:rownum + num_columns]
        for cell in cells:
            odd = "even" if odd == "odd" else "odd"
            html.open_tr(class_="data %s0" % odd)
            if view.get("column_headers") != "off":
                html.open_td(class_="left")
                html.write(cell.title(use_short=False))
                html.close_td()

            for row in thispart:
                cell.paint(row)

            if len(thispart) < num_columns:
                html.td('', class_="gap", style="border-style: none;", colspan=(1 + num_columns - len(thispart)))
            html.close_tr()
        rownum += num_columns
    html.close_table()
    html.close_div()


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
def render_grouped_boxes(rows, view, group_cells, cells, num_columns, show_checkboxes, css_class=None):

    repeat_heading_every = 20 # in case column_headers is "repeat"

    # N columns. Each should contain approx the same number of entries
    groups = []
    last_group = None
    for row in rows:
        save_state_for_playing_alarm_sounds(row)
        this_group = group_value(row, group_cells)
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
    def render_group(header, rows_with_ids):
        html.open_table(class_="groupheader", cellspacing=0,  cellpadding=0, border=0)
        html.open_tr(class_="groupheader")
        painted = False
        for cell in group_cells:
            if painted:
                html.td(",&nbsp;")
            painted = cell.paint(rows_with_ids[0][1])
        html.close_tr()
        html.close_table()

        html.open_table(class_="data")
        odd = "even"

        def show_header_line():
            html.open_tr()
            if show_checkboxes:
                render_group_checkbox_th()
            for cell in cells:
                cell.paint_as_header()
                html.write_text("\n")
            html.close_tr()

        column_headers = view.get("column_headers")
        if column_headers != "off":
            show_header_line()

        groups, rows_with_ids = calculate_grouping_of_services(rows_with_ids)

        visible_row_number = 0
        group_hidden, num_grouped_rows = None, 0
        for index, row in rows_with_ids:
            if view.get("column_headers") == "repeat":
                if visible_row_number > 0 and visible_row_number % repeat_heading_every == 0:
                    show_header_line()
            visible_row_number += 1

            save_state_for_playing_alarm_sounds(row)

            odd = "even" if odd == "odd" else "odd"

            # state = row.get("service_state", row.get("aggr_state"))
            state = saveint(row.get("service_state"))
            if state == None:
                state = saveint(row.get("host_state", 0))
                if state > 0:
                    state +=1 # 1 is critical for hosts

            num_cells = len(cells)

            if index in groups:
                group_spec, num_grouped_rows = groups[index]
                group_hidden = grouped_row_title(index, group_spec, num_grouped_rows, odd, num_cells)
                odd = "even" if odd == "odd" else "odd"


            css_classes = []

            if is_stale(row):
                css_classes.append("stale")

            hide = ""
            if num_grouped_rows > 0:
                num_grouped_rows -= 1
                if group_hidden:
                    hide = "display:none"

            if group_hidden != None and num_grouped_rows == 0:
                # last row in group
                css_classes.append("group_end")
                group_hidden = None

            css_classes.append("%s%d" % (odd, state))

            html.open_tr(class_=["data"] + css_classes, style=hide)

            if show_checkboxes:
                render_checkbox_td(view, row, num_cells)

            for cell in cells:
                cell.paint(row)

            html.close_tr()

        html.close_table()
        init_rowselect(view)

    # render table
    html.open_table(class_=["boxlayout", css_class if css_class else ''])
    html.open_tr()
    for column in columns:
        html.open_td(class_="boxcolumn")
        for header, rows_with_ids in column:
            render_group(header, rows_with_ids)
        html.close_td()
    html.close_tr()
    html.close_table()


def grouped_row_title(index, group_spec, num_rows, trclass, num_cells):
    is_open = html.foldable_container_is_open("grouped_rows", index, False)
    html.open_tr(class_=["data", "grouped_row_header", "closed" if not is_open else '', "%s0" % trclass])
    html.open_td(colspan=num_cells,
                 onclick="toggle_grouped_rows('grouped_rows', '%s', this, %d)" % (index, num_rows))

    html.img("images/tree_black_closed.png", align="absbottom", class_=["treeangle", "nform", "open" if is_open else "closed"])
    html.write_text("%s (%d)" % (group_spec["title"], num_rows))

    html.close_td()
    html.close_tr()

    return not is_open


# Produces a dictionary where the row index of the first row is used as key
# and a tuple of the group_spec and the number of rows in this group is the value
def calculate_grouping_of_services(rows):
    if not config.service_view_grouping:
        return {}, rows

    # First create dictionaries for each found group containing the
    # group spec and the row indizes of the grouped rows
    groups = {}
    current_group = None
    group_id = None
    for index, (row_id, row) in enumerate(rows[:]):
        group_spec = try_to_match_group(row)
        if group_spec:
            if current_group == None:
                group_id = row_id

            elif current_group != group_spec:
                group_id = row_id

            # When the service is not OK and should not be grouped, move it's row
            # in front of the group.
            if row.get("service_state", -1) != 0 or is_stale(row):
                if current_group == None or current_group != group_spec:
                    continue # skip grouping first row

                elif current_group == group_spec:
                    row = rows.pop(index)
                    rows.insert(index - len(groups[group_id][1]), row)
                    continue

            current_group = group_spec
            groups.setdefault(group_id, (group_spec, []))
            groups[group_id][1].append(row_id)
        else:
            current_group = None

    # Now create the final structure as described above
    groupings = {}
    for group_id, (group_spec, row_indizes) in groups.items():
        if len(row_indizes) >= group_spec.get("min_items", 2):
            groupings[row_indizes[0]] = group_spec, len(row_indizes)

    return groupings, rows


def try_to_match_group(row):
    for group_spec in config.service_view_grouping:
        if row.get('service_description', '') != '' \
           and re.match(group_spec["pattern"], row["service_description"]):
            return group_spec

    return None


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


def render_grouped_boxed_graphs(*args):
    return render_grouped_boxes(*args, css_class="graph")


multisite_layouts["boxed_graph"] = {
    "title"      : _("Balanced graph boxes"),
    "render"     : render_grouped_boxed_graphs,
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

def render_tiled(rows, view, group_cells, cells, _ignore_num_columns, show_checkboxes):
    html.open_table(class_="data tiled")

    last_group = None
    group_open = False
    for row in rows:
        # Show group header
        if group_cells:
            this_group = group_value(row, group_cells)
            if this_group != last_group:

                # paint group header
                if group_open:
                    html.close_td()
                    html.close_tr()
                html.open_tr()
                html.open_td()
                html.open_table(class_="groupheader")
                html.open_tr(class_="groupheader")

                painted = False
                for cell in group_cells:
                    if painted:
                        html.td(',&nbsp;')
                    painted = cell.paint(row)

                html.close_tr()
                html.close_table()

                html.close_td()
                html.close_tr()

                html.open_tr()
                html.open_td(class_="tiles")

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
            html.open_tr()
            html.open_td(class_="tiles")
            group_open = True

        html.open_div(class_=["tile", sclass])
        html.open_table()

        # We need at least five cells
        if len(cells) < 5:
            cells = cells + ([ EmptyCell(view) ] * (5 - len(cells)))

        rendered = [ cell.render(row) for cell in cells ]

        html.open_tr()
        html.open_td(class_=["tl", rendered[1][0]])
        if show_checkboxes:
            render_checkbox(view, row, len(cells)-1)
        html.write("%s" % rendered[1][1])
        html.close_td()
        html.open_td(class_=["tr", rendered[2][0]])
        html.write("%s" % rendered[2][1])
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td(colspan=2, class_=["center", rendered[0][0]])
        html.write("%s" % rendered[0][1])
        html.close_td()
        html.close_tr()

        for css, cont in rendered[5:]:
            html.open_tr()
            html.open_td(colspan=2, class_=["cont", css])
            html.write("%s" % cont)
            html.close_td()
            html.close_tr()

        html.open_tr()
        html.open_td(class_=["bl", rendered[3][0]])
        html.write("%s" % rendered[3][1])
        html.close_td()
        html.open_td(class_=["br", rendered[4][0]])
        html.write("%s" % rendered[4][1])
        html.close_td()
        html.close_tr()

        html.close_table()
        html.close_div()

    if group_open:
        html.close_td()
        html.close_tr()

    html.close_table()
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


def render_grouped_list(rows, view, group_cells, cells, num_columns, show_checkboxes):

    repeat_heading_every = 20 # in case column_headers is "repeat"

    html.open_table(class_='data table')
    last_group = None
    odd = "even"
    column = 1
    group_open = False
    num_cells = len(cells)
    if show_checkboxes:
        num_cells += 1

    def show_header_line():
        html.open_tr()
        for n in range(1, num_columns + 1):
            if show_checkboxes:
                if n == 1:
                    render_group_checkbox_th()
                else:
                    html.th('')

            last_cell = cells[-1]
            for cell in cells:
                cell.paint_as_header(is_last_column_header=cell == last_cell)

            if n < num_columns:
                html.td('', class_="gap")

        html.close_tr()

    if not group_cells and view.get("column_headers") != "off":
        show_header_line()

    # Helper function that counts the number of entries in
    # the current group
    def count_group_members(row, rows):
        this_group = group_value(row, group_cells)
        members = 1
        for row in rows[1:]:
            that_group = group_value(row, group_cells)
            if that_group == this_group:
                members += 1
            else:
                break
        return members

    rows_with_ids = [ (row_id(view, row), row) for row in rows ]
    groups, rows_with_ids = calculate_grouping_of_services(rows_with_ids)

    visible_row_number = 0
    group_hidden, num_grouped_rows = None, 0
    for index, row in rows_with_ids:
        save_state_for_playing_alarm_sounds(row)
        # Show group header, if a new group begins. But only if grouping
        # is activated
        if group_cells:
            this_group = group_value(row, group_cells)
            if this_group != last_group:
                if column != 1: # not a the beginning of a new line
                    for i in range(column-1, num_columns):
                        html.td('', class_="gap")
                        html.td('', class_="fillup", colspan=num_cells)
                    html.close_tr()
                    column = 1

                group_open = True
                visible_row_number = 0

                # paint group header, but only if it is non-empty
                header_is_empty = True
                for cell in group_cells:
                    tdclass, content = cell.render(row)
                    if content:
                        header_is_empty = False
                        break

                if not header_is_empty:
                    html.open_tr(class_="groupheader")
                    html.open_td(class_="groupheader", colspan=(num_cells * (num_columns + 2) + (num_columns - 1)))
                    html.open_table(class_="groupheader", cellspacing=0, cellpadding=0, border=0)
                    html.open_tr()
                    painted = False
                    for cell in group_cells:
                        if painted:
                            html.td(',&nbsp;')
                        painted = cell.paint(row)

                    html.close_tr()
                    html.close_table()
                    html.close_td()
                    html.close_tr()

                # Table headers
                if view.get("column_headers") != "off":
                    show_header_line()
                trclass = "even"
                last_group = this_group

        # Should we wrap over to a new line?
        if column >= num_columns + 1:
            html.close_tr()
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
                if not row.get('service_description'):
                    state = row.get("host_state", 0)
                    if state > 0: state +=1 # 1 is critical for hosts
                else:
                    state = row.get("service_state", 0)
            else:
                state = 0

            if index in groups:
                group_spec, num_grouped_rows = groups[index]
                group_hidden = grouped_row_title(index, group_spec, num_grouped_rows, odd, num_cells)
                odd = "even" if odd == "odd" else "odd"

            css_classes = []

            hide = ""
            if num_grouped_rows > 0:
                num_grouped_rows -= 1
                if group_hidden:
                    hide = "display:none"

            if group_hidden != None and num_grouped_rows == 0:
                # last row in group
                css_classes.append("group_end")
                group_hidden = None

            odd = "even" if odd == "odd" else "odd"

            if num_columns > 1:
                css_classes.append("multicolumn")
            css_classes += ["%s%d" % (odd, state)]

            html.open_tr(class_=["data"] + css_classes, style=hide)

        # Not first columns: Create one empty column as separator
        else:
            html.open_td(class_="gap")
            html.close_td()


        if show_checkboxes:
            render_checkbox_td(view, row, num_cells)

        last_cell = cells[-1]
        for cell in cells:
            cell.paint(row, is_last_cell=last_cell==cell)

        column += 1

    if group_open:
        for i in range(column-1, num_columns):
            html.td('', class_="gap")
            html.td('', class_="fillup", colspan=num_cells)
        html.close_tr()
    html.close_table()
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

def render_matrix(rows, view, group_cells, cells, num_columns, _ignore_show_checkboxes):

    header_majorities = matrix_find_majorities_for_header(rows, group_cells)
    value_counts, row_majorities = matrix_find_majorities(rows, cells)

    for groups, unique_row_ids, matrix_cells in \
             create_matrices(rows, group_cells, cells, num_columns):

        # Paint the matrix. Begin with the group headers
        html.open_table(class_="data matrix")
        odd = "odd"
        for cell_nr, cell in enumerate(group_cells):
            odd = "even" if odd == "odd" else "odd"
            html.open_tr(class_="data %s0" % odd)
            html.open_td(class_="matrixhead")
            html.write(cell.title(use_short=False))
            html.close_td()
            for group, group_row in groups:
                tdclass, content = cell.render(group_row)
                if cell_nr > 0:
                    gv = group_value(group_row, [cell])
                    majority_value = header_majorities.get(cell_nr-1, None)
                    if majority_value != None and majority_value != gv:
                        tdclass += " minority"
                html.open_td(class_=["left", tdclass])
                html.write(content)
                html.close_td()
            html.close_tr()

        # Now for each unique service^H^H^H^H^H^H ID column paint one row
        for row_id in unique_row_ids:
            # Omit rows where all cells have the same values
            if painter_options.get("matrix_omit_uniform"):
                at_least_one_different = False
                for counts in value_counts[row_id].values():
                    if len(counts) > 1:
                        at_least_one_different = True
                        break
                if not at_least_one_different:
                    continue

            odd = "even" if odd == "odd" else "odd"
            html.open_tr(class_="data %s0" % odd)
            tdclass, content = cells[0].render(matrix_cells[row_id].values()[0])
            html.open_td(class_=["left", tdclass])
            html.write(content)
            html.close_td()

            # Now go through the groups and paint the rest of the
            # columns
            for group_id, group_row in groups:
                cell_row = matrix_cells[row_id].get(group_id)
                if cell_row == None:
                    html.td('')
                else:
                    if len(cells) > 2:
                        html.open_td(class_="cell")
                        html.open_table()

                    for cell_nr, cell in enumerate(cells[1:]):
                        tdclass, content = cell.render(cell_row)

                        gv = group_value(cell_row, [cell])
                        majority_value =  row_majorities[row_id].get(cell_nr, None)
                        if majority_value != None and majority_value != gv:
                            tdclass += " minority"

                        if len(cells) > 2:
                            html.open_tr()
                        html.open_td(class_=tdclass)
                        html.write(content)
                        html.close_td()
                        if len(cells) > 2:
                            html.close_tr()

                    if len(cells) > 2:
                        html.close_table()
                        html.close_td()
            html.close_tr()

        html.close_table()


def csv_export_matrix(rows, view, group_cells, cells):
    output_csv_headers(view)

    groups, unique_row_ids, matrix_cells = list(create_matrices(rows, group_cells, cells, num_columns=None))[0]
    value_counts, row_majorities = matrix_find_majorities(rows, cells)

    table.begin(output_format="csv")
    for cell_nr, cell in enumerate(group_cells):
        table.row()
        table.cell("", cell.title(use_short=False))
        for group, group_row in groups:
            tdclass, content = cell.render(group_row)
            table.cell("", content)

    for row_id in unique_row_ids:
        # Omit rows where all cells have the same values
        if painter_options.get("matrix_omit_uniform"):
            at_least_one_different = False
            for counts in value_counts[row_id].values():
                if len(counts) > 1:
                    at_least_one_different = True
                    break
            if not at_least_one_different:
                continue

        table.row()
        tdclass, content = cells[0].render(matrix_cells[row_id].values()[0])
        table.cell("", content)

        for group_id, group_row in groups:
            table.cell("")
            cell_row = matrix_cells[row_id].get(group_id)
            if cell_row != None:
                for cell_nr, cell in enumerate(cells[1:]):
                    tdclass, content = cell.render(cell_row)
                    if cell_nr:
                        html.write_text(",")
                    html.write(content)

    table.end()


def matrix_find_majorities_for_header(rows, group_cells):
    counts, majorities = matrix_find_majorities(rows, group_cells, for_header=True)
    return majorities.get(None, {})


def matrix_find_majorities(rows, cells, for_header=False):
    counts = {} # dict row_id -> cell_nr -> value -> count

    for row in rows:
        if for_header:
            row_id = None
        else:
            row_id = tuple(group_value(row, [ cells[0] ]))

        for cell_nr, cell in enumerate(cells[1:]):
            value = group_value(row, [cell])
            row_entry = counts.setdefault(row_id, {})
            cell_entry = row_entry.setdefault(cell_nr, {})
            cell_entry.setdefault(value, 0)
            cell_entry[value] += 1


    # Now find majorities for each row
    majorities = {} # row_id -> cell_nr -> majority value
    for row_id, row_entry in counts.items():
        maj_entry = majorities.setdefault(row_id, {})
        for cell_nr, cell_entry in row_entry.items():
            maj_value = None
            max_count = 0  # Absolute maximum count
            max_non_unique = 0 # maximum count, but maybe non unique
            for value, count in cell_entry.items():
                if count > max_non_unique and count >= 2:
                    maj_value = value
                    max_non_unique = count
                    max_count = count
                elif count == max_non_unique:
                    maj_value = None
                    max_count = None
            maj_entry[cell_nr] = maj_value

    return counts, majorities


# Create list of matrices to render
def create_matrices(rows, group_cells, cells, num_columns):

    if len(cells) < 2:
        raise MKGeneralException(_("Cannot display this view in matrix layout. You need at least two columns!"))

    if not group_cells:
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
        save_state_for_playing_alarm_sounds(row)
        group_id = group_value(row, group_cells)
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

        # Now the rule is that the *first* cell (usually the service
        # description) will define the left legend of the matrix. It defines
        # the set of possible rows.
        row_id = group_value(row, [ cells[0] ])
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
