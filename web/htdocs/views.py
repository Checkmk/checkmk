#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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
import weblib, traceback
from lib import *
from pagefunctions import *

max_display_columns   = 12
max_sort_columns      = 5

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

# Load all view plugins
def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
        return
    loaded_with_language = current_language

    global multisite_datasources     ; multisite_datasources      = {}
    global multisite_filters         ; multisite_filters          = {}
    global multisite_layouts         ; multisite_layouts          = {}
    global multisite_painters        ; multisite_painters         = {}
    global multisite_sorters         ; multisite_sorters          = {}
    global multisite_builtin_views   ; multisite_builtin_views    = {}
    global multisite_painter_options ; multisite_painter_options  = {}
    global multisite_commands        ; multisite_commands         = []
    global ubiquitary_filters        ; ubiquitary_filters         = [] # Always show this filters
    global view_hooks                ; view_hooks                 = {}

    config.declare_permission_section("action", _("Commands on host and services"))

    load_web_plugins("views", globals())

    # Declare permissions for builtin views
    config.declare_permission_section("view", _("Builtin views"))
    for name, view in multisite_builtin_views.items():
        config.declare_permission("view.%s" % name,
                view["title"],
                view["description"],
                config.roles)

    # Add painter names to painter objects (e.g. for JSON web service)
    for n, p in multisite_painters.items():
        p["name"] = n




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

    html.write("<table class=\"form\">\n")

    # sort filters according to title
    s = [(f.sort_index, f.title, f) for f in filters if f.available()]
    s.sort()
    col = 0
    for sort_index, title, f in s:
        if not f.visible():
            html.write('<div style="display:none">')
            f.display()
            html.write('</div>')
        else:
            if col == 0:
                html.write("<tr>")
            html.write("<td class=legend>%s</td>" % title)
            html.write("<td class=content>")
            f.display()
            html.write("</td>")
            if col == config.filter_columns - 1:
                html.write("</tr>\n")
            col = (col + 1) % config.filter_columns
    if col == 1:
        html.write("<td class=legend></td>\n<td class=content></td></tr>\n")
    html.write('<tr><td class="legend button" colspan=%d>' % (config.filter_columns * 2))
    html.button("search", _("Search"), "submit")
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

    html.write("<table class=\"form\">\n")
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
# name:          The unique id of that filter. This id is e.g. used in the
#                persisted view configuration
# title:         The title of the filter visible to the user. This text
#                may be localized
# info:          The datasource info this filter needs to work. If this
#                is "service", the filter will also be available in tables
#                showing service information. "host" is available in all
#                service and host views. The log datasource provides both
#                "host" and "service". Look into datasource.py for which
#                datasource provides which information
# htmlvars:      HTML variables this filter uses
# link_columns:  If this filter is used for linking (state "hidden"), then
#                these Livestatus columns are needed to fill the filter with
#                the proper information. In most cases, this is just []. Only
#                a few filters are useful for linking (such as the host_name and
#                service_description filters with exact match)
class Filter:
    def __init__(self, name, title, info, htmlvars, link_columns):
        self.name = name
        self.info = info
        self.title = title
        self.htmlvars = htmlvars
        self.link_columns = link_columns

    # Some filters can be unavailable due to the configuration (e.g.
    # the WATO Folder filter is only available if WATO is enabled.
    def available(self):
        return True

    # Some filters can be invisible. This is useful to hide filters which have always
    # the same value but can not be removed using available() because the value needs
    # to be set during runtime.
    # A good example is the "site" filter which does not need to be available to the
    # user in single site setups.
    def visible(self):
        return True

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
    user = config.user_id
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
def page_edit_views(msg=None):
    if not config.may("edit_views"):
        raise MKAuthException(_("You are not allowed to edit views."))

    html.header(_("Edit views"), stylesheets=["pages","views"])
    html.write(_("<p>Here you can create and edit customizable <b>views</b>. A view "
            "displays monitoring status or log data by combining filters, sortings, "
            "groupings and other aspects.</p>"))

    if msg: # called from page_edit_view() after saving
        html.message(msg)

    load_views()

    # Deletion of views
    delname = html.var("_delete")
    if delname and html.confirm(_("Please confirm the deletion of the view <tt>%s</tt>.") % delname):
        del html.multisite_views[(config.user_id, delname)]
        save_views(config.user_id)
        html.reload_sidebar();

    html.begin_form("create_view", "edit_view.py")
    html.write("<table class=views>\n")

    html.write("<tr><td class=legend colspan=8>")
    html.button("create", _("Create new view"))
    html.write(_(" for datasource: "))
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
        if owner == config.user_id or (view["public"] and (owner == "" or config.user_may(owner, "publish_views"))):
            if first:
                html.write("<tr><th>"+_('Name')+"</th><th>"+_('Title / Description')+"</th>"
                           "<th>"+_('Owner')+"</th><th>"+_('Public')+"</th><th>"+_('Hidden')+"</th>"
                           "<th>"+_('Mobile')+"</th>"
                           "<th>"+_('Datasource')+"</th><th></th></tr>\n")
                first = False
            html.write("<tr><td class=legend>%s</td>" % viewname)
            html.write("<td class=content>")
            if not view["hidden"]:
                html.write("<a href=\"view.py?view_name=%s\">%s</a>" % (viewname, view["title"]))
            else:
                html.write(view["title"])
            description = view.get("description")
            if description:
                html.write("<br><div class=viewdescription>%s</div>" % htmllib.attrencode(description))
            html.write("</td>")
            if owner == "":
                ownertxt = "<i>builtin</i>"
            else:
                ownertxt = owner
            html.write("<td class=content>%s</td>" % ownertxt)
            html.write("<td class=content>%s</td>" % (view["public"] and "yes" or "no"))
            html.write("<td class=content>%s</td>" % (view["hidden"] and "yes" or "no"))
            html.write("<td class=content>%s</td>" % (view.get("mobile") and "yes" or "no"))
            html.write("<td class=content>%s</td><td class=buttons>\n" % view["datasource"])
            if owner == "":
                buttontext = _("Customize")
            else:
                buttontext = _("Clone")
            backurl = htmllib.urlencode(html.makeuri([]))
            url = "edit_view.py?clonefrom=%s&load_view=%s&back=%s" % (owner, viewname, backurl)
            html.buttonlink(url, buttontext, True)
            if owner == config.user_id:
                html.buttonlink("edit_view.py?load_view=%s" % viewname, _("Edit"))
                html.buttonlink("edit_views.py?_delete=%s" % viewname, _("Delete!"), True)
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
def page_edit_view():
    if not config.may("edit_views"):
        raise MKAuthException(_("You are not allowed to edit views."))

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
            if cloneuser == config.user_id: # Clone own view
                newname = viewname + "_clone"
            else:
                newname = viewname
            # Name conflict -> try new names
            n = 1
            while (config.user_id, newname) in html.multisite_views:
                n += 1
                newname = viewname + "_clone%d" % n
            view["name"] = newname
            viewname = newname
            oldname = None # Prevent renaming
            if cloneuser == config.user_id:
                view["title"] += _(" (Copy)")
        else:
            view = html.multisite_views.get((config.user_id, viewname))
            if not view:
                view = html.multisite_views.get(('', viewname)) # load builtin view

        datasourcename = view["datasource"]
        if view:
            load_view_into_html_vars(view)

    # set datasource name if a new view is being created
    elif html.var("datasource"):
        datasourcename = html.var("datasource")
    else:
        raise MKInternalError(_("No view name and not datasource defined."))


    # handle case of save or try or press on search button
    if html.var("save") or html.var("try") or html.var("search"):
        try:
            view = create_view()
            if html.var("save"):
                if html.check_transaction():
                    load_views()
                    html.multisite_views[(config.user_id, view["name"])] = view
                    oldname = html.var("old_name")
                    # Handle renaming of views
                    if oldname and oldname != view["name"]:
                        # -> delete old entry
                        if (config.user_id, oldname) in html.multisite_views:
                            del html.multisite_views[(config.user_id, oldname)]
                        # -> change view_name in back parameter
                        if html.has_var('back'):
                            html.set_var('back', html.var('back', '').replace('view_name=' + oldname,
                                                                              'view_name=' + view["name"]))
                    save_views(config.user_id)
                return page_message_and_forward(_("Your view has been saved."), "edit_views.py",
                        "<script type='text/javascript'>if(top.frames[0]) top.frames[0].location.reload();</script>\n")

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    html.header(_("Edit view"), stylesheets=["pages","views"])
    html.write("<table class=navi><tr>\n")
    html.write('<td class="left open">%s</td>\n' % _('Edit'))
    html.write("<td class=gap></td>\n")
    html.write('<td class="right" onmouseover="hover_tab(this);" onmouseout="unhover_tab(this);">')
    html.write('<a href="edit_views.py">%s</a>\n' % _('All views'))
    html.write('</td>\n')
    html.write("</tr><tr class=form><td class=form colspan=3><div class=whiteborder>\n")

    html.begin_form("view")
    html.hidden_field("back", html.var("back", ""))
    html.hidden_field("old_name", viewname) # safe old name in case user changes it
    html.write("<table class=\"form\">\n")

    html.write("<tr><td class=legend>" + _("Title") + "</td><td class=content>")
    html.text_input("view_title", size=50)
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>" + _("Linkname") + "</td><td class=content>")
    html.text_input("view_name", size=12)
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>" + _("Topic") + "</td><td class=content>")
    html.text_input("view_topic", "Other", size=50)
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>" + _("Buttontext") + "</td><td class=content>")
    html.text_input("view_linktitle", size=26)
    html.write("&nbsp; Icon: ")
    html.text_input("view_icon", size=16)
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>" + _("Description") + "</td><td class=content>")
    html.text_area("view_description", "", 4)
    html.write("</td></tr>\n")

    # Larger sections are foldable and closed by default
    html.javascript("""
function toggle_section(nr, oImg) {
  var oContent = document.getElementById("ed_"   + nr);
  toggle_tree_state('vieweditor', nr, oContent);
  if (oContent.style.display == "none")
    toggle_folding(oImg, 0);
  else
    toggle_folding(oImg, 1);
  oContent = null;
}
""")


    def section_header(sid, title):
        html.write("<tr><td class=legend>")
        html.write("<img src=images/tree_00.png id=img_%d onclick=\"toggle_section('%d', this)\" class=toggleheader "
                   "title=\"Click to open this section\" "
                   "onmouseover=\"this.className='toggleheader hover';\" "
                   "onmouseout=\"this.className='toggleheader';\"><b>%s</b> " % (sid, sid, title))
        html.write("</td><td class=content>")
        html.write("<div id=\"ed_%d\" style=\"display: none;\">" % sid)

    def section_footer(sid):
        html.write("</div></td></tr>\n")
        # Open the section when the user had it open last time
        states = weblib.get_tree_states('vieweditor')
        if states.get(str(sid), 'off') == 'on':
            html.javascript('toggle_section("%d", document.getElementById("img_%s"))' % (sid, sid))

    # Properties
    sid = 2
    section_header(sid, _("Properties"))
    datasource_title = multisite_datasources[datasourcename]["title"]
    html.write("%s: <b>%s</b><br>\n" % (_('Datasource'), datasource_title))
    html.hidden_field("datasource", datasourcename)
    if config.may("publish_views"):
        html.checkbox("public")
        html.write(" " + _('make this view available for all users'))
        html.write("<br />\n")
    html.checkbox("hidden")
    html.write(" " + _('hide this view from the sidebar'))
    html.write("<br />\n")
    html.checkbox("mobile")
    html.write(" " + _('show this view in the Mobile GUI'))
    html.write("<br />\n")
    html.checkbox("mustsearch")
    html.write(" " + _('show data only on search') + "<br>")
    html.checkbox("hidebutton")
    html.write(" " + _('do not show a context button to this view'))
    section_footer(sid)

    # [3] Filters
    sid = 3
    section_header(sid, _("Filters"))
    html.write("<table class=filters>")
    html.write("<tr><th>")
    html.write(_("Filter"))
    html.write("</th><th>"+_('usage')+"</th><th>"+_('hardcoded settings')+"</th></tr>\n")
    allowed_filters = filters_allowed_for_datasource(datasourcename)
    # sort filters according to title
    s = [(filt.sort_index, filt.title, fname, filt)
          for fname, filt in allowed_filters.items()
          if fname not in ubiquitary_filters ]
    s.sort()
    for sortindex, title, fname, filt in s:
        html.write("<tr>")
        html.write("<td class=title>%s" % title)
        if filt.comment:
            html.write("<br><div class=filtercomment>%s</div>" % filt.comment)
        html.write("</td>")
        html.write("<td class=usage>")
        html.sorted_select("filter_%s" % fname,
                [("off", _("Don't use")),
                ("show", _("Show to user")),
                ("hide", _("Use for linking")),
                ("hard", _("Hardcode"))],
                "", "filter_activation(this.id)")
        html.write("</td><td class=widget>")
        filt.display()
        html.write("</td>")
        html.write("</tr>\n")
    html.write("</table>\n")
    # Set all filters into the proper display state
    html.write("<script language=\"javascript\">\n")
    for fname, filt in allowed_filters.items():
        if fname not in ubiquitary_filters:
            html.write("filter_activation(\"filter_%s\");\n" % fname)
    html.write("</script>\n")
    section_footer(sid)

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
            html.select("%sorder_%d" % (var_prefix, n), [("asc", _("Ascending")), ("dsc", _("Descending"))])
            html.write("<br>")
        section_footer(id)

    def column_selection(id, title, var_prefix, data):
        allowed = allowed_for_datasource(data, datasourcename)

        joined = []
        if var_prefix == 'col_':
            joined  = allowed_for_joined_datasource(data, datasourcename)

        section_header(id, title)
        # make sure, at least 3 selection boxes are free for new columns
        maxnum = 1
        while html.has_var("%s%d" % (var_prefix, maxnum)):
            maxnum += 1
        html.write('<div>')
        for n in range(1, maxnum):
            view_edit_column(n, var_prefix, maxnum, allowed, joined)
        html.write('</div>')
        html.jsbutton('add_column', _("Add Column"), "add_view_column(%d, '%s', '%s')" % (id, datasourcename, var_prefix))
        section_footer(id)

    # [4] Sorting
    sorter_selection(4, _("Sorting"), "sort_", max_sort_columns, multisite_sorters)

    # [5] Grouping
    column_selection(5, _("Group by"), "group_", multisite_painters)

    # [6] Columns (painters)
    column_selection(6, _("Columns"), "col_", multisite_painters)

    # [7] Layout
    sid = 7
    section_header(sid, _("Layout"))
    html.write("<table border=0>")
    html.write("<tr><td>%s:</td><td>" % _('Basic Layout'))
    html.sorted_select("layout", [ (k, v["title"]) for k,v in multisite_layouts.items() if not v.get("hide")])
    html.write("</td></tr>\n")
    html.write("<tr><td>%s:</td><td>" % _('Number of columns'))
    html.number_input("num_columns", 1)
    html.write("</td></tr>\n")
    html.write("<tr><td>%s:</td><td>" % _('Automatic reload (0 or empty for none)'))
    html.number_input("browser_reload", 0)
    html.write("</td></tr>\n")
    html.write("<tr><td>%s %s:</td><td>" % (_('Play'), docu_link("multisite_sounds", _("alarm sounds"))))
    html.checkbox("play_sounds", False)
    html.write("</td></tr>\n")
    html.write("<tr><td>%s:</td><td>" % _('Column headers'))

    # 1.1.11i3: Fix deprecated column_header option: perpage -> pergroup
    # This should be cleaned up someday
    if html.var("column_headers") == 'perpage':
        html.set_var("column_headers", 'pergroup')

    html.select("column_headers", [ ("off", _("off")), ("pergroup", _("once per group")) ])
    html.write("</td><tr>\n")
    html.write("<tr><td>%s:</td><td>" % _('Sortable by user'))
    html.checkbox('user_sortable', True)
    html.write("</td><tr>\n")
    html.write("<tr><td>%s:</td><td>" % _('Show check boxes'))
    html.checkbox('show_checkboxes', False)
    html.write("</td><tr>\n")
    html.write("</table>\n")
    section_footer(sid)


    html.write('<tr><td class="legend button" colspan=2>')
    html.button("save", _("Save"))
    html.write(" ")
    html.button("try", _("Try out"))
    html.write("</td></tr></table>\n")
    html.end_form()

    html.write("</div></td></tr></table>\n")

    if html.has_var("try") or html.has_var("search"):
        html.set_var("search", "on")
        if view:
            show_view(view, False, False)

    html.footer()

