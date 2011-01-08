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

import config, defaults, livestatus, htmllib, time, os, re, pprint, time, copy
from lib import *
from pagefunctions import *

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set


config.declare_permission_section("action", "Commands on Objects")
config.declare_permission("action.notifications",
        "Enable/disable notifications",
        "Enable and disable notifications on hosts and services",
        [ "admin" ])
config.declare_permission("action.enablechecks",
        "Enable/disable checks",
        "Enable and disable active or passive checks on hosts and services",
        [ "admin" ])
config.declare_permission("action.reschedule",
        "Reschedule checks",
        "Reschedule host and service checks",
        [ "user", "admin" ])
config.declare_permission("action.fakechecks",
        "Fake check results",
        "Manually submit check results for host and service checks",
        [ "admin" ])
config.declare_permission("action.acknowledge",
        "Acknowledge",
        "Acknowledge host and service problems and remove acknowledgements",
        [ "user", "admin" ])
config.declare_permission("action.addcomment",
        "Add comments",
        "Add comments to hosts or services, and remove comments",
        [ "user", "admin" ])
config.declare_permission("action.downtimes",
        "Set/Remove Downtimes",
        "Schedule and remove downtimes on hosts and services",
        [ "user", "admin" ])

# Datastructures and functions needed before plugins can be loaded

multisite_datasources      = {}
multisite_filters          = {}
multisite_layouts          = {}
multisite_painters         = {}
multisite_sorters          = {}
multisite_builtin_views    = {}
multisite_painter_options  = {}


##################################################################################
# Layouts
##################################################################################

def toggle_button(id, isopen, text, addclasses=[]):
    if isopen:
        cssclass = "open"
    else:
        cssclass = "closed"
    classes = " ".join(["navi"] + addclasses)
    html.write('<td class="left %s" onclick="toggle_tab(this, \'%s\');" '
               'onmouseover="this.style.cursor=\'pointer\'; hover_tab(this);" '
               'onmouseout="this.style.cursor=\'auto\'; unhover_tab(this);">%s</td>\n' % (cssclass, id, text))


def show_filter_form(is_open, filters):
    # Table muss einen anderen Namen, als das Formular
    html.write("<tr class=form id=table_filter %s>\n" % (not is_open and 'style="display: none"' or '') )
    html.write("<td>")
    html.begin_form("filter")
    html.write("<div class=whiteborder>\n")

    html.write("<table class=form>\n")
    # sort filters according to title
    s = [(f.sort_index, f.title, f) for f in filters]
    s.sort()
    col = 0
    for sort_index, title, f in s:
        if col == 0:
            html.write("<tr>")
        html.write("<td class=legend>%s</td>" % title)
        html.write("<td class=content>")
        f.display()
        html.write("</td>")
        if col == 1:
            html.write("</tr>\n")
        col = (col + 1) % 2
    if col == 1:
        html.write("<td class=legend></td>\n<td class=content></td></tr>\n")
    html.write('<tr><td class="legend button" colspan=4>')
    html.button("search", "Search", "submit")
    html.write("</td></tr>\n")
    html.write("</table>\n")

    html.hidden_fields()
    html.end_form()

    html.write("</div>")
    html.write("</td></tr>\n")

def show_painter_options(painter_options):
    html.write('<tr class=form id=painter_options style="display: none">')
    html.write("<td>")
    html.begin_form("painteroptions")
    html.write("<div class=whiteborder>\n")

    html.write("<table class=form>\n")
    for on in painter_options:
        opt = multisite_painter_options[on]
        html.write("<tr>")
        html.write("<td class=legend>%s</td>" % opt["title"])
        html.write("<td class=content>")
        html.select(on, opt["values"], get_painter_option(on), "submit();" )
        html.write("</td></tr>\n")
    html.write("</table>\n")

    html.hidden_fields()
    html.end_form()
    html.write("</div>")
    html.write("</td></tr>\n")


##################################################################################
# Filters
##################################################################################

def declare_filter(sort_index, f, comment = None):
    multisite_filters[f.name] = f
    f.comment = comment
    f.sort_index = sort_index

# Base class for all filters
class Filter:
    def __init__(self, name, title, info, htmlvars, link_columns):
        self.name = name
        self.info = info
        self.title = title
        self.htmlvars = htmlvars
        self.link_columns = link_columns

    def display(self):
        raise MKInternalError("Incomplete implementation of filter %s '%s': missing display()" % \
                (self.name, self.title))
        html.write("FILTER NOT IMPLEMENTED")

    def filter(self, tablename):
        return ""

    # post-Livestatus filtering (e.g. for BI aggregations)
    def filter_table(self, rows):
        return rows

    def variable_settings(self, row):
        return [] # return pairs of htmlvar and name according to dataset in row

    def infoprefix(self, infoname):
        if self.info == infoname:
            return ""
        else:
            return self.info[:-1] + "_"

    # Hidden filters may contribute to the pages headers of the views
    def heading_info(self, infoname):
        return None

# Load all view plugins
plugins_path = defaults.web_dir + "/plugins/views"
for fn in os.listdir(plugins_path):
    if fn.endswith(".py"):
        execfile(plugins_path + "/" + fn)
if defaults.omd_root:
    local_plugins_path = defaults.omd_root + "/local/share/check_mk/web/plugins/views"
    if os.path.exists(local_plugins_path):
        for fn in os.listdir(local_plugins_path):
            if fn.endswith(".py"):
                execfile(local_plugins_path + "/" + fn)

# Declare permissions for builtin views
config.declare_permission_section("view", "Builtin views")
for name, view in multisite_builtin_views.items():
    config.declare_permission("view.%s" % name,
            view["title"],
            "",
            config.roles)

# Add painter names to painter objects (e.g. for JSON web service)
for n, p in multisite_painters.items():
    p["name"] = n


max_display_columns   = 12
max_sort_columns      = 5

# Load all views - users or builtins
def load_views():
    html.multisite_views = {}

    # first load builtins. Set username to ''
    for name, view in multisite_builtin_views.items():
        view["owner"] = '' # might have been forgotten on copy action
        view["public"] = True
        view["name"] = name
        html.multisite_views[('', name)] = view

    # Now scan users subdirs for files "views.mk"
    subdirs = os.listdir(config.config_dir)
    for user in subdirs:
        try:
            dirpath = config.config_dir + "/" + user
            if os.path.isdir(dirpath):
                path = dirpath + "/views.mk"
                if not os.path.exists(path):
                    continue
                f = file(path, "r", 65536)
                sourcecode = f.read()
                t = 0
                while sourcecode == "": # This should never happen. But it happened. Don't know why.
                    # It's just a plain file. No fsync or stuff helped. Hack around a bit.
                    time.sleep(0.2)
                    sourcecode = f.read()
                    t += 1
                    if t > 10:
                        raise MKGeneralException("Cannot load views from %s/view.mk: file empty or not flushed" % dirpath)
                views = eval(sourcecode)
                for name, view in views.items():
                    view["owner"] = user
                    view["name"] = name
                    html.multisite_views[(user, name)] = view
        except SyntaxError, e:
            raise MKGeneralException("Cannot load views from %s/views.mk: %s" % (dirpath, e))

    html.available_views = available_views()

# Get the list of views which are available to the user
# (which could be retrieved with get_view)
def available_views():
    user = html.req.user
    views = {}

    # 1. user's own views, if allowed to edit views
    if config.may("edit_views"):
        for (u, n), view in html.multisite_views.items():
            if u == user:
                views[n] = view

    # 2. views of special users allowed to globally override builtin views
    for (u, n), view in html.multisite_views.items():
        if n not in views and view["public"] and config.user_may(u, "force_views"):
            views[n] = view

    # 3. Builtin views, if allowed.
    for (u, n), view in html.multisite_views.items():
        if u == '' and n not in views and config.may("view.%s" % n):
            views[n] = view

    # 4. other users views, if public. Sill make sure we honor permission
    #    for builtin views
    for (u, n), view in html.multisite_views.items():
        if n not in views and view["public"] and config.user_may(u, "publish_views"):
            # Is there a builtin view with the same name? If yes, honor permissions.
            if (u, n) in html.multisite_views and not config.may("view.%s" % n):
                continue
            views[n] = view

    return views


def save_views(us):
    userviews = {}
    for (user, name), view in html.multisite_views.items():
        if us == user:
            userviews[name] = view
    config.save_user_file("views", userviews)


