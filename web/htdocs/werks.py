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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# Functions for parsing Werks and showing the users a browsable change
# log

import defaults, os, table
from lib import *
from valuespec import *


werk_classes = {
    "feature"  : _("New Feature"),
    "fix"      : _("Bug Fix"),
    "security" : _("Security Fix"),
}

werk_levels = {
    1 : _("Trivial Change"),
    2 : _("Prominent Change"),
    3 : _("Major Feature"),
}

werk_compatibilities = {
    "compat" : _("Compatible"),
    "incomp" : _("Incompatible"),
}

werk_components = {
    # CRE
    "core" :          _("Core & Setup"),
    "checks" :        _("Checks & Agents"),
    "multisite" :     _("User Interface"),
    "wato" :          _("WATO"),
    "notifications" : _("Notifications"),
    "bi" :            _("BI"),
    "reporting" :     _("Reporting & Availability"),
    "ec" :            _("Event Console"),
    "livestatus" :    _("Livestatus"),
    "liveproxy" :     _("Livestatus-Proxy"),
    "inv" :           _("HW/SW-Inventory"),

    # CEE
    "cmc" :           _("The Check_MK Micro Core"),
    "setup" :         _("Setup, Site Management"),
    "config" :        _("Configuration generation"),
    "livestatus" :    _("Livestatus"),
    "inline-snmp" :   _("Inline-SNMP"),
    "agents" :        _("Agent Bakery"),
    "reporting" :     _("Reporting"),
    "metrics" :       _("Metrics System"),
    "notifications" : _("Notifications"),
}


# Keep global variable for caching werks between requests. The never change.
g_werks = None


def page_version():
    load_werks()
    html.header(_("Check_MK %s Release Notes") % defaults.check_mk_version, stylesheets=["pages", "check_mk", "status", "wato", "views" ])
    render_werks_table()
    html.footer()


def load_werks():
    global g_werks
    if g_werks == None:
        g_werks = {}
        werks_dir = defaults.share_dir + "/werks/"
        for file_name in os.listdir(werks_dir):
            if file_name[0].isdigit():
                werk_id = int(file_name)
                werk = load_werk(werks_dir + file_name)
                werk["id"] = werk_id
                g_werks[werk_id] = werk


def load_werk(path):
    werk = {
        "body" : [],
    }
    in_header = True
    for line in file(path):
        line = line.strip().decode("utf-8")
        if in_header and not line:
            in_header = False
        elif in_header:
            key, text = line.split(":", 1)
            werk[key.lower()] = tryint(text.strip())
        else:
            werk["body"].append(line)
    if "compatible" not in werk: # missing in some legacy werks
        werk["compatible"] = "compat"
    return werk


