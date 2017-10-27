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
import config
from lib import num_split

table     = None
mode      = None
next_func = None
row_css   = None

def begin(table_id=None, title=None, **kwargs):
    global table, mode, next_func

    # Use our pagename as table id if none is specified
    if table_id == None:
        table_id = html.myfile

    try:
        limit = config.table_row_limit
    except:
        limit = None

    limit = kwargs.get('limit', limit)
    if html.var('limit') == 'none' or kwargs.get("output_format", "html") != "html":
        limit = None

    table = {
        "id"              : table_id,
        "title"           : title,
        "headers"         : [],
        "collect_headers" : False, # also: True, "finished"
        "rows"            : [],
        "limit"           : limit,
        "omit_if_empty"   : kwargs.get("omit_if_empty", False),
        "omit_headers"    : kwargs.get("omit_headers", False),
        "searchable"      : kwargs.get("searchable", True),
        "sortable"        : kwargs.get("sortable", True),
        "next_header"     : None,
        "output_format"   : kwargs.get("output_format", "html"), # possible: html, csv, fetch
    }
    if kwargs.get("empty_text"):
        table["empty_text"] = kwargs["empty_text"]
    else:
        table["empty_text"] = _("No entries.")

    if kwargs.get("help"):
        table["help"] = kwargs["help"]

    if kwargs.get("css"):
        table["css"] = kwargs["css"]

    html.plug()
    mode = 'row'
    next_func = None

def finish_previous():
    global next_func
    if next_func:
        next_func(*next_args[0], **next_args[1])
        next_func = None

def row(*posargs, **kwargs):
    finish_previous()
    global next_func, next_args
    next_func = add_row
    next_args = posargs, kwargs

def add_row(css=None, state=0, collect_headers=True, fixed=False):
    if table["next_header"]:
        table["rows"].append((table["next_header"], None, "header", True))
        table["next_header"] = None

    table["rows"].append(([], css, state, fixed))

    if collect_headers:
        if table["collect_headers"] == False:
            table["collect_headers"] = True
        elif table["collect_headers"] == True:
            table["collect_headers"] = "finished"

    elif not collect_headers and table["collect_headers"] == True:
        table["collect_headers"] = False

# Intermediate title, shown as soon as there is a following row.
# We store the group headers in the list of rows, with css None
# and state set to "header"
def groupheader(title):
    table["next_header"] = title


def text_cell(*args, **kwargs):
    kwargs["escape_text"] = True
    cell(*args, **kwargs)


def cell(*posargs, **kwargs):
    finish_previous()
    global next_func, next_args
    next_func = add_cell
    next_args = posargs, kwargs


def add_cell(title="", text="", css=None, help=None, colspan=None, sortable=True, escape_text=False):
    if escape_text:
        text = html.permissive_attrencode(text)
    else:
        if isinstance(text, HTML):
            text = "%s" % text
        if type(text) != unicode:
            text = str(text)

    htmlcode = text + html.drain()

    if table["collect_headers"] == True:
        # small helper to make sorting introducion easier. Cells which contain
        # buttons are never sortable
        if css and 'buttons' in css and sortable:
            sortable = False
        table["headers"].append((title, css, help, sortable))

    table["rows"][-1][0].append((htmlcode, css, colspan))


def end():

    global table
    finish_previous()
    html.unplug()

    if not table:
        return

    # Output-Format "fetch" simply means that all data is being
    # returned as Python-values to be rendered somewhere else.
    if table["output_format"] == "fetch":
        return table["headers"], table["rows"]

    if not table["rows"] and table["omit_if_empty"]:
        table = None
        return

    if table["output_format"] == "csv":
        _write_csv(table, csv_separator=html.var("csv_separator", ";"))
        table = None
        return

    #html.guitest_record_output("data_tables", table)

    if table["title"]:
        html.open_h3()
        html.write(table["title"])
        html.close_h3()

    if table.get("help"):
        html.help(table["help"])

    if not table["rows"]:
        html.div(table["empty_text"], class_="info")
        table = None
        return

    # Controls whether or not actions are available for a table
    rows, actions_enabled, actions_visible, search_term, user_opts = _evaluate_user_opts(table)

    # Apply limit after search / sorting etc.
    num_rows_unlimited = len(rows)
    limit = table['limit']
    if limit is not None:
        # only use rows up to the limit plus the fixed rows
        rows = [ rows[i] for i in range(num_rows_unlimited) if i < limit or rows[i][3]]
        # Display corrected number of rows
        num_rows_unlimited -= len([row for row in rows if row[3]])

    # Render header
    _write_table(table, rows, actions_enabled, actions_visible, search_term)

    if limit is not None and num_rows_unlimited > limit:
        html.message(_('This table is limited to show only %d of %d rows. '
                       'Click <a href="%s">here</a> to disable the limitation.') %
                           (limit, num_rows_unlimited, html.makeuri([('limit', 'none')])))

    if actions_enabled:
        config.user.save_file("tableoptions", user_opts)
    table = None
    return