# ----------------------------------------------------------------------
#   _____     _     _               __         _
#  |_   _|_ _| |__ | | ___    ___  / _| __   _(_) _____      _____
#    | |/ _` | '_ \| |/ _ \  / _ \| |_  \ \ / / |/ _ \ \ /\ / / __|
#    | | (_| | |_) | |  __/ | (_) |  _|  \ V /| |  __/\ V  V /\__ \
#    |_|\__,_|_.__/|_|\___|  \___/|_|     \_/ |_|\___| \_/\_/ |___/
#
# ----------------------------------------------------------------------
# Show list of all views with buttons for editing
def page_edit_views(h, msg=None):
    global html
    html = h
    if not config.may("edit_views"):
        raise MKAuthException("You are not allowed to edit views.")

    html.header("Edit views")
    html.write("<p>Here you can create and edit customizable <b>views</b>. A view "
            "displays monitoring status or log data by combining filters, sortings, "
            "groupings and other aspects.</p>")

    if msg: # called from page_edit_view() after saving
        html.message(msg)

    load_views()

    # Deletion of views
    delname = html.var("_delete")
    if delname and html.confirm("Please confirm the deletion of the view <tt>%s</tt>" % delname):
        del html.multisite_views[(html.req.user, delname)]
        save_views(html.req.user)
        # Reload sidebar (snapin views needs a refresh)
        html.javascript("top.frames[0].location.reload();");

    html.begin_form("create_view", "edit_view.py")
    html.write("<table class=views>\n")

    html.write("<tr><td class=legend colspan=7>")
    html.button("create", "Create new view")
    html.write(" for datasource: ")
    html.sorted_select("datasource", [ (k, v["title"]) for k, v in multisite_datasources.items() ])

    keys_sorted = html.multisite_views.keys()
    def cmp_viewkey(a, b):
        if a[0] == b[0]:
            if a[1] < b[1]:
                return -1
            else:
                return 1
        elif a[0] == "":
            return 1
        elif b[0] == "":
            return -1
        elif a[0] < b[0]:
            return -1
        else:
            return 1
    keys_sorted.sort(cmp_viewkey)
    first = True
    for (owner, viewname) in keys_sorted:
        if owner == "" and not config.may("view.%s" % viewname):
            continue
        view = html.multisite_views[(owner, viewname)]
        if owner == html.req.user or (view["public"] and (owner == "" or config.user_may(owner, "publish_views"))):
            if first:
                html.write("<tr><th>Name</th><th>Title / Description</th><th>Owner</th><th>Public</th><th>linked</th><th>Datasource</th><th></th></tr>\n")
                first = False
            html.write("<tr><td class=legend>%s</td>" % viewname)
            html.write("<td class=content>")
            if not view["hidden"]:
                html.write("<a href=\"view.py?view_name=%s\">%s</a>" % (viewname, view["title"]))
            else:
                html.write(view["title"])
            description = view.get("description")
            if description:
                html.write("<br><div class=viewdescription>%s</div>" % description)
            html.write("</td>")
            if owner == "":
                ownertxt = "<i>builtin</i>"
            else:
                ownertxt = owner
            html.write("<td class=content>%s</td>" % ownertxt)
            html.write("<td class=content>%s</td>" % (view["public"] and "yes" or "no"))
            html.write("<td class=content>%s</td>" % (view["hidden"] and "yes" or "no"))
            html.write("<td class=content>%s</td><td class=buttons>\n" % view["datasource"])
            if owner == "":
                buttontext = "Customize"
            else:
                buttontext = "Clone"
            backurl = htmllib.urlencode(html.makeuri([]))
            url = "edit_view.py?clonefrom=%s&load_view=%s&back=%s" % (owner, viewname, backurl)
            html.buttonlink(url, buttontext, True)
            if owner == html.req.user:
                html.buttonlink("edit_view.py?load_view=%s" % viewname, "Edit")
                html.buttonlink("edit_views.py?_delete=%s" % viewname, "Delete!", True)
            html.write("</td></tr>\n")

    html.write("</table>\n")
    html.end_form()
    html.footer()


def select_view(varname, only_with_hidden = False):
    choices = [("", "")]
    for name, view in html.available_views.items():
        if not only_with_hidden or len(view["hide_filters"]) > 0:
            choices.append(("%s" % name, view["title"]))
    html.sorted_select(varname, choices, "")

# -------------------------------------------------------------------------
#   _____    _ _ _    __     ___
#  | ____|__| (_) |_  \ \   / (_) _____      __
#  |  _| / _` | | __|  \ \ / /| |/ _ \ \ /\ / /
#  | |__| (_| | | |_    \ V / | |  __/\ V  V /
#  |_____\__,_|_|\__|    \_/  |_|\___| \_/\_/
#  Edit one view
# -------------------------------------------------------------------------
def page_edit_view(h):
    global html
    html = h
    if not config.may("edit_views"):
        raise MKAuthException("You are not allowed to edit views.")

    load_views()
    view = None

    # Load existing view from disk - and create a copy if 'clonefrom' is set
    viewname = html.var("load_view")
    oldname = viewname
    if viewname:
        cloneuser = html.var("clonefrom")
        if cloneuser != None:
            view = copy.copy(html.multisite_views.get((cloneuser, viewname), None))
            # Make sure, name is unique
            if cloneuser == html.req.user: # Clone own view
                newname = viewname + "_clone"
            else:
                newname = viewname
            # Name conflict -> try new names
            n = 1
            while (html.req.user, newname) in html.multisite_views:
                n += 1
                newname = viewname + "_clone%d" % n
            view["name"] = newname
            viewname = newname
            oldname = None # Prevent renaming
            if cloneuser == html.req.user:
                view["title"] += " (Copy)"
        else:
            view = html.multisite_views.get((html.req.user, viewname))

        datasourcename = view["datasource"]
        if view:
            load_view_into_html_vars(view)

    # set datasource name if a new view is being created
    elif html.var("datasource"):
        datasourcename = html.var("datasource")
    else:
        raise MKInternalError("No view name and not datasource defined.")


    # handle case of save or try or press on search button
    if html.var("save") or html.var("try") or html.var("search"):
        try:
            view = create_view()
            if html.var("save"):
                if html.check_transaction():
                    load_views()
                    html.multisite_views[(html.req.user, view["name"])] = view
                    oldname = html.var("old_name")
                    # Handle renaming of views -> delete old entry
                    if oldname and oldname != view["name"] and (html.req.user, oldname) in html.multisite_views:
                        del html.multisite_views[(html.req.user, oldname)]
                    save_views(html.req.user)
                return page_message_and_forward(h, "Your view has been saved.", "edit_views.py",
                        "<script type='text/javascript'>top.frames[0].location.reload();</script>\n")

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    html.header("Edit view")
    html.write("<table class=navi><tr>\n")
    html.write('<td class="left open">Edit</td>\n')
    html.write("<td class=gap></td>\n")
    html.write('<td class="right" onmouseover="hover_tab(this);" onmouseout="unhover_tab(this);">')
    html.write('<a href="edit_views.py">All views</a>\n')
    html.write('</td>\n')
    html.write("</tr><tr class=form><td class=form colspan=3><div class=whiteborder>\n")

    html.begin_form("view")
    html.hidden_field("back", html.var("back", ""))
    html.hidden_field("old_name", viewname) # safe old name in case user changes it
    html.write("<table class=form>\n")

    html.write("<tr><td class=legend>Title</td><td class=content>")
    html.text_input("view_title")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Linkname</td><td class=content>")
    html.text_input("view_name")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Topic</td><td class=content>")
    html.text_input("view_topic", "Other")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Buttontext</td><td class=content>")
    html.text_input("view_linktitle")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Description</td><td class=content>")
    html.text_area("view_description", 4)
    html.write("</td></tr>\n")

    # Larger sections are foldable and closed by default
    html.javascript("""
function toggle_section(nr, oImg) {
  var oContent =  document.getElementById("ed_"   + nr);
  var closed = oContent.style.display == "none";
  if (closed) {
    oContent.style.display = "";
    oImg.src = "images/open.gif";
  }
  else {
    oContent.style.display = "none";
    oImg.src = "images/closed.gif";
  }
  oContent = null;
  oImg = null;
}
""")

    def section_header(id, title):
        html.write("<tr><td class=legend>")
        html.write("<b class=toggleheader onclick=\"toggle_section('%d', this) \""
                   "title=\"Click to open this section\" "
                   "onmouseover=\"this.className='toggleheader hover';\" "
                   "onmouseout=\"this.className='toggleheader';\">%s</b> " % (id, title))
        html.write("</td><td class=content>")
        html.write("<div id=\"ed_%d\" style=\"display: none;\">" % id)

    def section_footer():
        html.write("</div></td></tr>\n")

    # Properties
    section_header(2, "Properties")
    datasource_title = multisite_datasources[datasourcename]["title"]
    html.write("Datasource: <b>%s</b><br>\n" % datasource_title)
    html.hidden_field("datasource", datasourcename)
    if config.may("publish_views"):
        html.checkbox("public")
        html.write(" make this view available for all users")
        html.write("<br />\n")
    html.checkbox("hidden")
    html.write(" hide this view from the sidebar")
    html.write("<br />\n")
    html.checkbox("mustsearch")
    html.write(" show data only on search<br>")
    html.checkbox("hidebutton")
    html.write(" do not show a context button to this view")
    section_footer()

    # [3] Filters
    section_header(3, "Filters")
    html.write("<table class=filters>")
    html.write("<tr><th>Filter</th><th>usage</th><th>hardcoded settings</th><th>HTML variables</th></tr>\n")
    allowed_filters = filters_allowed_for_datasource(datasourcename)
    # sort filters according to title
    s = [(filt.sort_index, filt.title, fname, filt) for fname, filt in allowed_filters.items()]
    s.sort()
    for sortindex, title, fname, filt in s:
        html.write("<tr>")
        html.write("<td class=title>%s" % title)
        if filt.comment:
            html.write("<br><div class=filtercomment>%s</div>" % filt.comment)
        html.write("</td>")
        html.write("<td class=usage>")
        html.sorted_select("filter_%s" % fname,
                [("off", "Don't use"),
                ("show", "Show to user"),
                ("hide", "Use for linking"),
                ("hard", "Hardcode")],
                "", "filter_activation(this.id)")
        html.write("</td><td class=widget>")
        filt.display()
        html.write("</td>")
        html.write("<td><tt>")
        html.write(" ".join(filt.htmlvars))
        html.write("</tt></td>")
        html.write("</tr>\n")
    html.write("</table>\n")
    html.write("<script language=\"javascript\">\n")
    for fname, filt in allowed_filters.items():
        html.write("filter_activation(\"filter_%s\");\n" % fname)
    html.write("</script>\n")
    section_footer()

    def sorter_selection(id, title, var_prefix, maxnum, data):
        allowed = allowed_for_datasource(data, datasourcename)
        section_header(id, title)
        # make sure, at least 3 selection boxes are free for new columns
        while html.has_var("%s%d" % (var_prefix, maxnum - 2)):
            maxnum += 1
        for n in range(1, maxnum + 1):
            collist = [ ("", "") ] + [ (name, p["title"]) for name, p in allowed.items() ]
            html.write("%02d " % n)
            html.sorted_select("%s%d" % (var_prefix, n), collist)
            html.write(" ")
            html.select("%sorder_%d" % (var_prefix, n), [("asc", "Ascending"), ("dsc", "Descending")])
            html.write("<br>")
        section_footer()

    def column_selection(id, title, var_prefix, data):
        allowed = allowed_for_datasource(data, datasourcename)
        section_header(id, title)
        # make sure, at least 3 selection boxes are free for new columns
        maxnum = 1
        while html.has_var("%s%d" % (var_prefix, maxnum)):
            maxnum += 1
        html.write('<div>')
        for n in range(1, maxnum):
            view_edit_column(n, var_prefix, maxnum, allowed)
        html.write('</div>')
        html.buttonlink("javascript:add_view_column(%d, '%s', '%s')" % (id, datasourcename, var_prefix), "Add Column")
        section_footer()

    # [4] Sorting
    sorter_selection(4, "Sorting", "sort_", max_sort_columns, multisite_sorters)

    # [5] Grouping
    column_selection(5, "Group by", "group_", multisite_painters)

    # [6] Columns (painters)
    column_selection(6, "Columns", "col_", multisite_painters)

    # [2] Layout
    section_header(7, "Layout")
    html.write("<table border=0>")
    html.write("<tr><td>Basic Layout:</td><td>")
    html.sorted_select("layout", [ (k, v["title"]) for k,v in multisite_layouts.items() if not v.get("hide")])
    html.write("</td></tr>\n")
    html.write("<tr><td>Number of columns:</td><td>")
    html.number_input("num_columns", 1)
    html.write("</td></tr>\n")
    html.write("<tr><td>Automatic reload (0 or empty for none):</td><td>")
    html.number_input("browser_reload", 0)
    html.write("</td></tr>\n")
    html.write("<tr><td>Play %s:</td><td>" % docu_link("multisite_sounds", "alarm sounds"))
    html.checkbox("play_sounds", False)
    html.write("</td></tr>\n")
    html.write("<tr><td>Column headers:</td><td>")
    html.select("column_headers", [ ("off", "off"), ("pergroup", "once per group") ])
    html.write("</td><tr>\n")
    html.write("</table>\n")
    section_footer()


    html.write('<tr><td class="legend button" colspan=2>')
    html.button("try", "Try out")
    html.write(" ")
    html.button("save", "Save")
    html.write("</table>\n")
    html.end_form()

    html.write("</div></td></tr></table>\n")

    if html.has_var("try") or html.has_var("search"):
        html.set_var("search", "on")
        if view:
            show_view(view, False, False)

    html.footer()

