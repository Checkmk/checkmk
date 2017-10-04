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

# Functions for parsing Werks and showing the users a browsable change
# log

import config, os, table
import re
from lib import *
from valuespec import *
import cmk.store as store
import cmk.paths
import cmk.werks

acknowledgement_path = cmk.paths.var_dir + "/acknowledged_werks.mk"

# Keep global variable for caching werks between requests. The never change.
g_werks = None

werks_stylesheets = [ "pages", "check_mk", "status", "wato", "views" ]

def page_version():
    html.header(_("Check_MK %s Release Notes") % cmk.__version__, stylesheets = werks_stylesheets)
    load_werks()
    handle_acknowledgement()
    render_werks_table()
    html.footer()


def handle_acknowledgement():
    if html.var("_werk_ack") and html.check_transaction():
        werk_id = html.get_integer_input("_werk_ack")
        if werk_id not in g_werks:
            raise MKUserError("werk", _("This werk does not exist."))
        werk = g_werks[werk_id]

        if werk["compatible"] == "incomp_unack":
            acknowledge_werk(werk)
            html.message(_("Werk %s - %s has been acknowledged.") % (render_werk_id(werk, with_link=True), render_werk_title(werk)))
            html.reload_sidebar()
            load_werks() # reload ack states after modification

    elif html.var("_ack_all"):
        if (html.confirm(_("Do you really want to acknowledge <b>all</b> incompatible werks?"), method="GET")):
            num = len(unacknowledged_incompatible_werks())
            acknowledge_all_werks()
            html.message(_("%d incompatible Werks have been acknowledged.") % num)
            html.reload_sidebar()
            load_werks() # reload ack states after modification

    render_unacknowleged_werks()


def page_werk():
    load_werks()
    werk_id = html.get_integer_input("werk")
    if werk_id not in g_werks:
        raise MKUserError("werk", _("This werk does not exist."))
    werk = g_werks[werk_id]

    html.header(("%s %s - %s") % (_("Werk"), render_werk_id(werk, with_link=False), werk["title"]), stylesheets = werks_stylesheets)
    html.begin_context_buttons()
    back_url = html.makeuri([], filename="version.py", delvars=["werk"]) # keeps filter settings
    html.context_button(_("Back"), back_url, "back")
    if werk["compatible"] == "incomp_unack" and may_acknowledge():
        ack_url = html.makeactionuri([("_werk_ack", werk["id"])], filename="version.py")
        html.context_button(_("Acknowledge"), ack_url, "werk_ack")
    html.end_context_buttons()

    html.open_table(class_=["data", "headerleft", "werks"])

    def werk_table_row(caption, content, css=None):
        html.open_tr()
        html.th(caption)
        html.open_td(class_=css)
        html.write(content)
        html.close_td()
        html.close_tr()

    werk_table_row(_("ID"), render_werk_id(werk, with_link=False))
    werk_table_row(_("Title"), html.render_b(render_werk_title(werk)))
    werk_table_row(_("Component"), render_werk_component(werk))
    werk_table_row(_("Date"), render_werk_date(werk))
    werk_table_row(_("Check_MK Version"), werk["version"])
    werk_table_row(_("Level"), render_werk_level(werk), css="werklevel werklevel%d" % werk["level"])
    werk_table_row(_("Class"), render_werk_class(werk), css="werkclass werkclass%s" % werk["class"])
    werk_table_row(_("Compatibility"), render_werk_compatibility(werk), css="werkcomp werkcomp%s" % werk["compatible"])
    werk_table_row(_("Description"), render_werk_description(werk), css="nowiki")

    html.close_table()

    html.footer()



def load_werks():
    global g_werks
    if g_werks == None:
        g_werks = cmk.werks.load()

    ack_ids = load_acknowledgements()
    for werk in g_werks.values():
        if werk["compatible"] in [ "incomp", "incomp_unack" ]:
            if werk["id"] in ack_ids or werk_is_pre_127(werk):
                werk["compatible"] = "incomp_ack"
            else:
                werk["compatible"] = "incomp_unack"