werk_table_option_entries = [
    ( "classes",
      "double",
      ListChoice(
          title = _("Classes"),
          choices = sorted(werk_classes.items()),
      ),
      [ "feature", "fix", "security" ],
    ),
    ( "levels",
      "double",
      ListChoice(
          title = _("Levels"),
          choices = sorted(werk_levels.items()),
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
            ( [ "compat", "incomp" ], _("Show compatible and incompatible Werks") ),
            ( [ "compat" ],           _("Show only compatible Werks") ),
            ( [ "incomp" ],           _("Show only incompatible Werks") ),
          ]
      ),
      [ "compat", "incomp" ],
    ),
    ( "component",
      "single",
      DropdownChoice(
          title = _("Component"),
          choices = [
            ( None, _("All components") ),
          ] + sorted(werk_components.items()),
      ),
      None,
     ),
     ( "edition",
       "single",
       DropdownChoice(
           title = _("Edition"),
           choices = [
               ( None, _("All editions") ),
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
           size = 44,
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
#"
#"     Gruppierung:
#"     - Version
#"     - Tag
#"     - Woche??
#"     - Nix
#"

]


def render_werks_table():

    werk_table_options = render_werk_table_options()

    table.begin(title=_("Change log of Check_MK version %s") % defaults.check_mk_version,
                searchable = False,
                sortable = False,
                css="werks")
    for werk in werks_sorted_by_date():
        if werk_matches_options(werk, werk_table_options):
            table.row()
            table.cell(_("ID"), render_werk_id(werk), css="number")
            table.cell(_("Version"), werk["version"], css="number")
            table.cell(_("Date"), render_werk_date(werk), css="number")
            table.cell(_("Class"), render_werk_class(werk), css="werkclass werkclass%s" % werk["class"])
            table.cell(_("Level"), render_werk_level(werk), css="werklevel werklevel%d" % werk["level"])
            table.cell(_("Compatibility"), render_werk_compatibility(werk), css="werkcomp werkcomp%s" % werk["compatible"])
            table.cell(_("Component"), render_werk_component(werk), css="nowrap")
            table.cell(_("Title"), render_werk_title(werk))
    table.end()

def werk_matches_options(werk, werk_table_options):
    # html.debug((werk["date"], werk_table_options["date_range"]))
    matches =  \
           (not werk_table_options["id"] or werk["id"] == tryint(werk_table_options["id"])) and \
           werk["level"] in werk_table_options["levels"] and \
           werk["class"] in werk_table_options["classes"] and \
           werk["compatible"] in werk_table_options["compatibility"] and \
           werk_table_options["component"] in ( None, werk["component" ]) and \
           werk["date"] >= werk_table_options["date_range"][0] and \
           werk["date"] <= werk_table_options["date_range"][1]

    if not matches:
        return False

    if werk_table_options["edition"]:
        if werk_table_options["edition"] == "cre" and werk["id"] >= 8000:
            return False
        if werk_table_options["edition"] == "cee" and werk["id"] < 8000:
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



def render_werk_table_options():
    werk_table_options = {}
    html.begin_form("werks")
    html.hidden_field("wo_set", "set")
    begin_floating_options("werks", is_open=True)
    for name, height, vs, default_value in werk_table_option_entries:
        if html.var("wo_set"):
            value = vs.from_html_vars("wo_" + name)
        else:
            value = default_value
        werk_table_options.setdefault(name, value)
        render_floating_option(name, height, "wo_", vs, werk_table_options[name])
    end_floating_options(reset_url = html.makeuri([], remove_prefix = ""))
    html.hidden_fields()
    html.end_form()

    from_date, until_date = Timerange().compute_range(werk_table_options["date"])[0]
    werk_table_options["date_range"] = from_date, until_date

    return werk_table_options


def render_werk_id(werk):
    return "#%04d" % werk["id"]

def render_werk_date(werk):
    return time.strftime("%Y-%m-%d", time.localtime(werk["date"]))

def render_werk_level(werk):
    return werk_levels[werk["level"]]

def render_werk_class(werk):
    return werk_classes[werk["class"]]

def render_werk_compatibility(werk):
    return werk_compatibilities[werk["compatible"]]

def render_werk_component(werk):
    if werk["component"] not in werk_components:
        werk_components[werk["component"]] = werk["component"]
        html.write("<li>Invalid component %s in werk %s</li>" % (werk["component"], render_werk_id(werk)))
    return werk_components[werk["component"]]

def render_werk_title(werk):
    title = werk["title"]
    # if the title begins with the name or names of check plugins, then
    # we link to the man pages of those checks
    if ":" in title:
        parts = title.split(":", 1)
        title = insert_manpage_links(parts[0]) + ":" + parts[1]
    return title

def insert_manpage_links(text):
    parts = text.replace(",", " ").split()
    new_parts = []
    for part in parts:
        if os.path.exists(defaults.check_manpages_dir + "/" + part):
            part = '<a href="wato.py?mode=check_manpage&check_type=%s">%s</a>' % (
                part, part)
        new_parts.append(part)
    return ", ".join(new_parts)


def werks_sorted_by_date():
    werks_by_date = g_werks.values()
    werks_by_date.sort(cmp = lambda a, b: -cmp(a["date"], b["date"]))
    return werks_by_date