def view_edit_column(n, var_prefix, maxnum, allowed):
    collist = [ ("", "") ] + [ (name, p["title"]) for name, p in allowed.items() ]
    html.write("<div class=columneditor id=%seditor_%d><table><tr>" % (var_prefix, n))
    html.write('<td rowspan=3>')
    html.write('<img onclick="delete_view_column(this);" '
            'onmouseover=\"hilite_icon(this, 1)\" '
            'onmouseout=\"hilite_icon(this, 0)\" '
            'src="images/button_closesnapin_lo.png">')

    display = n == 1 and ' style="display:none;"' or ''
    html.write('<img id="%sup_%d" onclick="move_column_up(this);" '
            'onmouseover=\"hilite_icon(this, 1)\" '
            'onmouseout=\"hilite_icon(this, 0)\" '
            'src="images/button_moveup_lo.png"%s>' % (var_prefix, n, display))

    display = n == maxnum - 1 and ' style="display:none;"' or ''
    html.write('<img id="%sdown_%d" onclick="move_column_down(this);" '
            'onmouseover=\"hilite_icon(this, 1)\" '
            'onmouseout=\"hilite_icon(this, 0)\" '
            'src="images/button_movedown_lo.png"%s>' % (var_prefix, n, display))
    html.write('</td>')
    html.write('<td id="%slabel_%d" class=celeft>Column %d:</td><td>' % (var_prefix, n, n))
    html.sorted_select("%s%d" % (var_prefix, n), collist)
    html.write("</td></tr><tr><td class=celeft>Link:</td><td>")
    select_view("%slink_%d" % (var_prefix, n))
    html.write("</td></tr><tr><td class=celeft>Tooltip:</td><td>")
    html.sorted_select("%stooltip_%d" % (var_prefix, n), collist)
    html.write("</td></table>")
    html.write("</div>")

def ajax_get_edit_column(h):
    global html
    html = h
    if not config.may("edit_views"):
        raise MKAuthException("You are not allowed to edit views.")

    if not html.has_var('ds') or not html.has_var('num') or not html.has_var('pre'):
        raise MKInternalError("Missing attributes")

    load_views()

    allowed = allowed_for_datasource(multisite_painters, html.var('ds'))
    num = int(html.var('num', 0))

    html.form_vars = []
    view_edit_column(num, html.var('pre'), num + 1, allowed)

# Called by edit function in order to prefill HTML form
def load_view_into_html_vars(view):
    # view is well formed, not checks neccessary
    html.set_var("view_title",       view["title"])
    html.set_var("view_topic",       view.get("topic", "Other"))
    html.set_var("view_linktitle",   view.get("linktitle", view["title"]))
    html.set_var("view_description", view.get("description", ""))
    html.set_var("view_name",        view["name"])
    html.set_var("datasource",       view["datasource"])
    html.set_var("column_headers",   view.get("column_headers", "off"))
    html.set_var("layout",           view["layout"])
    html.set_var("num_columns",      view.get("num_columns", 1))
    html.set_var("browser_reload",   view.get("browser_reload", 0))
    html.set_var("play_sounds",      view.get("play_sounds", False) and "on" or "")
    html.set_var("public",           view["public"] and "on" or "")
    html.set_var("hidden",           view["hidden"] and "on" or "")
    html.set_var("mustsearch",       view["mustsearch"] and "on" or "")
    html.set_var("hidebutton",       view.get("hidebutton",  False) and "on" or "")

    # [3] Filters
    for name, filt in multisite_filters.items():
        if name in view["show_filters"]:
            html.set_var("filter_%s" % name, "show")
        elif name in view["hard_filters"]:
            html.set_var("filter_%s" % name, "hard")
        elif name in view["hide_filters"]:
            html.set_var("filter_%s" % name, "hide")

    for varname, value in view["hard_filtervars"]:
        if not html.has_var(varname):
            html.set_var(varname, value)

    # [4] Sorting
    n = 1
    for name, desc in view["sorters"]:
        html.set_var("sort_%d" % n, name)
        if desc:
            value = "dsc"
        else:
            value = "asc"
        html.set_var("sort_order_%d" % n, value)
        n +=1

    # [5] Grouping
    n = 1
    for entry in view["group_painters"]:
        name = entry[0]
        viewname = entry[1]
        tooltip = len(entry) > 2 and entry[2] or None
        html.set_var("group_%d" % n, name)
        if viewname:
            html.set_var("group_link_%d" % n, viewname)
        if tooltip:
            html.set_var("group_tooltip_%d" % n, tooltip)
        n += 1

    # [6] Columns
    n = 1
    for entry in view["painters"]:
        name = entry[0]
        viewname = entry[1]
        tooltip = len(entry) > 2 and entry[2] or None
        html.set_var("col_%d" % n, name)
        if viewname:
            html.set_var("col_link_%d" % n, viewname)
        if tooltip:
            html.set_var("col_tooltip_%d" % n, tooltip)
        n += 1

    # Make sure, checkboxes with default "on" do no set "on". Otherwise they
    # would always be on
    html.set_var("filled_in", "on")

