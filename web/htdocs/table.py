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

import config

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
    if html.var('limit') == 'none' or kwargs.get("output_format", "html") == "csv":
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
        "next_header"     : None,
        "output_format"   : kwargs.get("output_format", "html"),
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

def add_row(css=None, state=0):
    if table["next_header"]:
        table["rows"].append((table["next_header"], None, "header"))
        table["next_header"] = None
    table["rows"].append(([], css, state))
    if table["collect_headers"] == False:
        table["collect_headers"] = True
    elif table["collect_headers"] == True:
        table["collect_headers"] = "finished"

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

def add_cell(title="", text="", css=None, help=None, colspan=None):
    if type(text) != unicode:
        text = str(text)
    htmlcode = text + html.drain()
    if table["collect_headers"] == True:
        table["headers"].append((title, help))
    table["rows"][-1][0].append((htmlcode, css, colspan))

def end():
    global table
    finish_previous()
    html.unplug()

    if not table:
        return

    if table["output_format"] == "csv":
        do_csv = True
        csv_separator = html.var("csv_separator", ";")
    else:
        do_csv = False

    if not table["rows"] and table["omit_if_empty"]:
        table = None
        return

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
    actions_enabled = table["searchable"] and not do_csv
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

        # Search is always lower case -> case insensitive
        search_term = html.var('_%s_search' % table_id, table_opts.get('search', '')).lower()
        if search_term:
            html.set_var('_%s_search' % table_id, search_term)
            table_opts['search'] = search_term # persist
            filtered_rows = []
            for row, css, state in rows:
                if state == "header":
                    continue
                for cell_content, css_classes, colspan in row:
                    if search_term in cell_content.lower():
                        filtered_rows.append((row, css, state))
                        break # skip other cells when matched
            rows = filtered_rows

    num_rows_unlimited = len(rows)
    num_cols = len(table["headers"])

    # Apply limit after search / sorting etc.
    limit = table['limit']
    if limit is not None:
        rows = rows[:limit]

    if not do_csv:
        html.write('<table class="data')
        if "css" in table:
            html.write(" %s" % table["css"])
        html.write('">\n')

    def render_headers():
        if table["omit_headers"]:
            return

        if do_csv:
            html.write(csv_separator.join([html.strip_tags(header) or "" for (header, help) in table["headers"]]) + "\n")
        else:
            html.write("  <tr>")
            first_col = True
            for header, help in table["headers"]:
                if help:
                    header = '<span title="%s">%s</span>' % (html.attrencode(help), header)
                html.write("  <th>")

                # Add the table action link
                if first_col:
                    if actions_enabled:
                        if actions_visible:
                            state = '0'
                            help  = _('Hide table actions')
                            img   = 'table_actions_on'
                        else:
                            state = '1'
                            help  = _('Display table actions')
                            img   = 'table_actions_off'
                        html.icon_button(html.makeuri([('_%s_actions' % table_id, state)]),
                            help, img, cssclass = 'toggle_actions')
                    first_col = False

                html.write("%s</th>\n" % header)
            html.write("  </tr>\n")

    # If we have no group headers then paint the headers now
    if table["rows"] and table["rows"][0][2] != "header":
        render_headers()

    if actions_enabled and actions_visible and not do_csv:
        html.write('<tr class="data even0 actions"><td colspan=%d>' % num_cols)
        html.begin_form("%s_actions" % table_id)

        if table["searchable"]:
            html.write("<div class=search>")
            html.text_input("_%s_search" % table_id)
            html.button("_%s_submit" % table_id, _("Search"))
            html.button("_%s_reset" % table_id, _("Reset"))
            html.set_focus("_%s_search" % table_id)
            html.write("</div>\n")

        html.hidden_fields()
        html.end_form()
        html.write('</tr>')

    odd = "even"
    # TODO: Sorting

    for nr, (row, css, state) in enumerate(rows):
        if do_csv:
            html.write(csv_separator.join([ html.strip_tags(cell_content) for cell_content, css_classes, colspan in row ]))
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

    if actions_enabled and search_term and not rows and not do_csv:
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