def _evaluate_user_opts(table):

    table_id = table["id"]
    rows = table["rows"]

    search_term = None
    actions_enabled = (table["searchable"] or table["sortable"])

    if not actions_enabled:
        return rows, False, False, None, None

    else:
        user_opts = config.user.load_file("tableoptions", {})
        user_opts.setdefault(table_id, {})
        table_opts = user_opts[table_id]

        # Handle the initial visibility of the actions
        actions_visible = user_opts[table_id].get('actions_visible', False)
        if html.var('_%s_actions' % table_id):
            actions_visible = html.var('_%s_actions' % table_id) == '1'
            user_opts[table_id]['actions_visible'] = actions_visible

        if html.var('_%s_reset' % table_id):
            html.del_var('_%s_search' % table_id)
            if 'search' in table_opts:
                del table_opts['search'] # persist

        if table["searchable"]:
            # Search is always lower case -> case insensitive
            search_term = html.get_unicode_input('_%s_search' % table_id, table_opts.get('search', '')).lower()
            if search_term:
                html.set_var('_%s_search' % table_id, search_term)
                table_opts['search'] = search_term # persist
                rows = _filter_rows(rows, search_term)

        if html.var('_%s_reset_sorting' % table_id):
            html.del_var('_%s_sort' % table_id)
            if 'sort' in table_opts:
                del table_opts['sort'] # persist

        if table["sortable"]:
            # Now apply eventual sorting settings
            sort = html.var('_%s_sort' % table_id, table_opts.get('sort'))
            if sort is not None:
                html.set_var('_%s_sort' % table_id, sort)
                table_opts['sort'] = sort # persist
                sort_col, sort_reverse = map(int, sort.split(',', 1))
                rows = _sort_rows(rows, sort_col, sort_reverse)

        return rows, actions_enabled, actions_visible, search_term, user_opts


def _write_table(table, rows, actions_enabled, actions_visible, search_term):

    table_id = table["id"]
    num_cols = len(table["headers"])

    html.open_table(class_=["data", "oddeven", table["css"] if "css" in table else None])

    # If we have no group headers then paint the headers now
    if table["rows"] and table["rows"][0][2] != "header":
        _render_headers(table, actions_enabled, actions_visible)

    if actions_enabled and actions_visible:
        html.open_tr(class_=["data", "even0", "actions"])
        html.open_td(colspan=num_cols)
        if not html.in_form():
            html.begin_form("%s_actions" % table_id)

        if table["searchable"]:
            html.open_div(class_="search")
            html.text_input("_%s_search" % table_id)
            html.button("_%s_submit" % table_id, _("Search"))
            html.button("_%s_reset" % table_id, _("Reset search"))
            html.set_focus("_%s_search" % table_id)
            html.close_div()

        if html.has_var('_%s_sort' % table_id):
            html.open_div(class_=["sort"])
            html.button("_%s_reset_sorting" % table_id, _("Reset sorting"))
            html.close_div()

        if not html.in_form():
            html.begin_form("%s_actions" % table_id)

        html.hidden_fields()
        html.end_form()
        html.close_tr()

    odd = "even"
    for nr, (row, css, state, fixed) in enumerate(rows):
        # Intermediate header
        if state == "header":
            # Show the header only, if at least one (non-header) row follows
            if nr < len(rows) - 1 and rows[nr+1][2] != "header":
                html.open_tr(class_="groupheader")
                html.open_td(colspan=num_cols)
                html.open_h3()
                html.write(row)
                html.close_h3()
                html.close_td()
                html.close_tr()

                odd = "even"
                _render_headers(table, actions_enabled, actions_visible)
            continue

        odd = "even" if odd == "odd" else "odd"
        html.open_tr(class_=["data", "odd%d" % state, css if css else None])
        for cell_content, css_classes, colspan in row:
            html.open_td(class_=css_classes if css_classes else None, colspan=colspan if colspan else None)
            html.write(cell_content)
            html.close_td()
        html.close_tr()

    if not rows and search_term:
        html.open_tr(class_=["data", "odd0", "no_match"])
        html.td(_('Found no matching rows. Please try another search term.'), colspan=num_cols)
        html.close_tr()

    html.close_table()