# Extract properties of view from HTML variables and construct
# view object, to be used for saving or displaying
def create_view():
    name = html.var("view_name").strip()
    if name == "":
        raise MKUserError("view_name", "Please supply a unique name for the view, this will be used to specify that view in HTTP links.")
    if not re.match("^[a-zA-Z0-9_]+$", name):
        raise MKUserError("view_name", "The name of the view may only contain letters, digits and underscores.")
    title = html.var("view_title").strip()
    if title == "":
        raise MKUserError("view_title", "Please specify a title for your view")
    linktitle = html.var("view_linktitle").strip()
    if not linktitle:
        linktitle = title

    topic = html.var("view_topic")
    if not topic:
        topic = "Other"
    datasourcename = html.var("datasource")
    datasource = multisite_datasources[datasourcename]
    tablename = datasource["table"]
    layoutname = html.var("layout")
    try:
        num_columns = int(html.var("num_columns", 1))
        if num_columns < 1: num_columns = 1
        if num_columns > 50: num_columns = 50
    except:
        num_columns = 1

    try:
        browser_reload = int(html.var("browser_reload", 0))
        if browser_reload < 0: browser_reload = 0
    except:
        browser_reload = 0

    play_sounds    = html.var("play_sounds", "") != ""
    public         = html.var("public", "") != "" and config.may("publish_views")
    hidden         = html.var("hidden", "") != ""
    mustsearch     = html.var("mustsearch", "") != ""
    hidebutton     = html.var("hidebutton", "") != ""
    column_headers = html.var("column_headers")
    show_filternames = []
    hide_filternames = []
    hard_filternames = []
    hard_filtervars = []

    for fname, filt in multisite_filters.items():
        usage = html.var("filter_%s" % fname)
        if usage == "show":
            show_filternames.append(fname)
        elif usage == "hide":
            hide_filternames.append(fname)
        elif usage == "hard":
            hard_filternames.append(fname)
        if usage in [ "show", "hard" ]:
            for varname in filt.htmlvars:
                hard_filtervars.append((varname, html.var(varname, "")))

    sorternames = []
    for n in range(1, max_sort_columns+1):
        sname = html.var("sort_%d" % n)
        if sname:
            reverse = html.var("sort_order_%d" % n) == "dsc"
            sorternames.append((sname, reverse))

    group_painternames = []
    # User can set more than max_display_columns. We cannot easily know
    # how many variables he has set since holes are allowed. Let's silently
    # assume that 500 columns are enough. This surely is a hack, but if you
    # have read this comment you might want to mail me a (simple) patch for
    # doing this more cleanly...
    for n in range(1, 500):
        pname = html.var("group_%d" % n)
        viewname = html.var("group_link_%d" % n)
        tooltip = html.var("group_tooltip_%d" % n)
        if pname:
            if viewname not in  html.available_views:
                viewname = None
            group_painternames.append((pname, viewname, tooltip))

    painternames = []
    # User can set more than max_display_columns. We cannot easily know
    # how many variables he has set since holes are allowed. Let's silently
    # assume that 500 columns are enough. This surely is a hack, but if you
    # have read this comment you might want to mail me a (simple) patch for
    # doing this more cleanly...
    for n in range(1, 500):
        pname = html.var("col_%d" % n)
        viewname = html.var("col_link_%d" % n)
        tooltip = html.var("col_tooltip_%d" % n)
        if pname:
            if viewname not in  html.available_views:
                viewname = None
            painternames.append((pname, viewname, tooltip))

    return {
        "name"            : name,
        "owner"           : html.req.user,
        "title"           : title,
        "topic"           : topic,
        "linktitle"       : linktitle,
        "description"     : html.var("view_description", ""),
        "datasource"      : datasourcename,
        "public"          : public,
        "hidden"          : hidden,
        "mustsearch"      : mustsearch,
        "hidebutton"      : hidebutton,
        "layout"          : layoutname,
        "num_columns"     : num_columns,
        "browser_reload"  : browser_reload,
        "play_sounds"     : play_sounds,
        "column_headers"  : column_headers,
        "show_filters"    : show_filternames,
        "hide_filters"    : hide_filternames,
        "hard_filters"    : hard_filternames,
        "hard_filtervars" : hard_filtervars,
        "sorters"         : sorternames,
        "group_painters"  : group_painternames,
        "painters"        : painternames,
    }


# ---------------------------------------------------------------------
#  __     ___                       _
#  \ \   / (_) _____      __ __   _(_) _____      __
#   \ \ / /| |/ _ \ \ /\ / / \ \ / / |/ _ \ \ /\ / /
#    \ V / | |  __/\ V  V /   \ V /| |  __/\ V  V /
#     \_/  |_|\___| \_/\_/     \_/ |_|\___| \_/\_/
#
# ---------------------------------------------------------------------
# Show one view filled with data
def page_view(h):
    global html
    html = h

    load_views()
    view_name = html.var("view_name")
    view = html.available_views.get(view_name)
    if not view:
        raise MKGeneralException("No view defined with the name '%s'." % view_name)

    show_view(view, True, True, True)