def may_acknowledge():
    return config.user.may("general.acknowledge_werks")


def acknowledge_werk(werk):
    acknowledge_werks([werk])


def acknowledge_werks(werks, check_permission=True):
    if check_permission:
        config.user.need_permission("general.acknowledge_werks")

    ack_ids = load_acknowledgements()
    for werk in werks:
        ack_ids.append(werk["id"])
        werk["compatible"] = "incomp_ack"
    save_acknowledgements(ack_ids)


def save_acknowledgements(acknowledged_werks):
    store.save_data_to_file(acknowledgement_path, acknowledged_werks)


def acknowledge_all_werks(check_permission=True):
    load_werks()
    acknowledge_werks(unacknowledged_incompatible_werks(), check_permission)


def werk_is_pre_127(werk):
    return werk["version"].startswith("1.2.5") \
        or werk["version"].startswith("1.2.6")


def load_acknowledgements():
    return store.load_data_from_file(acknowledgement_path, [])


def unacknowledged_incompatible_werks():
    return werks_sorted_by_date([
        werk
        for werk in g_werks.values()
        if werk["compatible"] == "incomp_unack"])


def num_unacknowledged_incompatible_werks():
    load_werks()
    return len(unacknowledged_incompatible_werks())


def werk_table_option_entries():
    return [
        ( "classes",
          "double",
          ListChoice(
              title = _("Classes"),
              choices = sorted(cmk.werks.werk_classes().items()),
          ),
          [ "feature", "fix", "security" ],
        ),
        ( "levels",
          "double",
          ListChoice(
              title = _("Levels"),
              choices = sorted(cmk.werks.werk_levels().items()),
          ),
          [ 1, 2, 3 ],
        ),
         ( "date",
           "double",
           Timerange(
               title = _("Date"),
            ),
            ( 'date', ( 1383149313, int(time.time()) ) ),
         ),
        ( "id",
          "single",
          TextAscii(
              title = _("Werk ID"),
              label = "#",
              regex = "[0-9]{4}",
              allow_empty = True,
              size = 4,
          ),
          "",
        ),
        ( "compatibility",
          "single",
          DropdownChoice(
              title = _("Compatibility"),
              choices = [
                ( [ "compat", "incomp_ack", "incomp_unack" ], _("Compatible and incompatible Werks") ),
                ( [ "compat" ],                                _("Compatible Werks") ),
                ( [ "incomp_ack", "incomp_unack" ],           _("Incompatible Werks") ),
                ( [ "incomp_unack" ],                         _("Unacknowledged incompatible Werks") ),
                ( [ "incomp_ack" ],                            _("Acknowledged incompatible Werks") ),
              ]
          ),
          [ "compat", "incomp_ack", "incomp_unack" ],
        ),
        ( "component",
          "single",
          DropdownChoice(
              title = _("Component"),
              choices = [
                ( None, _("All components") ),
              ] + sorted(cmk.werks.werk_components().items()),
          ),
          None,
         ),
         ( "edition",
           "single",
           DropdownChoice(
               title = _("Edition"),
               choices = [
                   ( None, _("All editions") ),
                   ( "cme", _("Werks only concerning the Managed Services Edition") ),
                   ( "cee", _("Werks only concerning the Enterprise Edition") ),
                   ( "cre", _("Werks also concerning the Raw Edition") ),
                ],
            ),
            None,
         ),
         ( "content",
           "single",
           TextUnicode(
               title = _("Werk title or content"),
               size = 41,
           ),
           ""
         ),
         ( "version",
           "single",
           Tuple(
               title = _("Check_MK Version"),
               orientation = "float",
               elements = [
                   TextAscii(label = _("from:"), size=12),
                   TextAscii(label = _("to:"), size=12),
               ]
           ),
           ( "", "" ),
         ),
         ( "grouping",
           "single",
           DropdownChoice(
               title = _("Group Werks by"),
               choices = [
                 ( "version", _("Check_MK Version") ),
                 ( "day",     _("Day of creation") ),
                 ( "week",    _("Week of creation") ),
                 ( None,      _("Do not group") ),
               ],
           ),
           "version",
         ),
    ]