def _write_csv(table, csv_separator):

    rows = table["rows"]
    headers = table["headers"]
    limit = table['limit']
    omit_headers = table["omit_headers"]

    num_rows_unlimited = len(rows)
    num_cols = len(headers)

    # Apply limit after search / sorting etc.
    if limit is not None:
        rows = rows[:limit]

    # If we have no group headers then paint the headers now
    if not omit_headers and table["rows"] and table["rows"][0][2] != "header":
        html.write(csv_separator.join([html.strip_tags(header) or "" for (header, css, help, sortable) in headers]) + "\n")

    odd = "even"
    for nr, (row, css, state, fixed) in enumerate(rows):
        html.write(csv_separator.join([html.strip_tags(cell_content) for cell_content, css_classes, colspan in row ]))
        html.write("\n")



def _render_headers(table, actions_enabled, actions_visible):
    if table["omit_headers"]:
        return

    table_id = table['id']

    html.open_tr()
    first_col = True
    for nr, (header, css, help, sortable) in enumerate(table["headers"]):
        text = header

        if help:
            header = '<span title="%s">%s</span>' % (html.attrencode(help), header)

        css_class = "header_%s" % css if css else None

        if not table["sortable"] or not sortable:
            html.open_th(class_=css_class)
        else:
            reverse = 0
            sort = html.var('_%s_sort' % table_id)
            if sort:
                sort_col, sort_reverse = map(int, sort.split(',', 1))
                if sort_col == nr:
                    reverse = 1 if sort_reverse == 0 else 0

            action_uri = html.makeactionuri([('_%s_sort' % table_id, '%d,%d' % (nr, reverse))])
            html.open_th(class_=["sort", css_class],
                         title=_("Sort by %s") % text,
                         onclick="location.href='%s'" % action_uri)

        # Add the table action link
        if first_col:
            first_col = False
            if actions_enabled:
                if not header:
                    header = "&nbsp;" # Fixes layout problem with white triangle
                if actions_visible:
                    state = '0'
                    help  = _('Hide table actions')
                    img   = 'table_actions_on'
                else:
                    state = '1'
                    help  = _('Display table actions')
                    img   = 'table_actions_off'
                html.open_div(class_=["toggle_actions"])
                html.icon_button(html.makeuri([('_%s_actions' % table_id, state)]),
                    help, img, cssclass = 'toggle_actions')
                html.open_span()
                html.write(header)
                html.close_span()
                html.close_div()
            else:
                html.write(header)
        else:
            html.write(header)

        html.close_th()
    html.close_tr()


def _filter_rows(rows, search_term):
    filtered_rows = []
    for row, css, state, fixed in rows:
        if state == "header" or fixed:
            filtered_rows.append((row, css, state, fixed))
            continue # skip filtering of headers or fixed rows

        for cell_content, css_classes, colspan in row:
            if search_term in cell_content.lower():
                filtered_rows.append((row, css, state, fixed))
                break # skip other cells when matched
    return filtered_rows


def _sort_rows(rows, sort_col, sort_reverse):

    # remove and remind fixed rows, add to separate list
    fixed_rows = []
    for index, row in enumerate(rows[:]):
        if row[3] == True:
            rows.remove(row)
            fixed_rows.append((index, row))

    # Then use natural sorting to sort the list. Note: due to a
    # change in the number of columns of a table in different software
    # versions the cmp-function might fail. This is because the sorting
    # column is persisted in a user file. So we ignore exceptions during
    # sorting. This gives the user the chance to change the sorting and
    # see the table in the first place.
    try:
        rows.sort(cmp=lambda a, b: cmp(num_split(a[0][sort_col][0]),
                                       num_split(b[0][sort_col][0])),
                  reverse=sort_reverse==1)
    except IndexError:
        pass

    # Now re-add the removed "fixed" rows to the list again
    if fixed_rows:
        for index, row in fixed_rows:
            rows.insert(index, row)

    return rows