# Display view with real data. This is *the* function everying
# is about.
def show_view(view, show_heading = False, show_buttons = True, show_footer = True):
    all_display_options = "HTBFCEOZRSIXD" 

    # Parse display options and
    if html.output_format == "html":
        display_options = html.var("display_options", "")
    else:
        display_options = all_display_options.lower()

    # If all display_options are upper case assume all not given values default
    # to lower-case. Vice versa when all display_options are lower case.
    # When the display_options are mixed case assume all unset options to be enabled
    do_defaults =  display_options.isupper() and all_display_options.lower() or all_display_options
    for c in do_defaults:
        if c.lower() not in display_options.lower():
            display_options += c
    html.display_options = display_options

    # [1] Datasource
    datasource = multisite_datasources[view["datasource"]]
    tablename = datasource["table"]

    # [2] Layout
    if html.output_format == "html":
        layout = multisite_layouts[view["layout"]]
    else:
        layout = multisite_layouts.get(html.output_format)
        if not layout:
            layout = multisite_layouts["json"]

    # User can override the layout settings via HTML variables (buttons)
    # which are safed persistently. This is known as "view options"
    vo = view_options(view["name"])
    num_columns    = vo.get("num_columns",   view.get("num_columns",    1))
    browser_reload = vo.get("refresh",       view.get("browser_reload", None))

    if browser_reload and 'R' in display_options:
        html.set_browser_reload(browser_reload)

    # [3] Filters
    show_filters = [ multisite_filters[fn] for fn in view["show_filters"] ]
    hide_filters = [ multisite_filters[fn] for fn in view["hide_filters"] ]
    hard_filters = [ multisite_filters[fn] for fn in view["hard_filters"] ]
    for varname, value in view["hard_filtervars"]:
        # shown filters are set, if form is fresh and variable not supplied in URL
        if not html.var("filled_in") and not html.has_var(varname):
            html.set_var(varname, value)

    # Prepare Filter headers for Livestatus
    filterheaders = ""
    only_sites = None
    all_active_filters = show_filters + hide_filters + hard_filters
    for filt in all_active_filters: 
        header = filt.filter(tablename)
        if header.startswith("Sites:"):
            only_sites = header.strip().split(" ")[1:]
        else:
            filterheaders += header

    query = filterheaders + view.get("add_headers", "")

    # [4] Sorting
    sorters = [ (multisite_sorters[sn], reverse) for sn, reverse in view["sorters"] ]

    # [5] Grouping
    group_painters = [ (multisite_painters[e[0]],) + e[1:] for e in view["group_painters"] ]

    # [6] Columns
    painters = [ (multisite_painters[e[0]],) + e[1:] for e in view["painters"] ]

    # Now compute this list of all columns we need to query via Livestatus.
    # Those are: (1) columns used by the sorters in use, (2) columns use by
    # column- and group-painters in use and - note - (3) columns used to
    # satisfy external references (filters) of views we link to. The last bit
    # is the trickiest. Also compute this list of view options use by the 
    # painters
    columns = []
    painter_options = []
    for s, r in sorters:
        columns += s["columns"]

    for entry in (group_painters + painters):
        p = entry[0]
        v = entry[1]
        columns += p["columns"]
        painter_options += p.get("options", [])
        if v:
            linkview = html.available_views.get(v)
            if linkview:
                for ef in linkview["hide_filters"]:
                    f = multisite_filters[ef]
                    columns += f.link_columns
        if len(entry) > 2 and entry[2]:
            tt = entry[2]
            columns += multisite_painters[tt]["columns"]

    painter_options = list(set(painter_options))
    painter_options.sort()

    # Add key columns, needed for executing commands
    columns += datasource["keys"]

    # Make column list unique and remove (implicit) site column
    colset = set(columns)
    if "site" in colset:
        colset.remove("site")
    columns = list(colset)

    # Fetch data. Some views show data only after pressing [Search]
    if (not view["mustsearch"]) or html.var("search"):
        # names for additional columns (through Stats: headers)
        add_columns = datasource.get("add_columns", [])

        # tablename may be a function instead of a livestatus tablename
        # In that case that function is used to compute the result.
        if type(tablename) == type(lambda x:None):
            rows = tablename(html, columns, query, only_sites, get_limit(), all_active_filters)
        else:
            rows = query_data(datasource, columns, add_columns, query, only_sites, get_limit())

        sort_data(rows, sorters)
    else:
        rows = []

    # Apply non-Livestatus filters
    for filter in all_active_filters:
        rows = filter.filter_table(rows)

    # Show heading (change between "preview" mode and full page mode)
    if show_heading:
        # Show/Hide the header with page title, MK logo, etc.
        if 'H' in display_options: 
            html.body_start(view_title(view))
        if 'T' in display_options:
            html.top_heading(view_title(view))

    has_done_actions = False

    if show_buttons and 'B' in display_options:
        show_context_links(view, hide_filters)

    need_navi = show_buttons and ('D' in display_options or 'F' in display_options or 'C' in display_options or 'O' in display_options or 'E' in display_options)
    if need_navi:
        html.write("<table class=navi><tr>\n")

        # Filter-button
        if 'F' in display_options and len(show_filters) > 0 and not html.do_actions():
            filter_isopen = html.var("search", "") == "" and view["mustsearch"]
            toggle_button("table_filter", filter_isopen, "Filter", ["filter"])
            html.write("<td class=minigap></td>\n")

        # Command-button
        if 'C' in display_options and len(rows) > 0 and config.may("act") and not html.do_actions():
            toggle_button("table_actions", False, "Commands")
            html.write("<td class=minigap></td>\n")

        # Painter-Options
        if 'D' in display_options and len(painter_options) > 0 and config.may("painter_options"):
            toggle_button("painter_options", False, "Display")
            html.write("<td class=minigap></td>\n")

        # Buttons for view options
        if 'O' in display_options:
            if config.user_may(config.user, "view_option_columns"):
                for col in config.view_option_columns:
                    uri = html.makeuri([("num_columns", col)])
                    if col == num_columns:
                        addclass = " selected"
                    else:
                        addclass = ""
                    html.write('<td class="left w30%s"><a href="%s">%s</a></td>\n' % (addclass, uri, col))
                    html.write("<td class=minigap></td>\n")

            if 'R' in display_options and config.user_may(config.user, "view_option_refresh"):
                for ref in config.view_option_refreshes:
                    uri = html.makeuri([("refresh", ref)])
                    if ref == browser_reload or (not ref and not browser_reload):
                        addclass = " selected"
                    else:
                        addclass = ""
                    if ref:
                        reftext = "%d s" % ref
                    else:
                        reftext = "&#8734;"
                    html.write('<td class="left w40%s" id="button-refresh-%s"><a href="%s">%s</a></td>\n' %
                                                                               (addclass, ref, uri, reftext))
                    html.write("<td class=minigap></td>\n")

        html.write("<td class=gap>&nbsp;</td>\n")

        # Customize/Edit view button
        if 'E' in display_options and config.may("edit_views"):
            backurl = htmllib.urlencode(html.makeuri([]))
            html.write('<td class="right" onmouseover="hover_tab(this);" onmouseout="unhover_tab(this);">')
            if view["owner"] == html.req.user:
                html.write('<a href="edit_view.py?load_view=%s&back=%s">Edit</a>\n' % (view["name"], backurl))
            else:
                html.write('<a href="edit_view.py?clonefrom=%s&load_view=%s&back=%s">Edit</a>\n' % (view["owner"], view["name"], backurl))
            html.write('</td>')

        html.write("</tr>")
        html.write("</table><table class=navi><tr>\n")

        # Filter form
        if 'F' in display_options and len(show_filters) > 0 and not html.do_actions():
            show_filter_form(filter_isopen, show_filters)

    # Actions
    if len(rows) > 0:
        if html.do_actions() and html.transaction_valid(): # submit button pressed, no reload
            try:
                if 'C' in display_options:
                    html.write("<tr class=form><td class=whiteborder>")
                # Create URI with all actions variables removed
                backurl = html.makeuri([])
                has_done_actions = do_actions(datasource["infos"][0], rows, backurl)
                if 'C' in display_options:
                    html.write("</td></tr>")
            except MKUserError, e:
                html.show_error(e.message)
                if 'C' in display_options:
                    html.write("</td></tr>")
                html.add_user_error(e.varname, e.message)
                if 'C' in display_options:
                    show_action_form(True, datasource)

        elif 'C' in display_options:
            show_action_form(False, datasource)

    if need_navi:
        if 'O' in display_options and len(painter_options) > 0 and config.may("painter_options"):
            show_painter_options(painter_options)

        # Ende des Bereichs mit den Tabs
        html.write("</table>\n") # class=navi


    if not has_done_actions:
        # Limit exceeded? Show warning
        count = len(rows)
        limit = get_limit()
        if limit != None and count == limit + 1:
            text = "Your query produced more then %d results. " % limit
            if html.var("limit", "soft") == "soft" and config.may("ignore_soft_limit"):
                text += '<a href="%s">Repeat query and allow more results.</a>' % html.makeuri([("limit", "hard")])
            elif html.var("limit") == "hard" and config.may("ignore_hard_limit"):
                text += '<a href="%s">Repeat query without limit.</a>' % html.makeuri([("limit", "none")])
            html.show_warning(text)
            del rows[-1]
        layout["render"](rows, view, group_painters, painters, num_columns)

        # Play alarm sounds, if critical events have been displayed
        if 'S' in display_options and view.get("play_sounds"):
            play_alarm_sounds()

    # In multi site setups error messages of single sites do not block the
    # output and raise now exception. We simply print error messages here:
    if config.show_livestatus_errors:
        for sitename, info in html.live.deadsites.items():
            html.show_error("<b>%s - Livestatus error</b><br>%s" % (info["site"]["alias"], info["exception"]))

    if show_footer:
        html.bottom_focuscode()
        if 'Z' in display_options:
            html.bottom_footer()
        if 'H' in display_options:
            html.body_end()

def view_options(viewname):
    # Options are stored per view. Get all options for all views
    vo = config.load_user_file("viewoptions", {}) 
    # Now get options for the view in question
    v = vo.get(viewname, {}) 
    must_save = False

    if config.user_may(config.user, "view_option_refresh"):
        if html.has_var("refresh"):
            try:
                v["refresh"] = int(html.var("refresh"))
            except:
                v["refresh"] = None
            must_save = True
    elif "refresh" in v:
        del v["refresh"]

    if config.user_may(config.user, "view_option_columns"):
        if html.has_var("num_columns"):
            try:
                v["num_columns"] = max(1, int(html.var("num_columns")))
            except:
                v["num_columns"] = 1
            must_save = True
    elif "num_columns" in v:
        del v["num_columns"]

    if config.user_may(config.user, "painter_options"):
        for on, opt in multisite_painter_options.items():
            if html.has_var(on):
                must_save = True
                # Make sure only allowed values are returned
                value = html.var(on)
                for val, title in opt["values"]:
                    if value == val:
                        v[on] = value
            elif on not in v:
                v[on] = opt["default"]
            opt["value"] = v[on]

    else:
        for on, opt in multisite_painter_options.items():
            del v[on]
            opt["value"] = None

    if must_save:
        vo[viewname] = v
        config.save_user_file("viewoptions", vo)
    return v


def play_alarm_sounds():
    url = config.sound_url
    if not url.endswith("/"):
        url += "/"
    for event, wav in config.sounds:
        if not event or html.has_event(event):
            html.play_sound(url + wav)
            break # only one sound at one time