def view_edit_column(n, var_prefix, maxnum, allowed, joined = []):

    collist = [ ("", "") ] + collist_of_collection(allowed)
    if joined:
        collist += [ ("-", "---") ] + collist_of_collection(joined, collist)

    html.write("<div class=columneditor id=%seditor_%d><table><tr>" % (var_prefix, n))
    html.write('<td class="cebuttons" rowspan=5>')
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
    html.write('<td id="%slabel_%d" class=celeft>%s %d:</td><td>' % (var_prefix, n, _('Column'), n))
    html.select("%s%d" % (var_prefix, n), collist, "", "toggle_join_fields('%s', %d, this)" % (var_prefix, n))
    display = 'none'
    if joined and is_joined_value(collist, "%s%d" % (var_prefix, n)):
        display = ''
    html.write("</td></tr><tr id='%sjoin_index_row%d' style='display:%s'><td class=celeft>%s:</td><td>" %
                                                                    (var_prefix, n, display, _('of Service')))
    html.text_input("%sjoin_index_%d" % (var_prefix, n))
    html.write("</td></tr><tr><td class=celeft>%s:</td><td>" % _('Link'))
    select_view("%slink_%d" % (var_prefix, n))
    html.write("</td></tr><tr><td class=celeft>%s:</td><td>" % _('Tooltip'))
    html.select("%stooltip_%d" % (var_prefix, n), collist)
    html.write("</td></tr><tr id='%stitle_row%d' style='display:%s'><td class=celeft>%s:</td><td>" %
                                                                       (var_prefix, n, display, _('Title')))
    html.text_input("%stitle_%d" % (var_prefix, n))
    html.write("</td></tr></table>")
    html.write("</div>")