def render_unacknowleged_werks():
    werks = unacknowledged_incompatible_werks()
    if werks and may_acknowledge():
        html.begin_context_buttons()
        html.context_button(_("Acknowledge all"), html.makeactionuri([("_ack_all", "1")]), "werk_ack")
        html.end_context_buttons()

    if werks and not html.has_var("show_unack"):
        html.open_div(class_=["warning"])
        html.write_text(_("<b>Warning:</b> There are %d unacknowledged incompatible werks:") % len(werks))
        html.br()
        html.br()
        html.a(_("Show unacknowledged incompatible werks"),
               href=html.makeuri_contextless([("show_unack", "1"), ("wo_compatibility", "3")]))
        html.close_div()


def render_werks_table():

    werk_table_options = render_werk_table_options()

    if html.var("show_unack") and not html.var("wo_set"):
        werk_table_options = default_werk_table_options()
        werk_table_options["compatibility"] = [ "incomp_unack" ]

    current_group = False

    def begin_group(title):
        table.begin(title=title, limit=None, searchable = False, sortable = False, css="werks")

    werklist = []

    if werk_table_options["grouping"] == "version":
        werklist = cmk.werks.sort_by_version_and_component(g_werks.values())
    else:
        werklist = werks_sorted_by_date(g_werks.values())

    for werk in werklist:
        if werk_matches_options(werk, werk_table_options):
            group = werk_group_value(werk, werk_table_options["grouping"])
            if group != current_group:
                if current_group != False:
                    table.end()
                begin_group(group)
                current_group = group

            table.row()
            table.cell(_("ID"), render_werk_id(werk, with_link=True), css="number narrow")
            table.cell(_("Version"), werk["version"], css="number narrow")
            table.cell(_("Date"), render_werk_date(werk), css="number narrow")
            table.cell(_("Class"), render_werk_class(werk), css="werkclass werkclass%s" % werk["class"])
            table.cell(_("Level"), render_werk_level(werk), css="werklevel werklevel%d" % werk["level"])
            table.cell(_("Compatibility"), render_werk_compatibility(werk), css="werkcomp werkcomp%s" % werk["compatible"])
            table.cell(_("Component"), render_werk_component(werk), css="nowrap")
            table.cell(_("Title"), render_werk_title(werk))

    if current_group != False:
        table.end()
    else:
        html.h3(_("No matching Werks found."))

def werk_group_value(werk, grouping):
    if grouping == None:
        return None
    elif grouping == "version":
        return werk["version"]
    else:
        broken_time = time.localtime(werk["date"])
        if grouping == "day":
            return time.strftime("%Y-%m-%d", broken_time)
        else:
            return time.strftime("%s %%U - %%Y" % _("Week"), broken_time)

def werk_matches_options(werk, werk_table_options):
    if not ((not werk_table_options["id"] or werk["id"] == tryint(werk_table_options["id"])) and \
           werk["level"] in werk_table_options["levels"] and \
           werk["class"] in werk_table_options["classes"] and \
           werk["compatible"] in werk_table_options["compatibility"] and \
           werk_table_options["component"] in ( None, werk["component" ]) and \
           werk["date"] >= werk_table_options["date_range"][0] and \
           werk["date"] <= werk_table_options["date_range"][1]):
        return False


    if werk_table_options["edition"] and werk["edition"] != werk_table_options["edition"]:
        return False

    from_version, to_version = werk_table_options["version"]
    if from_version and cmp_version(werk["version"], from_version) < 0:
        return False

    if to_version and cmp_version(werk["version"], to_version) > 0:
        return False

    if werk_table_options["content"]:
        have_match = False
        search_text = werk_table_options["content"].lower()
        for line in [werk["title"]] + werk["body"]:
            if search_text in line.lower():
                have_match = True
                break
        if not have_match:
            return False

    return True