# How many data rows may the user query?
def get_limit():
    limitvar = html.var("limit", "soft")
    if limitvar == "hard" and config.may("ignore_soft_limit"):
        return config.hard_query_limit
    elif limitvar == "none" and config.may("ignore_hard_limit"):
        return None
    else:
        return config.soft_query_limit

def view_title(view):
    extra_titles = [ ]
    datasource = multisite_datasources[view["datasource"]]
    tablename = datasource["table"]
    hide_filters = [ multisite_filters[fn] for fn in view["hide_filters"] ]
    for filt in hide_filters:
        heading = filt.heading_info(tablename)
        if heading:
            extra_titles.append(heading)
    return view["title"] + " " + ", ".join(extra_titles)

# Return title for context link buttons
def view_linktitle(view):
    t = view.get("linktitle")
    if not t:
        return view_title(view)
    else:
        return t


def show_context_links(thisview, active_filters):
    # compute list of html variables used actively by hidden or shown
    # filters.
    active_filter_vars = set([])
    for filt in active_filters:
        for var in filt.htmlvars:
            if html.has_var(var) and var not in active_filter_vars:
                active_filter_vars.add(var)

    # sort views after text of possible button (sort buttons after their text)
    sorted_views = []
    for view in html.available_views.values():
        sorted_views.append((view_linktitle(view), view))
    sorted_views.sort()

    first = True
    for linktitle, view in sorted_views:
        name = view["name"]
        if view == thisview:
            continue
        if view.get("hidebutton", False):
            continue # this view does not want a button to be displayed
        hidden_filternames = view["hide_filters"]
        used_contextvars = []
        skip = False
        for fn in hidden_filternames:
            filt = multisite_filters[fn]
            contextvars = filt.htmlvars
            # now extract those variables which are honored by this
            # view, regardless if used by hardcoded, shown or hidden filters.
            for var in contextvars:
                if var not in active_filter_vars:
                    skip = var
                    break
            used_contextvars += contextvars
            if skip:
                break
        if skip:
            continue

        # add context link to this view
        if len(used_contextvars) > 0:
            if first:
                first = False
                html.begin_context_buttons()
            vars_values = [ (var, html.var(var)) for var in set(used_contextvars) ]
            html.context_button(view_linktitle(view), html.makeuri_contextless(vars_values + [("view_name", name)]))

    if not first:
        html.end_context_buttons()


# Retrieve data via livestatus, convert into list of dicts,
# prepare row-function needed for painters
def query_data(datasource, columns, add_columns, add_headers, only_sites = [], limit = None):
    tablename = datasource["table"]
    add_headers += datasource.get("add_headers", "")
    merge_column = datasource.get("merge_by")
    if merge_column:
        columns = [merge_column] + columns

    # Most layouts need current state of object in order to
    # choose background color - even if no painter for state
    # is selected. Make sure those columns are fetched. This
    # must not be done for the table 'log' as it cannot correctly
    # distinguish between service_state and host_state
    if "log" not in datasource["infos"]:
        state_columns = []
        if "service" in datasource["infos"]:
            state_columns += [ "service_has_been_checked", "service_state" ]
        elif "host" in datasource["infos"]:
            state_columns += [ "host_has_been_checked", "host_state" ]
        for c in state_columns:
            if c not in columns:
                columns.append(c)

    # Remove columns which are implicitely added by the datasource
    columns = [ c for c in columns if c not in add_columns ]

    query = "GET %s\n" % tablename
    query += "Columns: %s\n" % " ".join(columns)
    query += add_headers
    html.live.set_prepend_site(True)
    if limit != None:
        html.live.set_limit(limit + 1) # + 1: We need to know, if limit is exceeded
    if config.debug and html.output_format == "html":
        html.write("<div class=message><tt>%s</tt></div>\n" % (query.replace('\n', '<br>\n')))

    if only_sites:
        html.live.set_only_sites(only_sites)
    data = html.live.query(query)
    html.live.set_only_sites(None)
    html.live.set_prepend_site(False)
    html.live.set_limit() # removes limit

    if merge_column:
        data = merge_data(data, columns)

    # convert lists-rows into dictionaries.
    # performance, but makes live much easier later.
    columns = ["site"] + columns + add_columns
    rows = [ dict(zip(columns, row)) for row in data ]

    return rows


# Merge all data rows with different sites but the same value
# in merge_column. We require that all column names are prefixed
# with the tablename. The column with the merge key is required
# to be the *second* column (right after the site column)
def merge_data(data, columns):
    merged = {}
    mergefuncs = [lambda a,b: ""] # site column is not merged

    def worst_service_state(a, b):
        if a == 2 or b == 2:
            return 2
        else:
            return max(a, b)

    def worst_host_state(a, b):
        if a == 1 or b == 1:
            return 1
        else:
            return max(a, b)

    for c in columns:
        tablename, col = c.split("_", 1)
        if col.startswith("num_") or col.startswith("members"):
            mergefunc = lambda a,b: a+b
        elif col.startswith("worst_service"):
            return worst_service_state
        elif col.startswith("worst_host"):
            return worst_host_state
        else:
            mergefunc = lambda a,b: a
        mergefuncs.append(mergefunc)

    for row in data:
        mergekey = row[1]
        if mergekey in merged:
            oldrow = merged[mergekey]
            merged[mergekey] = [ f(a,b) for f,a,b in zip(mergefuncs, oldrow, row) ]
        else:
            merged[mergekey] = row

    # return all rows sorted according to merge key
    mergekeys = merged.keys()
    mergekeys.sort()
    return [ merged[k] for k in mergekeys ]


# Sort data according to list of sorters. The tablename
# is needed in order to handle different column names
# for same objects (e.g. host_name in table services and
# simply name in table hosts)
def sort_data(data, sorters):
    if len(sorters) == 0:
        return
    elif len(sorters) == 1:
        data.sort(sorters[0][0]["cmp"], None, sorters[0][1])
        return

    sort_cmps = [(s["cmp"], (reverse and -1 or 1)) for s, reverse in sorters]

    def multisort(e1, e2):
        for func, neg in sort_cmps:
            c = neg * func(e1, e2)
            if c != 0: return c
        return 0 # equal

    data.sort(multisort)


# Create a list of filters allowed for a certain data source.
# Each filter is valid for a special info, e.g. "host" or
# "service". or always (info is None in that case).
# Each datasource provides a list of info. The datasource "services"
# provides "service" and "host", for example.
def filters_allowed_for_datasource(datasourcename):
    datasource = multisite_datasources[datasourcename]
    infos = datasource["infos"]
    allowed = {}
    for fname, filt in multisite_filters.items():
        if filt.info == None or filt.info in infos:
            allowed[fname] = filt
    return allowed

def painters_allowed_for_datasource(datasourcename):
    return allowed_for_datasource(multisite_painters, datasourcename)

def sorters_allowed_for_datasource(datasourcename):
    return allowed_for_datasource(multisite_sorters, datasourcename)

def list_in_list(a, b):
    for ele in a:
        if ele not in b:
            return False
    return True

# Filters a list of sorters or painters and decides which of
# those are available for a certain data source
def allowed_for_datasource(collection, datasourcename):
    datasource = multisite_datasources[datasourcename]
    infos_available = set(datasource["infos"])
    add_columns = datasource.get("add_columns", [])
    allowed = {}
    for name, item in collection.items():
        columns = item["columns"]
        infos_needed = set([ c.split("_", 1)[0] for c in columns if c != "site" and c not in add_columns])
        if len(infos_needed.difference(infos_available)) == 0:
            allowed[name] = item
    return allowed

# -----------------------------------------------------------------------------
#         _        _   _
#        / \   ___| |_(_) ___  _ __  ___
#       / _ \ / __| __| |/ _ \| '_ \/ __|
#      / ___ \ (__| |_| | (_) | | | \__ \
#     /_/   \_\___|\__|_|\___/|_| |_|___/
#
# -----------------------------------------------------------------------------

def show_action_form(is_open, datasource):
    if not config.may("act"):
        return

    # We take the first info to be the native data type of this table
    # and show actions useful for that
    what = datasource["infos"][0]
    # if what not in [ "host", "service", "comment", "downtime" ]:
    #   return # no actions on others

    # Table muss einen anderen Namen, als das Formular

    html.write("<tr class=form id=table_actions %s><td>" % (not is_open and 'style="display: none"' or '') )
    html.begin_form("actions")
    html.hidden_field("_do_actions", "yes")
    html.hidden_field("actions", "yes")
    html.hidden_fields() # set all current variables, exception action vars
    html.write("<div class=whiteborder>\n")
    html.write("<table class=form>\n")

    if what in [ "host", "service" ]:
        show_host_service_actions(what)
    elif what == "downtime":
        show_downtime_actions()
    elif what == "comment":
        show_comment_actions()
    else:
        html.write("<tr><td>No commands possible for %ss</td></tr>" % what)

    html.write("</table></div>\n")
    html.end_form()
    html.write("</td></tr>\n")