def ajax_get_edit_column():
    if not config.may("edit_views"):
        raise MKAuthException(_("You are not allowed to edit views."))

    if not html.has_var('ds') or not html.has_var('num') or not html.has_var('pre'):
        raise MKInternalError(_("Missing attributes"))

    load_views()

    allowed = allowed_for_datasource(multisite_painters, html.var('ds'))

    joined = []
    if html.var('pre') == 'col_':
        joined  = allowed_for_joined_datasource(multisite_painters, html.var('ds'))

    num = int(html.var('num', 0))

    html.form_vars = []
    view_edit_column(num, html.var('pre'), num + 1, allowed, joined)

# Called by edit function in order to prefill HTML form
def load_view_into_html_vars(view):
    # view is well formed, not checks neccessary
    html.set_var("view_title",       view["title"])
    html.set_var("view_topic",       view.get("topic", "Other"))
    html.set_var("view_linktitle",   view.get("linktitle", view["title"]))
    html.set_var("view_icon",        view.get("icon")),
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
    html.set_var("mobile",           view.get("mobile") and "on" or "")
    html.set_var("mustsearch",       view["mustsearch"] and "on" or "")
    html.set_var("hidebutton",       view.get("hidebutton",  False) and "on" or "")
    html.set_var("user_sortable",    view.get("user_sortable", True) and "on" or "")
    html.set_var("show_checkboxes",  view.get("show_checkboxes", False) and "on" or "")

    # [3] Filters
    for name, filt in multisite_filters.items():
        if name not in ubiquitary_filters:
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
        name       = entry[0]
        viewname   = entry[1]
        tooltip    = len(entry) > 2 and entry[2] or None
        join_index = len(entry) > 3 and entry[3] or None
        col_title  = len(entry) > 4 and entry[4] or None
        html.set_var("col_%d" % n, name)
        if viewname:
            html.set_var("col_link_%d" % n, viewname)
        if tooltip:
            html.set_var("col_tooltip_%d" % n, tooltip)
        if join_index:
            html.set_var("col_join_index_%d" % n, join_index)
        if col_title:
            html.set_var("col_title_%d" % n, col_title)
        n += 1

    # Make sure, checkboxes with default "on" do no set "on". Otherwise they
    # would always be on
    html.set_var("filled_in", "create_view")