def default_werk_table_options():
    werk_table_options = {}
    for name, height, vs, default_value in werk_table_option_entries():
        werk_table_options[name] = default_value
    werk_table_options["date_range"] = (1, time.time())
    return werk_table_options


def render_werk_table_options():
    werk_table_options = {}

    html.begin_foldable_container("werks", "options", isopen=True, title=_("Searching and Filtering"), indent=False)
    html.begin_form("werks")
    html.hidden_field("wo_set", "set")
    begin_floating_options("werks", is_open=True)
    for name, height, vs, default_value in werk_table_option_entries():
        if html.var("wo_set"):
            value = vs.from_html_vars("wo_" + name)
        else:
            value = default_value
        werk_table_options.setdefault(name, value)
        render_floating_option(name, height, "wo_", vs, werk_table_options[name])
    end_floating_options(reset_url = html.makeuri([], remove_prefix = ""))
    html.hidden_fields()
    html.end_form()
    html.end_foldable_container()

    from_date, until_date = Timerange().compute_range(werk_table_options["date"])[0]
    werk_table_options["date_range"] = from_date, until_date

    return werk_table_options


def render_werk_id(werk, with_link):
    if with_link:
        url = html.makeuri([("werk", werk["id"])], filename="werk.py")
        return '<a href="%s">%s</a>' % (url, render_werk_id(werk, with_link=False))
    else:
        return "#%04d" % werk["id"]

def render_werk_date(werk):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(werk["date"]))

def render_werk_level(werk):
    return cmk.werks.werk_levels()[werk["level"]]

def render_werk_class(werk):
    return cmk.werks.werk_classes()[werk["class"]]

def render_werk_compatibility(werk):
    return cmk.werks.werk_compatibilities()[werk["compatible"]]

def render_werk_component(werk):
    return cmk.werks.werk_components().get(werk["component"], werk["component"])


def render_werk_title(werk):
    title = werk["title"]
    # if the title begins with the name or names of check plugins, then
    # we link to the man pages of those checks
    if ":" in title:
        parts = title.split(":", 1)
        title = insert_manpage_links(parts[0]) + ":" + parts[1]
    return title

def render_werk_description(werk):
    html_code = "<p>"
    in_list = False
    in_code = False
    for line in werk["body"]:
        if line.startswith("LI:"):
            if not in_list:
                html_code += "<ul>"
                in_list = True
            html_code += "<li>%s</li>\n" % line[3:]
        else:
            if in_list:
                html_code += "</ul>"
                in_list = False

            if line.startswith("H2:"):
                html_code += "<h3>%s</h3>\n" % line[3:]
            elif line.startswith("C+:"):
                html_code += "<pre class=code>"
                in_code = True
            elif line.startswith("F+:"):
                file_name = line[3:]
                if file_name:
                    html_code += "<div class=filename>%s</div>" % file_name
                html_code += "<pre class=file>"
                in_code = True
            elif line.startswith("C-:") or line.startswith("F-:"):
                html_code += "</pre>"
                in_code = False
            elif line.startswith("OM:"):
                html_code += "OMD[mysite]:~$ <b>" + line[3:] + "</b>\n"
            elif line.startswith("RP:"):
                html_code += "root@myhost:~# <b>" + line[3:] + "</b>\n"
            elif not line.strip() and not in_code:
                html_code += "</p><p>"
            else:
                html_code += line + "\n"

    if in_list:
        html_code += "</ul>"

    html_code += "</p>"
    return html_code

def insert_manpage_links(text):
    parts = text.replace(",", " ").split()
    new_parts = []
    check_regex = re.compile("[-_\.a-z0-9]")
    for part in parts:
        if check_regex.match(part) and os.path.exists(cmk.paths.check_manpages_dir + "/" + part):
            part = '<a href="wato.py?mode=check_manpage&check_type=%s">%s</a>' % (part, part)
        new_parts.append(part)
    return " ".join(new_parts)


def werks_sorted_by_date(werks):
    return sorted(werks, cmp = lambda a, b: -cmp(a["date"], b["date"]))