def show_downtime_actions():
    if config.may("action.downtimes"):
        html.write("<tr><td class=legend>Downtimes</td>\n"
                "<td class=content>\n"
                   "<input type=submit name=_remove_downtimes value=\"Remove\"> &nbsp; "
                   "</td></tr>\n")

def show_comment_actions():
    if config.may("action.addcomment"):
        html.write("<tr><td class=legend>Comments</td>\n"
                "<td class=content>\n"
                   "<input type=submit name=_remove_comments value=\"Remove\"> &nbsp; "
                   "</td></tr>\n")


def show_host_service_actions(what):
    if config.may("action.notifications"):
        html.write("<tr><td class=legend>Notifications</td>\n"
                   "<td class=content>\n"
                   "<input type=submit name=_enable_notifications value=\"Enable\"> &nbsp; "
                   "<input type=submit name=_disable_notifications value=\"Disable\"> &nbsp; "
                   "</td></tr>\n")

    if config.may("action.enablechecks") or config.may("action.reschedule"):
        html.write("<tr><td class=legend>Active checks</td>\n"
                   "<td class=content>\n")
        if config.may("action.enablechecks"):
            html.write("<input type=submit name=_enable_checks value=\"Enable\"> &nbsp; "
                   "<input type=submit name=_disable_checks value=\"Disable\"> &nbsp; ")
        if config.may("action.reschedule"):
            html.write("<input type=submit name=_resched_checks value=\"Reschedule next check now\">\n"
                   "</td></tr>\n")

    if config.may("action.enablechecks"):
        html.write("<tr><td class=legend>Passive checks</td>\n"
                   "<td class=content>\n")
        html.write("<input type=submit name=_enable_passive_checks value=\"Enable\"> &nbsp; "
               "<input type=submit name=_disable_passive_checks value=\"Disable\"> &nbsp; "
               "</td></tr>\n")

    if config.may("action.fakechecks"):
        if what == "service":
            states = ["Ok", "Warning", "Critical", "Unknown"]
        else:
            states = ["Up", "Down", "Unreachable"]
        html.write("<tr><td class=legend>Fake check results</td><td class=content>\n")
        for state in states:
            html.button("_fake", state)
            html.write(" ")
        html.write("</td></tr>\n")

    if config.may("action.acknowledge"):
        html.write("<tr><td rowspan=3 class=legend>Acknowledge</td>\n")
        html.write("<td class=content><input type=submit name=_acknowledge value=\"Acknowledge\"> &nbsp; "
                   "<input type=submit name=_remove_ack value=\"Remove Acknowledgement\"></td></tr>\n")

        html.write("<tr><td class=content>")
        html.checkbox("_ack_sticky", True)
        html.write(" sticky &nbsp; ")
        html.checkbox("_ack_notify", True)
        html.write(" send notification &nbsp; ")
        html.checkbox("_ack_persistent", False)
        html.write(" persistent comment")
        html.write("</td></tr>\n")

        html.write("<tr><td class=content><div class=textinputlegend>Comment:</div>")
        html.text_input("_ack_comment")
        html.write("</td></tr>\n")
        
    if config.may("action.addcomment"):
        html.write("<tr><td rowspan=2 class=legend>Add comment</td>\n")
        html.write("<td class=content><input type=submit name=_add_comment value=\"Add comment\"></td></tr>\n"
                "<tr><td class=content><div class=textinputlegend>Comment:</div>")
        html.text_input("_comment")
        html.write("</td></tr>\n")

    if config.may("action.downtimes"):
        html.write("<tr><td class=legend rowspan=4>Schedule Downtimes</td>\n"
                   "<td class=content>\n"
                   "<input type=submit name=_down_2h value=\"2 hours\"> "
                   "<input type=submit name=_down_today value=\"Today\"> "
                   "<input type=submit name=_down_week value=\"This week\"> "
                   "<input type=submit name=_down_month value=\"This month\"> "
                   "<input type=submit name=_down_year value=\"This year\"> "
                   " &nbsp; - &nbsp;"
                   "<input type=submit name=_down_remove value=\"Remove all\"> "
                   "</tr><tr>"
                   "<td class=content>"
                   "<input type=submit name=_down_custom value=\"Custom time range\"> &nbsp; ")
        html.datetime_input("_down_from", time.time())
        html.write("&nbsp; to &nbsp;")
        html.datetime_input("_down_to", time.time() + 7200)
        html.write("</td></tr>")
        html.write("<tr><td class=content>")
        html.checkbox("_down_flexible", False)
        html.write(" flexible with max. duration ")
        html.time_input("_down_duration", 2, 0)
        html.write(" (HH:MM)</td></tr>\n")
        html.write("<tr><td class=content><div class=textinputlegend>Comment:</div>\n")
        html.text_input("_down_comment")

def nagios_action_command(what, row):
    if what in [ "host", "service" ]:
        return nagios_host_service_action_command(what, row)
    elif what == "downtime":
        return nagios_downtime_command(row)
    elif what == "comment":
        return nagios_comment_command(row)

def nagios_downtime_command(row):
    id = row.get("downtime_id")
    prefix = "[%d] " % time.time()
    if html.var("_remove_downtimes"):
        if row.get("service_description"):
            command = prefix + "DEL_SVC_DOWNTIME;%d" % id
        else:
            command = prefix + "DEL_HOST_DOWNTIME;%d" % id
        return "remove the following", [command]

def nagios_comment_command(row):
    id = row.get("comment_id")
    prefix = "[%d] " % time.time()
    if html.var("_remove_comments"):
        if row.get("comment_type") == 1:
            command = prefix + "DEL_HOST_COMMENT;%d" % id
        else:
            command = prefix + "DEL_SVC_COMMENT;%d" % id
        return "remove the following", [command]