# Extract properties of view from HTML variables and construct
# view object, to be used for saving or displaying
def create_view():
    name = html.var("view_name").strip()
    if name == "":
        raise MKUserError("view_name", _("Please supply a unique name for the view, this will be used to specify that view in HTTP links."))
    if not re.match("^[a-zA-Z0-9_]+$", name):
        raise MKUserError("view_name", _("The name of the view may only contain letters, digits and underscores."))
    title = html.var_utf8("view_title").strip()
    if title == "":
        raise MKUserError("view_title", _("Please specify a title for your view."))
    linktitle = html.var("view_linktitle").strip()
    if not linktitle:
        linktitle = title
    icon = html.var("view_icon")
    if not icon:
        icon = None

    topic = html.var_utf8("view_topic")
    if not topic:
        topic = _("Other")
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

    play_sounds      = html.var("play_sounds", "") != ""
    public           = html.var("public", "") != "" and config.may("publish_views")
    hidden           = html.var("hidden", "") != ""
    mobile           = html.var("mobile", "") != ""
    mustsearch       = html.var("mustsearch", "") != ""
    hidebutton       = html.var("hidebutton", "") != ""
    column_headers   = html.var("column_headers")
    user_sortable    = html.var("user_sortable")
    show_checkboxes  = html.var("show_checkboxes")

    show_filternames = []
    hide_filternames = []
    hard_filternames = []
    hard_filtervars  = []

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
        pname      = html.var("col_%d" % n)
        viewname   = html.var("col_link_%d" % n)
        tooltip    = html.var("col_tooltip_%d" % n)
        join_index = html.var('col_join_index_%d' % n)
        col_title  = html.var('col_title_%d' % n)
        if pname and pname != '-':
            if viewname not in  html.available_views:
                viewname = None

            allowed_cols = collist_of_collection(allowed_for_datasource(multisite_painters, datasourcename))
            joined_cols  = collist_of_collection(allowed_for_joined_datasource(multisite_painters, datasourcename), allowed_cols)
            if is_joined_value(joined_cols, "col_%d" % n) and not join_index:
                raise MKUserError('col_join_index_%d' % n, "Please specify the service to show the data for")

            if join_index and col_title:
                painternames.append((pname, viewname, tooltip, join_index, col_title))
            elif join_index:
                painternames.append((pname, viewname, tooltip, join_index))
            else:
                painternames.append((pname, viewname, tooltip))

    if len(painternames) == 0:
        raise MKUserError("col_1", _("Please add at least one column to your view."))

    return {
        "name"            : name,
        "owner"           : config.user_id,
        "title"           : title,
        "topic"           : topic,
        "linktitle"       : linktitle,
        "icon"            : icon,
        "description"     : html.var_utf8("view_description", ""),
        "datasource"      : datasourcename,
        "public"          : public,
        "hidden"          : hidden,
        "mobile"          : mobile,
        "mustsearch"      : mustsearch,
        "hidebutton"      : hidebutton,
        "layout"          : layoutname,
        "num_columns"     : num_columns,
        "browser_reload"  : browser_reload,
        "play_sounds"     : play_sounds,
        "column_headers"  : column_headers,
        "user_sortable"   : user_sortable,
        "show_checkboxes" : show_checkboxes,
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
def page_view():
    bi.reset_cache_status() # needed for status icon

    load_views()
    view_name = html.var("view_name")
    if view_name == None:
        raise MKGeneralException("Missing the variable view_name in the URL.")
    view = html.available_views.get(view_name)
    if not view:
        raise MKGeneralException("No view defined with the name '%s'." % view_name)

    show_view(view, True, True, True)


# Get a list of columns we need to fetch in order to
# render a given list of painters. If join_columns is True,
# then we only return the list needed by "Join" columns, i.e.
# columns that need to fetch information from another table
# (e.g. from the services table while we are in a hosts view)
# If join_columns is False, we only return the "normal" columns.
def get_needed_columns(painters):
    columns = []
    for entry in painters:
        p = entry[0]
        v = entry[1]
        columns += p["columns"]
        if v:
            linkview = html.available_views.get(v)
            if linkview:
                for ef in linkview["hide_filters"]:
                    f = multisite_filters[ef]
                    columns += f.link_columns
        if len(entry) > 2 and entry[2]:
            tt = entry[2]
            columns += multisite_painters[tt]["columns"]
    return columns


# Display options are flags that control which elements of a
# view should be displayed (buttons, sorting, etc.). They can be
# specified via the URL variable display_options. The function
# extracts this variable, applies defaults and generates
# three versions of the display options:
# Return value -> display options to actually use
# html.display_options -> display options to use in for URLs to other views
# html.title_display_options -> display options for title sorter links
def prepare_display_options():
    # Display options (upper-case: show, lower-case: don't show)
    # H  The HTML header and body-tag (containing the tags <HTML> and <BODY>)
    # T  The title line showing the header and the logged in user
    # B  The blue context buttons that link to other views
    # F  The tab for using filters
    # C  The tab for using commands and all icons for commands (e.g. the reschedule icon)
    # O  The view options number of columns and refresh
    # D  The Display tab, which contains column specific formatting settings
    # E  The tab for editing the view
    # Z  The footer line, where refresh: 30s is being displayed
    # R  The auto-refreshing in general (browser reload)
    # S  The playing of alarm sounds (on critical and warning services)
    # I  All hyperlinks pointing to other views
    # X  All other hyperlinks (pointing to external applications like PNP, WATO or others)
    # M  If this option is not set, then all hyperlinks are targeted to the HTML frame
    #    with the name main. This is useful when using views as elements in the dashboard.
    # L  The column title links in multisite views
    # W  The limit and livestatus error message in views
    all_display_options = "HTBFCEOZRSIXDMLW"

    # Parse display options and
    if html.output_format == "html":
        display_options = html.var("display_options", "")
    else:
        display_options = all_display_options.lower()

    # If all display_options are upper case assume all not given values default
    # to lower-case. Vice versa when all display_options are lower case.
    # When the display_options are mixed case assume all unset options to be enabled
    def apply_display_option_defaults(opts):
        do_defaults = opts.isupper() and all_display_options.lower() or all_display_options
        for c in do_defaults:
            if c.lower() not in opts.lower():
                opts += c
        return opts

    display_options = apply_display_option_defaults(display_options)
    # Add the display_options to the html object for later linking etc.
    html.display_options = display_options

    # This is needed for letting only the data table reload. The problem is that
    # the data table is re-fetched via javascript call using special display_options
    # but these special display_options must not be used in links etc. So we use
    # a special var _display_options for defining the display_options for rendering
    # the data table to be reloaded. The contents of "display_options" are used for
    # linking to other views.
    if html.has_var('_display_options'):
        display_options = html.var("_display_options", "")
        display_options = apply_display_option_defaults(display_options)
        html.display_options = display_options

    # But there is one special case: The sorter links! These links need to know
    # about the provided display_option parameter. The links could use
    # "html.display_options" but this contains the implicit options which should
    # not be added to the URLs. So the real parameters need to be preserved for
    # this case. It is stored in the var "html.display_options"
    if html.var('display_options'):
        html.title_display_options = html.var("display_options")

    # If display option 'M' is set, then all links are targetet to the 'main'
    # frame. Also the display options are removed since the view in the main
    # frame should be displayed in standard mode.
    if 'M' not in display_options:
        html.set_link_target("main")
        html.del_var("display_options")

    # Below we have the following display_options vars:
    # html.display_options        - Use this when rendering the current view
    # html.var("display_options") - Use this for linking to other views
    return display_options


# Display view with real data. This is *the* function everying
# is about.
def show_view(view, show_heading = False, show_buttons = True,
              show_footer = True, render_function = None, only_count=False):
    display_options = prepare_display_options()

    # User can override the layout settings via HTML variables (buttons)
    # which are safed persistently. This is known as "view options"
    vo = view_options(view["name"])
    num_columns     = vo.get("num_columns",     view.get("num_columns",    1))
    browser_reload  = vo.get("refresh",         view.get("browser_reload", None))
    show_checkboxes = vo.get("show_checkboxes", view.get("show_checkboxes", False))

    # Get the datasource (i.e. the logical table)
    datasource = multisite_datasources[view["datasource"]]
    tablename = datasource["table"]

    # Filters to show in the view
    show_filters = [ multisite_filters[fn] for fn in view["show_filters"] ]

    # add ubiquitary_filters that are possible for this datasource
    for fn in ubiquitary_filters:
        # Disable 'filename' filter, if WATO is disabled
        if fn == "filename" and not config.wato_enabled:
            continue
        filter = multisite_filters[fn]
        if not filter.info or filter.info in datasource["infos"]:
            show_filters.append(filter)

    hide_filters = [ multisite_filters[fn] for fn in view["hide_filters"] ]
    hard_filters = [ multisite_filters[fn] for fn in view["hard_filters"] ]

    for varname, value in view["hard_filtervars"]:
        # shown filters are set, if form is fresh and variable not supplied in URL
        if only_count or (html.var("filled_in") != "filter" and not html.has_var(varname)):
            html.set_var(varname, value)

    # Prepare Filter headers for Livestatus
    filterheaders = ""
    only_sites = None
    all_active_filters = [ f for f in show_filters + hide_filters + hard_filters if f.available() ]
    for filt in all_active_filters:
        header = filt.filter(tablename)
        if header.startswith("Sites:"):
            only_sites = header.strip().split(" ")[1:]
        else:
            filterheaders += header

    query = filterheaders + view.get("add_headers", "")

    # Sorting - use view sorters and URL supplied sorters
    if not only_count:
        sorter_list = html.has_var('sort') and parse_url_sorters(html.var('sort')) or view["sorters"]
        sorters = [ (multisite_sorters[s[0]],) + s[1:] for s in sorter_list ]
    else:
        sorters = []

    # Prepare gropuing information
    group_painters = [ (multisite_painters[e[0]],) + e[1:] for e in view["group_painters"] ]

    # Prepare columns to paint
    painters = [ (multisite_painters[e[0]],) + e[1:] for e in view["painters"] ]

    # Now compute the list of all columns we need to query via Livestatus.
    # Those are: (1) columns used by the sorters in use, (2) columns use by
    # column- and group-painters in use and - note - (3) columns used to
    # satisfy external references (filters) of views we link to. The last bit
    # is the trickiest. Also compute this list of view options use by the
    # painters

    all_painters = group_painters + painters
    join_painters = [ p for p in all_painters if len(p) >= 4 ]
    master_painters = [ p for p in all_painters if len(p) < 4 ]
    columns      = get_needed_columns(master_painters)
    join_columns = get_needed_columns(join_painters)

    # Columns needed for sorters
    for s in sorters:
        if len(s) == 2:
            columns += s[0]["columns"]
        else:
            join_columns += s[0]["columns"]

    # Add key columns, needed for executing commands
    columns += datasource["keys"]

    # Add idkey columns, needed for identifying the row
    columns += datasource["idkeys"]

    # Make column list unique and remove (implicit) site column
    colset = set(columns)
    if "site" in colset:
        colset.remove("site")
    columns = list(colset)

    # Get list of painter options we need to display (such as PNP time range
    # or the format being used for timestamp display)
    painter_options = []
    for entry in all_painters:
        p = entry[0]
        painter_options += p.get("options", [])
    painter_options = list(set(painter_options))
    painter_options.sort()

    # Fetch data. Some views show data only after pressing [Search]
    if (only_count or (not view["mustsearch"]) or html.var("filled_in") == "filter"):
        # names for additional columns (through Stats: headers)
        add_columns = datasource.get("add_columns", [])

        # tablename may be a function instead of a livestatus tablename
        # In that case that function is used to compute the result.

        if type(tablename) == type(lambda x:None):
            rows = tablename(columns, query, only_sites, get_limit(), all_active_filters)
        else:
            rows = query_data(datasource, columns, add_columns, query, only_sites, get_limit())

        # Now add join information, if there are join columns
        if len(join_painters) > 0:
            do_table_join(datasource, rows, filterheaders, join_painters, join_columns, only_sites)

        sort_data(rows, sorters)
    else:
        rows = []

    # Apply non-Livestatus filters
    for filter in all_active_filters:
        rows = filter.filter_table(rows)

    # TODO: Use livestatus Stats: instead of fetching rows!
    if only_count:
        for varname, value in view["hard_filtervars"]:
            html.del_var(varname)
        return len(rows)

    # Set browser reload
    if browser_reload and 'R' in display_options and not only_count:
        html.set_browser_reload(browser_reload)

    # The layout of the view: it can be overridden by several specifying
    # an output format (like json or python).
    if html.output_format == "html":
        layout = multisite_layouts[view["layout"]]
    else:
        layout = multisite_layouts.get(html.output_format)
        if not layout:
            layout = multisite_layouts["json"]

    # Until now no single byte of HTML code has been output.
    # Now let's render the view.
    if not render_function:
        render_function = render_view

    render_function(view, rows, datasource, group_painters, painters,
                display_options, painter_options, show_heading, show_buttons,
                show_checkboxes, layout, num_columns, show_filters, show_footer, hide_filters,
                browser_reload)


# Output HTML code of a view. If you add or remove paramters here,
# then please also do this in htdocs/mobile.py!
def render_view(view, rows, datasource, group_painters, painters,
                display_options, painter_options, show_heading, show_buttons,
                show_checkboxes, layout, num_columns, show_filters, show_footer, hide_filters,
                browser_reload):


    # Show heading (change between "preview" mode and full page mode)
    if show_heading:
        # Show/Hide the header with page title, MK logo, etc.
        if 'H' in display_options:
            # FIXME: view/layout/module related stylesheets/javascripts e.g. in case of BI?
            html.body_start(view_title(view), stylesheets=["pages","views","status","bi"], javascripts=['bi'])
        if 'T' in display_options:
            html.top_heading(view_title(view))

    has_done_actions = False

    if show_buttons and 'B' in display_options:
        show_context_links(view, hide_filters)

    # Show the command form? Are commands possible?
    command_form = len(rows) > 0 and display_command_form(display_options, datasource)

    need_navi = show_buttons and \
        not html.do_actions() and (
        'D' in display_options or
        'F' in display_options or
        'C' in display_options or
        'O' in display_options or
        'E' in display_options)
    if need_navi:
        html.write("<table class=navi><tr>\n")

        # Painter-Options
        if 'D' in display_options and len(painter_options) > 0 and config.may("painter_options"):
            toggle_button("painter_options", False, _("Display"))
            html.write("<td class=minigap></td>\n")

        # Filter-button
        if 'F' in display_options and len(show_filters) > 0:
            filter_isopen = html.var("filled_in") != "filter" and view["mustsearch"]
            # Show warning-icon if some filter is set
            label = _("Filter")
            if html.var("filled_in") == "filter":
                label = '<img class=tabicon src="images/icon_filter_set.png"> %s' % label

            toggle_button("table_filter", filter_isopen, label, ["filter"])
            html.write("<td class=minigap></td>\n")

        # Command-button, open command form if checkboxes are currently shown
        if command_form:
            toggle_button("table_actions", False, _("Commands"))
            # toggle_button("table_actions", show_checkboxes, _("Commands"))
            html.write("<td class=minigap></td>\n")

        # Buttons for view options
        if 'O' in display_options:
            # Link for selecting/deselecting all rows
            if command_form and layout["checkboxes"]:
                if show_checkboxes:
                    addclass = " selected"
                    title = _("Hide check boxes")
                    uri = html.makeuri([("show_checkboxes", "")])
                else:
                    addclass = ""
                    title = _("Show check boxes for selecting specific items for the commands")
                    uri = html.makeuri([("show_checkboxes", "on")])
                html.write('<td class="left w30%s"><a href="%s" title="%s">%s</a></td>\n' %
                           (addclass, uri, title, _('X')))
                html.write("<td class=minigap></td>\n")

            if config.may("view_option_columns"):
                for col in config.view_option_columns:
                    uri = html.makeuri([("num_columns", col)])
                    if col == num_columns:
                        addclass = " selected"
                    else:
                        addclass = ""
                    html.write('<td class="left w30%s"><a href="%s" title="%s">%s</a></td>\n' %
                                          (addclass, uri, _('%d column layout') % col, col))
                    html.write("<td class=minigap></td>\n")

            if 'R' in display_options and config.may("view_option_refresh"):
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
                    html.write('<td class="left w40%s" id="button-refresh-%s">'
                               '<a href="%s" title="%s">%s</a></td>\n' %
                               (addclass, ref, uri, _('refresh every %d seconds') % ref, reftext))
                    html.write("<td class=minigap></td>\n")

        html.write("<td class=gap>&nbsp;</td>\n")

        # Customize/Edit view button
        if 'E' in display_options and config.may("edit_views"):
            backurl = htmllib.urlencode(html.makeuri([]))
            html.write('<td class="right" onmouseover="hover_tab(this);" onmouseout="unhover_tab(this);">')
            if view["owner"] == config.user_id:
                html.write('<a href="edit_view.py?load_view=%s&back=%s">%s</a>\n' %
                                                     (view["name"], backurl, _('Edit')))
            else:
                html.write('<a href="edit_view.py?clonefrom=%s&load_view=%s&back=%s">%s</a>\n' %
                                                  (view["owner"], view["name"], backurl, _('Edit')))
            html.write('</td>')

        html.write("</tr>")
        html.write("</table><table class=navi><tr>\n")

        # Filter form
        if 'F' in display_options and len(show_filters) > 0:
            show_filter_form(filter_isopen, show_filters)

    # Actions
    if command_form:
        # If we are currently within an action (confirming or executing), then
        # we display only the selected rows (if checkbox mode is active)
        if html.var("selected_rows", "") and html.do_actions():
            rows = get_selected_rows(view, rows, html.var("selected_rows"))

        if html.do_actions() and html.transaction_valid(): # submit button pressed, no reload
            try:
                if 'C' in display_options:
                    html.write("<tr class=form><td class=whiteborder>")
                # Create URI with all actions variables removed
                backurl = html.makeuri([])
                has_done_actions = do_actions(view, datasource["infos"][0], rows, backurl)
                if 'C' in display_options:
                    html.write("</td></tr>")
            except MKUserError, e:
                html.show_error(e.message)
                if 'C' in display_options:
                    html.write("</td></tr>")
                html.add_user_error(e.varname, e.message)
                if 'C' in display_options:
                    show_command_form(True, datasource)

        elif 'C' in display_options: # (*not* display open, if checkboxes are currently shown)
            # show_command_form(show_checkboxes, datasource)
            show_command_form(False, datasource)

    if need_navi:
        if 'O' in display_options and len(painter_options) > 0 and config.may("painter_options"):
            show_painter_options(painter_options)

        # Ende des Bereichs mit den Tabs
        html.write("</table>\n") # class=navi

    # The refreshing content container
    if 'R' in display_options:
        html.write("<div id=data_container>\n")

    if not has_done_actions:
        # Limit exceeded? Show warning
        if 'W' in display_options:
            html.check_limit(rows, get_limit())
        layout["render"](rows, view, group_painters, painters, num_columns,
                         show_checkboxes and not html.do_actions())

        # Play alarm sounds, if critical events have been displayed
        if 'S' in display_options and view.get("play_sounds"):
            play_alarm_sounds()

    # In multi site setups error messages of single sites do not block the
    # output and raise now exception. We simply print error messages here.
    # In case of the web service we show errors only on single site installations.
    if config.show_livestatus_errors \
       and 'W' in display_options \
       and (html.output_format == "html" or not config.is_multisite()):
        for sitename, info in html.live.deadsites.items():
            html.show_error("<b>%s - Livestatus error</b><br>%s" % (info["site"]["alias"], info["exception"]))

    # FIXME: Sauberer wäre noch die Status Icons hier mit aufzunehmen
    if 'R' in display_options:
        html.write("</div>\n")

    if show_footer:
        pid = os.getpid()
        if html.live.successfully_persisted():
            html.add_status_icon("persist", "Reused persistent livestatus connection from earlier request (PID %d)" % pid)
        if bi.reused_compilation():
            html.add_status_icon("aggrcomp", "Reused cached compiled BI aggregations (PID %d)" % pid)

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

    # Refresh rate
    if config.may("view_option_refresh"):
        if html.has_var("refresh"):
            try:
                v["refresh"] = int(html.var("refresh"))
            except:
                v["refresh"] = None
            must_save = True
    elif "refresh" in v:
        del v["refresh"]

    # Number of columns in layout
    if config.may("view_option_columns"):
        if html.has_var("num_columns"):
            try:
                v["num_columns"] = max(1, int(html.var("num_columns")))
            except:
                v["num_columns"] = 1
            must_save = True
    elif "num_columns" in v:
        del v["num_columns"]

    # Show checkboxes for commands
    if config.may("act"):
        if html.has_var("show_checkboxes"):
            v["show_checkboxes"] = html.var("show_checkboxes", "") != ""
            must_save = True
    elif "show_checkboxes" in v:
        del v["show_checkboxes"]

    if config.may("painter_options"):
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

def do_table_join(master_ds, master_rows, master_filters, join_painters, join_columns, only_sites):
    join_table, join_master_column = master_ds["join"]
    slave_ds = multisite_datasources[join_table]
    join_slave_column = slave_ds["joinkey"]

    # Create additional filters
    join_filter = ""
    for entry in join_painters:
        paintfunc, linkview, title, join_key = entry[:4]
        join_filter += "Filter: %s = %s\n" % (join_slave_column, join_key )
    join_filter += "Or: %d\n" % len(join_painters)
    query = master_filters + join_filter
    rows = query_data(slave_ds, [join_master_column, join_slave_column] + join_columns, [], query, only_sites, None)
    per_master_entry = {}
    current_key = None
    current_entry = None
    for row in rows:
        master_key = (row["site"], row[join_master_column])
        if master_key != current_key:
            current_key = master_key
            current_entry = {}
            per_master_entry[current_key] = current_entry
        current_entry[row[join_slave_column]] = row

    # Add this information into master table in artificial column "JOIN"
    for row in master_rows:
        key = (row["site"], row[join_master_column])
        joininfo = per_master_entry.get(key, {})
        row["JOIN"] = joininfo


def play_alarm_sounds():
    if not config.enable_sounds:
        return

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

    title = view["title"] + " " + ", ".join(extra_titles)

    for fn in ubiquitary_filters:
        # Disable 'filename' filter, if WATO is disabled
        if fn == "filename" and not config.wato_enabled:
            continue
        filt = multisite_filters[fn]
        heading = filt.heading_info(tablename)
        if heading:
            title = heading + " - " + title

    return title

# Return title for context link buttons
def view_linktitle(view):
    t = view.get("linktitle")
    if not t:
        return view_title(view)
    else:
        return t


def show_context_links(thisview, active_filters):
    # html.begin_context_buttons() called automatically by html.context_button()
    # That way if no button is painted we avoid the empty container
    execute_hooks('buttons-begin')

    # WATO: If we have a host context, then show button to WATO, if permissions allow this
    if html.has_var("host") \
       and config.wato_enabled \
       and config.may("wato.use") \
       and (config.may("wato.hosts") or config.may("wato.seeall")) \
       and wato.using_wato_hosts():
        host = html.var("host")
        if host:
            url = wato.api.link_to_host(host)
        else:
            url = wato.api.link_to_path(html.var("wato_folder", ""))
        html.context_button(_("WATO"), url, "wato", id="wato",
            bestof = config.context_buttons_to_show)

    links = collect_context_links(thisview, active_filters)
    for view, linktitle, uri, icon, buttonid in links:
        if not view.get("mobile"):
            html.context_button(linktitle, url=uri, icon=icon, id=buttonid, bestof=config.context_buttons_to_show)

    execute_hooks('buttons-end')
    html.end_context_buttons()

# Collect all views that share a context with thisview. For example
# if a view has an active filter variable specifying a host, then
# all host-related views are relevant.
def collect_context_links(thisview, active_filters):
    # compute list of html variables used actively by hidden or shown
    # filters.
    active_filter_vars = set([])
    for filt in active_filters:
        for var in filt.htmlvars:
            if html.has_var(var):
                active_filter_vars.add(var)

    context_links = []
    # sort view buttons somehow
    sorted_views = html.available_views.values()
    sorted_views.sort(cmp = lambda b,a: cmp(a.get('icon'), b.get('icon')))

    for view in sorted_views:
        name = view["name"]
        linktitle = view.get("linktitle")
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
        if len(used_contextvars):
            vars_values = [ (var, html.var(var)) for var in set(used_contextvars) ]
            uri = html.makeuri_contextless(vars_values + [("view_name", name)])
            icon = view.get("icon")
            buttonid = "cb_" + name
            context_links.append((view, linktitle, uri, icon, buttonid))
    return context_links


def ajax_count_button():
    id = html.var("id")
    counts = config.load_user_file("buttoncounts", {})
    for i in counts:
        counts[i] *= 0.95
    counts.setdefault(id, 0)
    counts[id] += 1
    config.save_user_file("buttoncounts", counts)


# Retrieve data via livestatus, convert into list of dicts,
# prepare row-function needed for painters
# datasource: the datasource object as defined in plugins/views/datasources.py
# columns: the list of livestatus columns to query
# add_columns: list of columns the datasource is known to add itself
#  (couldn't we get rid of this parameter by looking that up ourselves?)
# add_headers: additional livestatus headers to add
# only_sites: list of sites the query is limited to
# limit: maximum number of data rows to query
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
        if "host" in datasource["infos"]:
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
    if config.debug_livestatus_queries \
            and html.output_format == "html" and 'W' in html.display_options:
        html.write('<div class="livestatus message" onmouseover="this.style.display=\'none\';">'
                   '<tt>%s</tt></div>\n' % (query.replace('\n', '<br>\n')))

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

    # Handle case where join columns are not present for all rows
    def save_compare(compfunc, row1, row2):
        if row1 == None and row2 == None:
            return 0
        elif row1 == None:
            return -1
        elif row2 == None:
            return 1
        else:
            return compfunc(row1, row2)

    sort_cmps = []
    for s in sorters:
        cmpfunc = s[0]["cmp"]
        negate = s[1] and -1 or 1
        if len(s) > 2:
            joinkey = s[2] # e.g. service description
        else:
            joinkey = None
        sort_cmps.append((cmpfunc, negate, joinkey))

    def multisort(e1, e2):
        for func, neg, joinkey in sort_cmps:
            if joinkey: # Sorter for join column, use JOIN info
                c = neg * save_compare(func, e1["JOIN"].get(joinkey), e2["JOIN"].get(joinkey))
            else:
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

def allowed_for_joined_datasource(collection, datasourcename):
    if 'join' not in multisite_datasources[datasourcename]:
        return {}
    return allowed_for_datasource(collection, multisite_datasources[datasourcename]['join'][0])

def is_joined_value(collection, varname):
    selected_label = [ label for name, label in collection if name == html.var(varname, '') ]
    return selected_label and selected_label[0][:8] == 'SERVICE:'

def collist_of_collection(collection, join_target = []):
    def sort_list(l):
        # Sort the lists but don't mix them up
        swapped = [ (disp, key) for key, disp in l ]
        swapped.sort()
        return [ (key, disp) for disp, key in swapped ]

    if not join_target:
        return sort_list([ (name, p["title"]) for name, p in collection.items() ])
    else:
        return sort_list([ (name, 'SERVICE: ' + p["title"]) for name, p in collection.items() if (name, p["title"]) not in join_target ])

#   .----------------------------------------------------------------------.
#   |         ____                                          _              |
#   |        / ___|___  _ __ ___  _ __ ___   __ _ _ __   __| |___          |
#   |       | |   / _ \| '_ ` _ \| '_ ` _ \ / _` | '_ \ / _` / __|         |
#   |       | |__| (_) | | | | | | | | | | | (_| | | | | (_| \__ \         |
#   |        \____\___/|_| |_| |_|_| |_| |_|\__,_|_| |_|\__,_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Functions dealing with external commands send to the monitoring      |
#   | core. The commands themselves are defined as a plugin. Shipped       |
#   | command definitions are in plugins/views/commands.py.                |
#   | We apologize for the fact that we one time speak of "commands" and   |
#   | the other time of "action". Both is the same here...                 |
#   '----------------------------------------------------------------------'

# Checks wether or not this view handles commands for the current user
# When it does not handle commands the command tab, command form, row
# selection and processing commands is disabled.
def display_command_form(display_options, datasource):
    if not 'C' in display_options:
        return False
    if not config.may("act"):
        return False
    if html.has_var("try"):
        return False

    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource["infos"][0]
    for command in multisite_commands:
        if what in command["tables"] and config.may(command["permission"]):
            return True

def show_command_form(is_open, datasource):
    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource["infos"][0]

    html.write("<tr class=form id=table_actions %s><td>" %
                (not is_open and 'style="display: none"' or '') )
    html.begin_form("actions", onsubmit = 'add_row_selections(this);')
    html.hidden_field("_do_actions", "yes")
    html.hidden_field("actions", "yes")
    html.hidden_fields() # set all current variables, exception action vars
    html.write("<div class=whiteborder>\n")
    html.write('<table class="form">\n')

    # Commands are defined in plugins/views/commands.py. Iterate
    # over all command definitions and render HTML input fields.
    for command in multisite_commands:
        if what in command["tables"] and config.may(command["permission"]):
            html.write('<tr><td class=legend>%s</td>\n' % command["title"])
            html.write('<td class=content>\n')
            command["render"]()
            html.write('</td></tr>\n')

    html.write("</table></div>\n")
    html.end_form()
    html.write("</td></tr>\n")

# Examine the current HTML variables in order determine, which
# command the user has selected. The fetch ids from a data row
# (host name, service description, downtime/commands id) and
# construct one or several core command lines and a descriptive
# title.
def core_command(what, row):
    host = row.get("host_name")
    descr = row.get("service_description")

    if what == "host":
        spec = host
        cmdtag = "HOST"
        prefix = "host_"
    elif what == "service":
        spec = "%s;%s" % (host, descr)
        cmdtag = "SVC"
        prefix = "service_"
    elif what in [ "comment", "downtime" ]:
        spec = row.get(what + "_id")
        if descr:
            cmdtag = "SVC"
        else:
            cmdtag = "HOST"
    else:
        raise MKInternalError(_("Sorry, no actions possible on table %s") % tablename)

    commands = None
    for cmd in multisite_commands:
        if config.may(cmd["permission"]):
            result = cmd["action"](cmdtag, spec, row)
            if result:
                commands, title = result
                break

    if not commands:
        raise MKUserError(None, _("Sorry. This command is not implemented."))

    # Some commands return lists of complete command lines, others
    # just return one basic command without timestamp. Convert those
    if type(commands) != list:
        commands = ["[%d] %s\n" % (int(time.time()), commands)]

    return commands, title


# Returns:
# True -> Actions have been done
# False -> No actions done because now rows selected
# [...] new rows -> Rows actions (shall/have) be performed on
def do_actions(view, what, action_rows, backurl):
    if not config.may("act"):
        html.show_error(_("You are not allowed to perform actions. "
                          "If you think this is an error, please ask "
                          "your administrator grant you the permission to do so."))
        return False # no actions done

    if not action_rows:
        html.show_error(_("No rows selected to perform actions for."))
        return False # no actions done

    command = None
    title = core_command(what, action_rows[0])[1] # just get the title
    if not html.confirm(_("Do you really want to %s the following %d %ss?") %
                                               (title, len(action_rows), what)):
        return False

    count = 0
    for row in action_rows:
        nagios_commands, title = core_command(what, row)
        for command in nagios_commands:
            if type(command) == unicode:
                command = command.encode("utf-8")
            html.live.command(command, row["site"])
            count += 1

    if command:
        message = _("Successfully sent %d commands to Nagios.") % count
        if config.debug:
            message += _("The last one was: <pre>%s</pre>") % command
        if html.output_format == "html": # sorry for this hack
            message += '<br><a href="%s">%s</a>' % (backurl, _('Back to view'))
        html.message(message)
    elif count == 0:
        html.message(_("No matching data row. No command sent."))
    return True

def get_selected_rows(view, rows, sel_var):
    action_rows = []
    selected_rows = sel_var.split(',')
    for row in rows:
        if row_id(view, row) in selected_rows:
            action_rows.append(row)
    return action_rows


def get_context_link(user, viewname):
    if viewname in html.available_views:
        return "view.py?view_name=%s" % viewname
    else:
        return None

def ajax_export():
    load_views()
    for name, view in html.available_views.items():
        view["owner"] = ''
        view["public"] = True
    html.write(pprint.pformat(html.available_views))


def page_message_and_forward(message, default_url, addhtml=""):
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

def register_hook(hook, func):
    if not hook in view_hooks:
        view_hooks[hook] = []

    if func not in view_hooks[hook]:
        view_hooks[hook].append(func)

def execute_hooks(hook):
    for hook_func in view_hooks.get(hook, []):
        try:
            hook_func()
        except:
            if config.debug:
                raise MKGeneralException(_('Problem while executing hook function %s in hook %s: %s')
                                           % (hook_func.__name__, hook, traceback.format_exc()))
            else:
                pass

def prepare_paint(p, row):
    painter = p[0]
    linkview = p[1]
    tooltip = len(p) > 2 and p[2] or None
    if len(p) >= 4:
        join_key = p[3]
        row = row.get("JOIN", {}).get(p[3])
        if not row:
            return "", ""  # no join information available for that column

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

        filename = html.mobile and "mobile_view.py" or "view.py"
        uri = filename + "?" + htmllib.urlencode_vars([("view_name", linkview)] + vars)
        content = "<a href=\"%s\">%s</a>" % (uri, content)
#        rel = 'view.py?view_name=hoststatus&site=local&host=erdb-lit&display_options=htbfcoezrsix'
#        content = '<a class=tips rel="%s" href="%s">%s</a>' % (rel, uri, content)
    return content

def docu_link(topic, text):
    return '<a href="%s" target="_blank">%s</a>' % (config.doculink_urlformat % topic, text)

def row_id(view, row):
    '''
    Calculates a uniq id for each data row which identifies the current
    row accross different page loadings.
    '''
    key = ''
    for col in multisite_datasources[view['datasource']]['idkeys']:
        key += '~%s' % row[col]
    return str(hash(key))

def paint(p, row, tdattrs=""):
    tdclass, content = prepare_paint(p, row)
    if tdclass:
        html.write("<td %s class=\"%s\">%s</td>\n" % (tdattrs, tdclass, content))
    else:
        html.write("<td %s>%s</td>" % (tdattrs, content))
    return content != ""

def substract_sorters(base, remove):
    for s in remove:
        if s in base:
            base.remove(s)
        elif (s[0], not s[1]) in base:
            base.remove((s[0], not s[1]))

def parse_url_sorters(sort):
    sorters = []
    if not sort:
        return sorters
    for s in sort.split(','):
        if not '~' in s:
            sorters.append((s.replace('-', ''), s.startswith('-')))
        else:
            sorter, join_index = s.split('~', 1)
            sorters.append((sorter.replace('-', ''), sorter.startswith('-'), join_index))
    return sorters

def get_sorter_name_of_painter(painter):
    if 'sorter' in painter:
        return painter['sorter']
    elif painter['name'] in multisite_sorters:
        return painter['name']

def get_primary_sorter_order(view, painter):
    sorter_name = get_sorter_name_of_painter(painter)
    this_asc_sorter  = (sorter_name, False)
    this_desc_sorter = (sorter_name, True)
    group_sort, user_sort, view_sort = get_separated_sorters(view)
    if user_sort and this_asc_sorter == user_sort[0]:
        return 'asc'
    elif user_sort and this_desc_sorter == user_sort[0]:
        return 'desc'
    else:
        return ''

def get_separated_sorters(view):
    group_sort = [ (get_sorter_name_of_painter(multisite_painters[p[0]]), False)
                   for p in view['group_painters']
                   if p[0] in multisite_painters
                      and get_sorter_name_of_painter(multisite_painters[p[0]]) is not None ]
    view_sort  = [ s for s in view['sorters'] if not s[0] in group_sort ]

    # Get current url individual sorters. Parse the "sort" url parameter,
    # then remove the group sorters. The left sorters must be the user
    # individual sorters for this view.
    # Then remove the user sorters from the view sorters
    user_sort = parse_url_sorters(html.var('sort'))

    substract_sorters(user_sort, group_sort)
    substract_sorters(view_sort, user_sort)

    return group_sort, user_sort, view_sort

def sort_url(view, painter, join_index):
    """
    The following sorters need to be handled in this order:

    1. group by sorter (needed in grouped views)
    2. user defined sorters (url sorter)
    3. configured view sorters
    """
    sort = html.var('sort', None)
    sorter = []

    group_sort, user_sort, view_sort = get_separated_sorters(view)

    sorter = group_sort + user_sort + view_sort

    # Now apply the sorter of the current column:
    # - Negate/Disable when at first position
    # - Move to the first position when already in sorters
    # - Add in the front of the user sorters when not set
    sorter_name = get_sorter_name_of_painter(painter)
    if join_index:
        this_asc_sorter  = (sorter_name, False, join_index)
        this_desc_sorter = (sorter_name, True, join_index)
    else:
        this_asc_sorter  = (sorter_name, False)
        this_desc_sorter = (sorter_name, True)

    if user_sort and this_asc_sorter == user_sort[0]:
        # Second click: Change from asc to desc order
        sorter[sorter.index(this_asc_sorter)] = this_desc_sorter
    elif user_sort and this_desc_sorter == user_sort[0]:
        # Third click: Remove this sorter
        sorter.remove(this_desc_sorter)
    else:
        # First click: add this sorter as primary user sorter
        # Maybe the sorter is already in the user sorters or view sorters, remove it
        for s in [ user_sort, view_sort ]:
            if this_asc_sorter in s:
                s.remove(this_asc_sorter)
            if this_desc_sorter in s:
                s.remove(this_desc_sorter)
        # Now add the sorter as primary user sorter
        sorter = group_sort + [this_asc_sorter] + user_sort + view_sort

    p = []
    for s in sorter:
        if len(s) == 2:
            p.append((s[1] and '-' or '') + s[0])
        else:
            p.append((s[1] and '-' or '') + s[0] + '~' + s[2])

    return ','.join(p)

def paint_header(view, p):
    # The variable p is a tuple with the following components:
    # p[0] --> painter object, from multisite_painters[]
    # p[1] --> view name to link to or None (not needed here)
    # p[2] --> tooltip (title) to display (not needed here)
    # p[3] --> optional: join key (e.g. service description)
    # p[4] --> optional: column title to use instead default
    painter = p[0]
    join_index = None
    t = painter.get("short", painter["title"])
    if len(p) >= 4: # join column
        join_index = p[3]
    if len(p) >= 5 and p[4]:
        t = p[4]

    # Optional: Sort link in title cell
    # Use explicit defined sorter or implicit the sorter with the painter name
    # Important for links:
    # - Add the display options (Keeping the same display options as current)
    # - Link to _self (Always link to the current frame)
    # - Keep the _body_class variable (e.g. for dashlets)
    thclass = ''
    onclick = ''
    title = ''
    if 'L' in html.display_options \
       and view.get('user_sortable', True) \
       and get_sorter_name_of_painter(painter) is not None:
        params = [
            ('sort', sort_url(view, painter, join_index)),
        ]
        if html.has_var('_body_class'):
            params.append(('_body_class',     html.var('_body_class')))
        if hasattr(html, 'title_display_options'):
            params.append(('display_options', html.title_display_options))

        thclass = ' class="sort %s"' % get_primary_sorter_order(view, painter)
        onclick = ' onclick="location.href=\'%s\'"' % html.makeuri(params, 'sort')
        title   = ' title="%s"' % (_('Sort by %s') % t)

    html.write("<th%s%s%s>%s</th>" % (thclass, onclick, title, t))

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

def get_host_tags(row):
    for name, val in zip(row["host_custom_variable_names"],
                         row["host_custom_variable_values"]):
        if name == "TAGS":
            return  val
    return ""

def cmp_insensitive_string(v1, v2):
    c = cmp(v1.lower(), v2.lower())
    # force a strict order in case of equal spelling but different
    # case!
    if c == 0:
        return cmp(v1, v2)
    else:
        return c

# Sorting
def cmp_simple_string(column, r1, r2):
    v1, v2 = r1.get(column, ''), r2.get(column, '')
    return cmp_insensitive_string(v1, v2)

def cmp_string_list(column, r1, r2):
    v1 = ''.join(r1.get(column, []))
    v2 = ''.join(r2.get(column, []))
    return cmp_insensitive_string(v1, v2)

def cmp_simple_number(column, r1, r2):
    return cmp(r1.get(column), r2.get(column))

def declare_simple_sorter(name, title, column, func):
    multisite_sorters[name] = {
        "title"   : title,
        "columns" : [ column ],
        "cmp"     : lambda r1, r2: func(column, r1, r2)
    }

def declare_1to1_sorter(painter_name, func, col_num = 0, reverse = False):
    multisite_sorters[painter_name] = {
        "title"   : multisite_painters[painter_name]['title'],
        "columns" : multisite_painters[painter_name]['columns'],
        "cmp"     : lambda r1, r2: func(multisite_painters[painter_name]['columns'][col_num],
                                        reverse and r1 or r2,
                                        reverse and r2 or r1)
    }
    return painter_name


load_plugins()

