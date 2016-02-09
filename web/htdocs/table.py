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
        pass

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
    elif not collect_headers and table["collect_headers"]:
        table["collect_headers"] = False

# Intermediate title, shown as soon as there is a following row.
# We store the group headers in the list of rows, with css None
# and state set to "header"
def groupheader(title):
    table["next_header"] = title

def cell(*posargs, **kwargs):
    finish_previous()
    global next_func, next_args
    next_func = add_cell
    next_args = posargs, kwargs

def add_cell(title="", text="", css=None, help=None, colspan=None, sortable=True):
    if type(text) != unicode:
        text = str(text)
    htmlcode = text + html.drain()
    if table["collect_headers"] == True:
        # small helper to make sorting introducion easier. Cells which contain
        # buttons are never sortable
        if css and 'buttons' in css and sortable:
            sortable = False
        table["headers"].append((title, help, sortable))
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

    if table["output_format"] == "csv":
        do_csv = True
        csv_separator = html.var("csv_separator", ";")
    else:
        do_csv = False

    if not table["rows"] and table["omit_if_empty"]:
        table = None
        return

    html.guitest_record_output("data_tables", table)

    if table["title"] and not do_csv:
        html.write("<h3>%s</h3>" % table["title"])

    if table.get("help") and not do_csv:
        html.help(table["help"])

    if not table["rows"] and not do_csv:
        html.write("<div class=info>%s</div>" % table["empty_text"])
        table = None
        return

    table_id = table['id']
    rows = table["rows"]

    # Controls wether or not actions are available for a table
    search_term = None
    actions_enabled = (table["searchable"] or table["sortable"]) and not do_csv
    if actions_enabled:
        user_opts = config.load_user_file("tableoptions", {})
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
                filtered_rows = []
                for row, css, state, fixed in rows:
                    if state == "header" or fixed:
                        continue # skip filtering of headers or fixed rows
                    for cell_content, css_classes, colspan in row:
                        if fixed or search_term in cell_content.lower():
                            filtered_rows.append((row, css, state, fixed))
                            break # skip other cells when matched
                rows = filtered_rows

        if html.var('_%s_reset_sorting' % table_id):
            html.del_var('_%s_sort' % table_id)
            if 'sort' in table_opts:
                del table_opts['sort'] # persist

        if table["sortable"]:
            # Now apply eventual sorting settings
            sort = html.var('_%s_sort' % table_id, table_opts.get('sort'))
            if sort != None:
                html.set_var('_%s_sort' % table_id, sort)
                table_opts['sort'] = sort # persist
                sort_col, sort_reverse = map(int, sort.split(',', 1))

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

    num_rows_unlimited = len(rows)
    num_cols = len(table["headers"])

    # Apply limit after search / sorting etc.
    limit = table['limit']
    if limit is not None:
        rows = rows[:limit]

    if not do_csv:
        html.write('<table class="data oddeven')
        if "css" in table:
            html.write(" %s" % table["css"])
        html.write('">\n')

    def render_headers():
        if table["omit_headers"]:
            return

        if do_csv:
            html.write(csv_separator.join([html.strip_tags(header) or "" for (header, help, sortable) in table["headers"]]) + "\n")
        else:
            html.write("  <tr>")
            first_col = True
            for nr, (header, help, sortable) in enumerate(table["headers"]):
                text = header
                if help:
                    header = '<span title="%s">%s</span>' % (html.attrencode(help), header)
                if not table["sortable"] or not sortable:
                    html.write("  <th>")
                else:
                    reverse = 0
                    sort = html.var('_%s_sort' % table_id)
                    if sort:
                        sort_col, sort_reverse = map(int, sort.split(',', 1))
                        if sort_col == nr:
                            reverse = sort_reverse == 0 and 1 or 0
                    html.write("  <th class=\"sort\" title=\"%s\" onclick=\"location.href='%s'\">" %
                                (_('Sort by %s') % text, html.makeactionuri([('_%s_sort' % table_id, '%d,%d' % (nr, reverse))])))

                # Add the table action link
                if first_col:
                    first_col = False
                    if actions_enabled:
                        if actions_visible:
                            state = '0'
                            help  = _('Hide table actions')
                            img   = 'table_actions_on'
                        else:
                            state = '1'
                            help  = _('Display table actions')
                            img   = 'table_actions_off'
                        html.write("<div class=\"toggle_actions\">")
                        html.icon_button(html.makeuri([('_%s_actions' % table_id, state)]),
                            help, img, cssclass = 'toggle_actions')
                        html.write("<span>%s</span>" % header)
                        html.write("</div>")
                    else:
                        html.write(header)
                else:
                    html.write(header)

                html.write("</th>\n")
            html.write("  </tr>\n")

    # If we have no group headers then paint the headers now
    if table["rows"] and table["rows"][0][2] != "header":
        render_headers()

    if actions_enabled and actions_visible and not do_csv:
        html.write('<tr class="data even0 actions"><td colspan=%d>' % num_cols)
        if not html.in_form():
            html.begin_form("%s_actions" % table_id)

        if table["searchable"]:
            html.write("<div class=search>")
            html.text_input("_%s_search" % table_id)
            html.button("_%s_submit" % table_id, _("Search"))
            html.button("_%s_reset" % table_id, _("Reset search"))
            html.set_focus("_%s_search" % table_id)
            html.write("</div>\n")

        if html.has_var('_%s_sort' % table_id):
            html.write("<div class=sort>")
            html.button("_%s_reset_sorting" % table_id, _("Reset sorting"))
            html.write("</div>\n")

        if not html.in_form():
            html.begin_form("%s_actions" % table_id)

        html.hidden_fields()
        html.end_form()
        html.write('</tr>')

    odd = "even"
    for nr, (row, css, state, fixed) in enumerate(rows):
        if do_csv:
            html.write(csv_separator.join([html.strip_tags(cell_content) for cell_content, css_classes, colspan in row ]))
            html.write("\n")

        else: # HTML output
            # Intermediate header
            if state == "header":
                # Show the header only, if at least one (non-header) row follows
                if nr < len(rows) - 1 and rows[nr+1][2] != "header":
                    html.write('  <tr class="groupheader"><td colspan=%d><br>%s</td></tr>' % (num_cols, row))
                    odd = "even"
                    render_headers()
                continue

            odd = odd == "odd" and "even" or "odd"
            html.write('  <tr class="data %s%d' % (odd, state))
            if css:
                html.write(' %s' % css)
            html.write('">\n')
            for cell_content, css_classes, colspan in row:
                colspan = colspan and (' colspan="%d"' % colspan) or ''
                html.write("    <td%s%s>" % (css_classes and (" class='%s'" % css_classes) or "", colspan))
                html.write(cell_content)
                html.write("</td>\n")
            html.write("</tr>\n")

    if table["searchable"] and search_term and not rows and not do_csv:
        html.write('<tr class="data odd0 no_match"><td colspan=%d>%s</td></tr>' %
            (num_cols, _('Found no matching rows. Please try another search term.')))

    if not do_csv:
        html.write("</table>\n")

    if limit is not None and num_rows_unlimited > limit and not do_csv:
        html.message(_('This table is limited to show only %d of %d rows. '
                       'Click <a href="%s">here</a> to disable the limitation.') %
                           (limit, num_rows_unlimited, html.makeuri([('limit', 'none')])))

    if actions_enabled and not do_csv:
        config.save_user_file("tableoptions", user_opts)

    table = None