def nagios_host_service_action_command(what, dataset):
    host = dataset.get("host_name")
    descr = dataset.get("service_description")

    down_from = int(time.time())
    down_to = None
    if what == "host":
        spec = host
        cmdtag = "HOST"
        prefix = "host_"
    elif what == "service":
        spec = "%s;%s" % (host, descr)
        cmdtag = "SVC"
        prefix = "service_"
    else:
        raise MKInternalError("Sorry, no actions possible on table %s" % tablename)

    if html.var("_enable_notifications") and config.may("action.notifications"):
        command = "ENABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec
        title = "<b>enable notifications</b> for"

    elif html.var("_disable_notifications") and config.may("action.notifications"):
        command = "DISABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec
        title = "<b>disable notifications</b> for"

    elif html.var("_enable_checks") and config.may("action.enablechecks"):
        command = "ENABLE_" + cmdtag + "_CHECK;%s" % spec
        title = "<b>enable active checks</b> of"

    elif html.var("_disable_checks") and config.may("action.enablechecks"):
        command = "DISABLE_" + cmdtag + "_CHECK;%s" % spec
        title = "<b>disable active checks</b> of"

    elif html.var("_enable_passive_checks") and config.may("action.enablechecks"):
        command = "ENABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec
        title = "<b>enable passive checks</b> of"

    elif html.var("_disable_passive_checks") and config.may("action.enablechecks"):
        command = "DISABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec
        title = "<b>disable passive checks</b> of"

    elif html.var("_resched_checks") and config.may("action.reschedule"):
        command = "SCHEDULE_FORCED_" + cmdtag + "_CHECK;%s;%d" % (spec, int(time.time()))
        title = "<b>reschedule an immediate check</b> of"

    elif html.var("_fake") and config.may("action.fakechecks"):
        statename = html.var("_fake")
        pluginoutput =  "Manually set to %s by %s" % (statename, html.req.user)
        svcstate = {"Ok":0, "Warning":1, "Critical":2, "Unknown":3}.get(statename)
        if svcstate != None:
            command = "PROCESS_SERVICE_CHECK_RESULT;%s;%s;%s" % (spec, svcstate, pluginoutput)
        else:
            hoststate = {"Up":0, "Down":1, "Unreachable":2}.get(statename)
            if hoststate != None:
                command = "PROCESS_HOST_CHECK_RESULT;%s;%s;%s" % (spec, hoststate, pluginoutput)
        title = "<b>manually set check results to %s</b> for" % statename

    elif html.var("_acknowledge") and config.may("action.acknowledge"):
        comment = html.var_utf8("_ack_comment")
        if not comment:
            raise MKUserError("_ack_comment", "You need to supply a comment.")
        sticky = html.var("_ack_sticky") and 2 or 0
        sendnot = html.var("_ack_notify") and 1 or 0
        perscomm = html.var("_ack_persistent") and 1 or 0
        command = "ACKNOWLEDGE_" + cmdtag + "_PROBLEM;%s;%d;%d;%d;%s" % \
                      (spec, sticky, sendnot, perscomm, html.req.user) + (";%s" % comment)
        title = "<b>acknowledge the problems</b> of"

    elif html.var("_add_comment") and config.may("action.addcomment"):
        comment = html.var_utf8("_comment")
        if not comment:
            raise MKUserError("_comment", "You need to supply a comment.")
        command = "ADD_" + cmdtag + "_COMMENT;%s;1;%s" % \
                  (spec, html.req.user) + (";%s" % comment)
        title = "<b>add a comment to</b>"

    elif html.var("_remove_ack") and config.may("action.acknowledge"):
        command = "REMOVE_" + cmdtag + "_ACKNOWLEDGEMENT;%s" % spec
        title = "<b>remove acknowledgements</b> from"

    elif html.var("_down_2h") and config.may("action.downtimes"):
        down_to = down_from + 7200
        title = "<b>schedule an immediate 2-hour downtime</b> on"

    elif html.var("_down_today") and config.may("action.downtimes"):
        br = time.localtime(down_from)
        down_to = time.mktime((br.tm_year, br.tm_mon, br.tm_mday, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        title = "<b>schedule an immediate downtime until 24:00:00</b> on"

    elif html.var("_down_week") and config.may("action.downtimes"):
        br = time.localtime(down_from)
        wday = br.tm_wday
        days_plus = 6 - wday
        down_to = time.mktime((br.tm_year, br.tm_mon, br.tm_mday, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        down_to += days_plus * 24 * 3600
        title = "<b>schedule an immediate downtime until sunday night</b> on"

    elif html.var("_down_month") and config.may("action.downtimes"):
        br = time.localtime(down_from)
        new_month = br.tm_mon + 1
        if new_month == 13:
            new_year = br.tm_year + 1
            new_month = 1
        else:
            new_year = br.tm_year
        down_to = time.mktime((new_year, new_month, 1, 0, 0, 0, 0, 0, br.tm_isdst))
        title = "<b>schedule an immediate downtime until end of month</b> on"

    elif html.var("_down_year") and config.may("action.downtimes"):
        br = time.localtime(down_from)
        down_to = time.mktime((br.tm_year, 12, 31, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        title = "<b>schedule an immediate downtime until end of %d</b> on" % br.tm_year

    elif html.var("_down_custom") and config.may("action.downtimes"):
        down_from = html.get_datetime_input("_down_from")
        down_to   = html.get_datetime_input("_down_to")
        title = "<b>schedule a downtime from %s to %s</b> on " % (
            time.asctime(time.localtime(down_from)),
            time.asctime(time.localtime(down_to)))

    elif html.var("_down_remove") and config.may("action.downtimes"):
        downtime_ids = []
        for id in dataset[prefix + "downtimes"]:
            if id != "":
                downtime_ids.append(int(id))
        commands = []
        for dtid in downtime_ids:
            commands.append("[%d] DEL_%s_DOWNTIME;%d\n" % (int(time.time()), cmdtag, dtid))
        title = "<b>remove all scheduled downtimes</b> of "
        return title, commands

    else:
        raise MKUserError(None, "Sorry. This command is not implemented.")

    if down_to:
        comment = html.var_utf8("_down_comment")
        if not comment:
            raise MKUserError("_down_comment", "You need to supply a comment for your downtime.")
        if html.var("_down_flexible"):
            fixed = 0
            duration = html.get_time_input("_down_duration", "the duration")
        else:
            fixed = 1
            duration = 0
        command = (("SCHEDULE_" + cmdtag + "_DOWNTIME;%s;" % spec) \
                   + ("%d;%d;%d;0;%d;%s;" % (down_from, down_to, fixed, duration, html.req.user)) \
                   + comment)

    nagios_command = ("[%d] " % int(time.time())) + command + "\n"
    return title, [nagios_command]

def do_actions(what, rows, backurl):
    if not config.may("act"):
        html.show_error("You are not allowed to perform actions. If you think this is an error, "
              "please ask your administrator grant you the permission to do so.")
        return False # no actions done

    command = None
    title = nagios_action_command(what, rows[0])[0] # just get the title
    if not html.confirm("Do you really want to %s the following %d %ss?" % (title, len(rows), what)):
        return False # no actions done

    count = 0
    for row in rows:
        title, nagios_commands = nagios_action_command(what, row)
        for command in nagios_commands:
            if type(command) == unicode:
                command = command.encode("utf-8")
            html.live.command(command, row["site"])
            count += 1

    if command:
        message = "Successfully sent %d commands to Nagios." % count
        if config.debug:
            message += "The last one was: <pre>%s</pre>" % command
        if html.output_format == "html": # sorry for this hack
            message += '<br><a href="%s">Back to view</a>' % backurl
        html.message(message)
    elif count == 0:
        html.message("No matching service. No command sent.")
    return True

def get_context_link(user, viewname):
    if viewname in html.available_views:
        return "view.py?view_name=%s" % viewname
    else:
        return None

def ajax_export(h):
    global html
    html = h
    load_views()
    for name, view in html.available_views.items():
        view["owner"] = ''
        view["public"] = True
    html.write(pprint.pformat(html.available_views))


def page_message_and_forward(h, message, default_url, addhtml=""):
    global html
    html = h
    url = html.var("back")
    if not url:
        url = default_url

    html.set_browser_redirect(1, url)
    html.header("Multisite")
    html.message(message)
    html.write(addhtml)
    html.footer()

#   ____  _             _             _   _      _
#  |  _ \| |_   _  __ _(_)_ __       | | | | ___| |_ __   ___ _ __ ___
#  | |_) | | | | |/ _` | | '_ \ _____| |_| |/ _ \ | '_ \ / _ \ '__/ __|
#  |  __/| | |_| | (_| | | | | |_____|  _  |  __/ | |_) |  __/ |  \__ \
#  |_|   |_|\__,_|\__, |_|_| |_|     |_| |_|\___|_| .__/ \___|_|  |___/
#                 |___/                           |_|

def prepare_paint(p, row):
    painter = p[0]
    linkview = p[1]
    tooltip = len(p) > 2 and p[2] or None

    tdclass, content = painter["paint"](row)

    content = htmllib.utf8_to_entities(content)

    # Create contextlink to other view
    if content and linkview:
        content = link_to_view(content, row, linkview)

    # Tooltip
    if content != '' and tooltip:
        cla, txt = multisite_painters[tooltip]["paint"](row)
        tooltiptext = htmllib.strip_tags(txt)
        content = '<span title="%s">%s</span>' % (tooltiptext, content)
    return tdclass, content

def link_to_view(content, row, linkview):
    if 'I' not in html.display_options:
        return content

    view = html.available_views.get(linkview)
    if view:
        filters = [ multisite_filters[fn] for fn in view["hide_filters"] ]
        vars = []
        for filt in filters:
            vars += filt.variable_settings(row)
        do = html.var("display_options")
        if do:
            vars.append(("display_options", do))

        uri = "view.py?" + htmllib.urlencode_vars([("view_name", linkview)] + vars)
        content = "<a href=\"%s\">%s</a>" % (uri, content)
#        rel = 'view.py?view_name=hoststatus&site=local&host=erdb-lit&display_options=htbfcoezrsix'
#        content = '<a class=tips rel="%s" href="%s">%s</a>' % (rel, uri, content)
    return content

def docu_link(topic, text):
    return '<a href="%s" target="_blank">%s</a>' % (config.doculink_urlformat % topic, text)

def paint(p, row):
    tdclass, content = prepare_paint(p, row)
    if tdclass:
        html.write("<td class=\"%s\">%s</td>\n" % (tdclass, content))
    else:
        html.write("<td>%s</td>" % content)
    return content != ""

def paint_header(p):
    painter = p[0]
    t = painter.get("short", painter["title"])
    html.write("<th>%s</th>" % t)

def register_events(row):
    if config.sounds != []:
        host_state = row.get("host_hard_state", row.get("host_state"))
        if host_state != None:
            html.register_event({0:"up", 1:"down", 2:"unreachable"}[host_state])
        svc_state = row.get("service_last_hard_state", row.get("service_state"))
        if svc_state != None:
            html.register_event({0:"up", 1:"warning", 2:"critical", 3:"unknown"}[svc_state])

# The Group-value of a row is used for deciding wether
# two rows are in the same group or not
def group_value(row, group_painters):
    group = []
    for p in group_painters:
        groupvalfunc = p[0].get("groupby")
        if groupvalfunc:
            group.append(groupvalfunc(row))
        else:
            for c in p[0]["columns"]:
                group.append(row[c])
    return group

def get_painter_option(name):
    opt = multisite_painter_options[name]
    if not config.may("painter_options"):
        return opt["default"]
    return opt.get("value", opt["default"])

