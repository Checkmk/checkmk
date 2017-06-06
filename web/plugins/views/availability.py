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

import availability, table
from valuespec import *

# Variable name conventions
# av_rawdata: a two tier dict: (site, host) -> service -> list(spans)
#   In case of BI (site, host) is (None, aggr_group), service is aggr_name
# availability_table: a list of dicts. Each dicts describes the availability
#   information of one object (seconds being OK, CRIT, etc.)

#   .--Options-------------------------------------------------------------.
#   |                   ___        _   _                                   |
#   |                  / _ \ _ __ | |_(_) ___  _ __  ___                   |
#   |                 | | | | '_ \| __| |/ _ \| '_ \/ __|                  |
#   |                 | |_| | |_) | |_| | (_) | | | \__ \                  |
#   |                  \___/| .__/ \__|_|\___/|_| |_|___/                  |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |  Handling of all options for tuning availability computation and     |
#   |  display.                                                            |
#   '----------------------------------------------------------------------'

# Get availability options without rendering the valuespecs
def get_availability_options_from_url(what):
    html.plug()
    avoptions = render_availability_options(what)
    html.drain()
    html.unplug()
    return avoptions


def render_availability_options(what):
    if html.var("_reset"):
        config.save_user_file("avoptions", {})
        for varname in html.vars.keys():
            if varname.startswith("avo_"):
                html.del_var(varname)
            html.del_var("avoptions")

    avoptions = availability.get_default_avoptions()

    # Users of older versions might not have all keys set. The following
    # trick will merge their options with our default options.
    avoptions.update(config.load_user_file("avoptions", {}))

    is_open = False
    html.begin_form("avoptions")
    html.hidden_field("avoptions", "set")
    avoption_entries = availability.get_avoption_entries(what)
    if html.var("avoptions") == "set":
        for name, height, show_in_reporting, vs in avoption_entries:
            try:
                avoptions[name] = vs.from_html_vars("avo_" + name)
                vs.validate_value(avoptions[name], "avo_" + name)
            except MKUserError, e:
                html.add_user_error(e.varname, e)
                is_open = True

    range_vs = None
    for name, height, show_in_reporting, vs in avoption_entries:
        if name == 'rangespec':
            range_vs = vs

    try:
        range, range_title = range_vs.compute_range(avoptions["rangespec"])
        avoptions["range"] = range, range_title
    except MKUserError, e:
        html.add_user_error(e.varname, e)

    if html.has_user_errors():
        html.show_user_errors()

    begin_floating_options("avoptions", is_open)
    for name, height, show_in_reporting, vs in avoption_entries:
        render_floating_option(name, height, "avo_", vs, avoptions.get(name))
    end_floating_options(reset_url = html.makeuri([("_reset", "1")], remove_prefix="avo_", delvars=["apply", "filled_in"]))

    html.hidden_fields()
    html.end_form()


    if html.form_submitted():
        config.save_user_file("avoptions", avoptions)

    return avoptions


#.
#   .--Rendering-----------------------------------------------------------.
#   |            ____                _           _                         |
#   |           |  _ \ ___ _ __   __| | ___ _ __(_)_ __   __ _             |
#   |           | |_) / _ \ '_ \ / _` |/ _ \ '__| | '_ \ / _` |            |
#   |           |  _ <  __/ | | | (_| |  __/ |  | | | | | (_| |            |
#   |           |_| \_\___|_| |_|\__,_|\___|_|  |_|_| |_|\__, |            |
#   |                                                    |___/             |
#   +----------------------------------------------------------------------+
#   |  Rendering availability data into HTML.                              |
#   '----------------------------------------------------------------------'

# Hints:
# There are several modes for displaying data
# 1. Availability table
# 2. Timeline view with chronological events of one object
# There are two types of data sources
# a. Hosts/Services (identified by site, host and service)
# b. BI aggregates (identified by aggr_groups and aggr_name)
# The code flow for these four combinations is different
#

# Render the page showing availability table or timelines. It
# is (currently) called by views.py, when showing a view but
# availability mode is activated.
def render_availability_page(view, datasource, filterheaders, display_options, only_sites, limit):
    if handle_edit_annotations():
        return

    # We make reports about hosts, services or BI aggregates
    if "service" in datasource["infos"]:
        what = "service"
    elif "aggr_name" in datasource["infos"]:
        what = "bi"
    else:
        what = "host"

    avoptions = get_availability_options_from_url(what)
    time_range, range_title = avoptions["range"]

    # We have two display modes:
    # - Show availability table (stats) "table"
    # - Show timeline                   "timeline"
    # --> controlled by URL variable "av_mode"
    av_mode = html.var("av_mode", "table")

    if av_mode == "timeline":
        title = _("Availability Timeline")
    else:
        title = _("Availability")

    # This is combined with the object selection
    # - Show all objects
    # - Show one specific object
    # --> controlled by URL variables "av_site", "av_host" and "av_service"
    # --> controlled by "av_aggr" in case of BI aggregate
    title += " - "
    if html.var("av_host"):
        av_object = (html.var("av_site"), html.var("av_host"), html.var("av_service"))
        title += av_object[1]
        if av_object[2]:
            title += " - " + av_object[2]
    elif html.var("av_aggr"):
        av_object = (None, None, html.var("av_aggr"))
        title += av_object[2]
    else:
        av_object = None
        title += view_title(view)

    # Now compute all data, we need this also for CSV export
    if not html.has_user_errors():
        av_rawdata = availability.get_availability_rawdata(what, filterheaders, only_sites,
                                                           av_object, av_mode == "timeline", avoptions)
        av_data = availability.compute_availability(what, av_rawdata, avoptions)

    # Do CSV ouput
    if html.output_format == "csv_export":
        output_availability_csv(what, av_data, avoptions)
        return

    title += " - " + range_title

    if 'H' in display_options:
        html.body_start(title, stylesheets=["pages","views","status"], force=True)
    if 'T' in display_options:
        html.top_heading(title)

    handle_delete_annotations()

    # Remove variables for editing annotations, otherwise they will make it into the uris
    html.del_all_vars("editanno_")
    html.del_all_vars("anno_")
    if html.var("filled_in") == "editanno":
        html.del_var("filled_in")

    if 'B' in display_options:
        html.begin_context_buttons()
        togglebutton("avoptions", html.has_user_errors(), "painteroptions", _("Configure details of the report"))
        html.context_button(_("Status View"), html.makeuri([("mode", "status")]), "status")
        if config.reporting_available() and config.may("general.reporting"):
            html.context_button(_("Export as PDF"), html.makeuri([], filename="report_instant.py"), "report")
        if av_mode == "table":
            html.context_button(_("Export as CSV"), html.makeuri([("output_format", "csv_export")]), "download_csv")

        if av_mode == "timeline" or av_object:
            html.context_button(_("Availability"), html.makeuri([("av_mode", "availability"), ("av_host", ""), ("av_aggr", "")]), "availability")
        elif not av_object:
            html.context_button(_("Timeline"), html.makeuri([("av_mode", "timeline")]), "timeline")

        elif av_mode == "timeline" and what != "bi":
            history_url = availability.history_url_of(av_object, time_range)
            html.context_button(_("History"), history_url, "history")
        html.end_context_buttons()

    # Render the avoptions again to get the HTML code, because the HTML vars have changed
    # above (anno_ and editanno_ has been removed, which must not be part of the form
    avoptions = render_availability_options(what)

    if not html.has_user_errors():
        do_render_availability(what, av_rawdata, av_data, av_mode, av_object, avoptions)

    if 'Z' in display_options:
        html.bottom_footer()
    if 'H' in display_options:
        html.body_end()


def do_render_availability(what, av_rawdata, av_data, av_mode, av_object, avoptions):

    if av_mode == "timeline":
        render_availability_timelines(what, av_data, avoptions)
    else:
        availability_tables = availability.compute_availability_groups(what, av_data, avoptions)
        render_availability_tables(availability_tables, what, avoptions)

    annotations = load_annotations()
    render_annotations(annotations, av_rawdata, what, avoptions, omit_service = av_object != None)


def render_availability_tables(availability_tables, what, avoptions):

    if not availability_tables:
        html.message(_("No matching hosts/services."))
        return

    for group_title, availability_table in availability_tables:
        render_availability_table(group_title, availability_table, what, avoptions)

    # Legend for Availability levels
    av_levels = avoptions["av_levels"]
    if av_levels and not "omit_av_levels" in avoptions["labelling"]:
        warn, crit = av_levels
        html.write('<div class="avlegend levels">')
        html.write('<h3>%s</h3>' % _("Availability levels"))
        html.write('<div class="state state0">%s</div><div class=level>&ge; %.3f%%</div>' % (_("OK"), warn))
        html.write('<div class="state state1">%s</div><div class=level>&ge; %.3f%%</div>' % (_("WARN"), crit))
        html.write('<div class="state state2">%s</div><div class=level>&lt; %.3f%%</div>' % (_("CRIT"), crit))
        html.write('</div>')

    # Legend for timeline
    if "display_timeline_legend" in avoptions["labelling"] and avoptions["show_timeline"]:
        render_timeline_legend(what)


def render_availability_timelines(what, av_data, avoptions):
    for av_entry in av_data:
        render_availability_timeline(what, av_entry, avoptions)


def render_availability_timeline(what, av_entry, avoptions):

    html.write("<h3>%s %s</h3>" % (_("Timeline of"), availability.object_title(what, av_entry)))

    timeline_rows = av_entry["timeline"]
    if not timeline_rows:
        html.write('<div class=info>%s</div>' % _("No information available"))
        return

    timeline_layout = availability.layout_timeline(what, timeline_rows, av_entry["considered_duration"], avoptions, "standalone")
    render_timeline_bar(timeline_layout, "standalone")
    render_date = timeline_layout["render_date"]
    render_number = availability.render_number_function(avoptions)


    # TODO: Hier fehlt bei BI der Timewarpcode (also der Baum im Zauberzustand)
    # if what == "bi":
    #    render_timewarp(

    # Table with detailed events
    table.begin("av_timeline", "", css="timelineevents")
    for row_nr, row in enumerate(timeline_layout["table"]):
        table.row()
        table.cell(_("Links"), css="buttons")
        if what == "bi":
            url = html.makeuri([("timewarp", str(int(row["from"])))])
            if html.var("timewarp") and int(html.var("timewarp")) == int(row["from"]):
                html.disabled_icon_button("timewarp_off")
            else:
                html.icon_button(url, _("Time warp - show BI aggregate during this time period"), "timewarp")
        else:
            url = html.makeuri([("anno_site", av_entry["site"]),
                                ("anno_host", av_entry["host"]),
                                ("anno_service", av_entry["service"]),
                                ("anno_from", row["from"]),
                                ("anno_until", row["until"])])
            html.icon_button(url, _("Create an annotation for this period"), "annotation")

        table.cell(_("From"),     row["from_text"],     css="nobr narrow")
        table.cell(_("Until"),    row["until_text"],    css="nobr narrow")
        table.cell(_("Duration"), row["duration_text"], css="narrow number")
        table.cell(_("State"),    row["state_name"],    css=row["css"] + " state narrow")
        table.cell(_("Last Known Plugin Output"), row.get("log_output", ""))

    table.end()

    # Legend for timeline
    if "display_timeline_legend" in avoptions["labelling"]:
        render_timeline_legend(what)



def render_timeline_legend(what):
    html.write('<div class="avlegend timeline">')
    html.write('<h3>%s</h3>' % _('Timeline colors'))
    html.write('<div class="state state0">%s</div>' % (what == "host" and _("UP") or _("OK")))
    if what != "host":
        html.write('<div class="state state1">%s</div>'    % _("WARN"))
    html.write('<div class="state state2">%s</div>' % (what == "host" and _("DOWN") or _("CRIT")))
    html.write('<div class="state state3">%s</div>' % (what == "host" and _("UNREACH") or _("UNKNOWN")))
    html.write('<div class="state flapping">%s</div>' % _("Flapping"))
    if what != "host":
        html.write('<div class="state hostdown">%s</div>' % _("H.Down"))
    html.write('<div class="state downtime">%s</div>' % _("Downtime"))
    html.write('<div class="state ooservice">%s</div>' % _("OO/Service"))
    html.write('<div class="state unmonitored">%s</div>' % _("unmonitored"))
    html.write('</div>')


def render_availability_table(group_title, availability_table, what, avoptions):

    av_table = availability.layout_availability_table(what, group_title, availability_table, avoptions)

    # TODO: If summary line is activated, then sorting should now move that line to the
    # top. It should also stay at the bottom. This would require an extension to the
    # table.py module.
    table.begin("av_items", av_table["title"], css="availability",
        searchable = False, limit = None,
        omit_headers = "omit_headers" in avoptions["labelling"])

    for row in av_table["rows"]:
        table.row()

        # Column with icons
        timeline_url = None
        if row["urls"]:
            table.cell("", css="buttons")
            for image, tooltip, url in row["urls"]:
                html.icon_button(url, tooltip, image)
                if image == "timeline":
                    timeline_url = url

        # Column with host/service or aggregate name
        for title, (name, url) in zip(av_table["object_titles"], row["object"]):
            table.cell(title, '<a href="%s">%s</a>' % (url, name))

        if "timeline" in row:
            table.cell(_("Timeline"), css="timeline")
            html.write('<a href="%s">' % timeline_url)
            render_timeline_bar(row["timeline"], "inline")
            html.write('</a>')

        # Columns with the actual availability data
        for (title, help), (text, css) in zip(av_table["cell_titles"], row["cells"]):
            table.cell(title, text, css=css, help=help)

    if "summary" in av_table:
        table.row(css="summary", fixed=True)
        if row["urls"]:
            table.cell("", "") # Empty cell in URLs column
        table.cell("", _("Summary"), css="heading")
        for x in range(1, len(av_table["object_titles"])):
            table.cell("", "") # empty cells, of more object titles than one
        if "timeline" in row:
            table.cell("", "")

        for (title, help), (text, css) in zip(av_table["cell_titles"], av_table["summary"]):
            table.cell(title, text, css="heading " + css, help=help)

    return table.end() # returns Table data if fetch == True


def render_timeline_bar(timeline_layout, style):
    render_date = timeline_layout["render_date"]
    from_time, until_time = timeline_layout["range"]
    html.write('<div class="timelinerange %s">' % style)
    if style == "standalone":
        html.write('<div class=from>%s</div><div class=until>%s</div></div>' % (
            render_date(from_time), render_date(until_time)))

    if "time_choords" in timeline_layout:
        timebar_width = 500 # CSS width of inline timebar
        for position, title in timeline_layout["time_choords"]:
            pixel = timebar_width * position
            html.write('<div title="%s" class="timelinechoord" style="left: %dpx"></div>' % (title, pixel))

    html.write('<table class="timeline %s">' % style)
    html.write('<tr class=timeline>')
    for row_nr, title, width, css in timeline_layout["spans"]:
        if style == "standalone" and row_nr != None:
            hovercode = ' onmouseover="timeline_hover(this, %d, 1);" onmouseout="timeline_hover(this, %d, 0);"' % (row_nr, row_nr)
        else:
            hovercode = ""

        html.write('<td%s style="width: %.3f%%" title="%s" class="%s"></td>' % (
                     hovercode, width, html.attrencode(title), css))
    html.write("</tr></table>")
    html.write("</div>")



#.
#   .--BI------------------------------------------------------------------.
#   |                              ____ ___                                |
#   |                             | __ )_ _|                               |
#   |                             |  _ \| |                                |
#   |                             | |_) | |                                |
#   |                             |____/___|                               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Special code for Business Intelligence availability                 |
#   '----------------------------------------------------------------------'

# Render availability of a BI aggregate. This is currently
# no view and does not support display options
# TODO: Why should we handle this in a special way? Probably because we cannot
# get the list of BI aggregates from the statehist table but use the views
# logic for getting the aggregates. As soon as we have cleaned of the visuals,
# filters, contexts etc we can unify the code!
def render_bi_availability(title, aggr_rows):
    av_mode = html.var("av_mode", "availability")

    avoptions = get_availability_options_from_url("bi")
    time_range, range_title = avoptions["range"]

    if av_mode == "timeline":
        title = _("Timeline of ") + title
    else:
        title = _("Availability of ") + title

    if html.output_format != "csv_export":
        html.body_start(title, stylesheets=["pages","views","status", "bi"], javascripts=['bi'])
        html.top_heading(title)
        html.begin_context_buttons()
        togglebutton("avoptions", False, "painteroptions", _("Configure details of the report"))
        html.context_button(_("Status View"), html.makeuri([("mode", "status")]), "status")
        if config.reporting_available() and config.may("general.reporting"):
            html.context_button(_("Export as PDF"), html.makeuri([], filename="report_instant.py"), "report")
        if av_mode == "availability":
            html.context_button(_("Export as CSV"), html.makeuri([("output_format", "csv_export")]), "download_csv")

        if av_mode == "timeline":
            html.context_button(_("Availability"), html.makeuri([("av_mode", "availability")]), "availability")

        elif len(aggr_rows) == 1:
            aggr_name = aggr_rows[0]["aggr_name"]
            aggr_group = aggr_rows[0]["aggr_group"]
            timeline_url = html.makeuri([("av_mode", "timeline"), ("av_aggr_name", aggr_name), ("av_aggr_group", aggr_group)])
            html.context_button(_("Timeline"), timeline_url, "timeline")
        html.end_context_buttons()

        avoptions = render_availability_options("bi")

    timewarpcode = ""
    if not html.has_user_errors():
        spans = []
        for aggr_row in aggr_rows:
            tree = aggr_row["aggr_tree"]
            reqhosts = tree["reqhosts"]
            try:
                timewarp = int(html.var("timewarp"))
            except:
                timewarp = None
            these_spans, timewarp_tree_state = availability.get_bi_spans(tree, aggr_row["aggr_group"], avoptions, timewarp)
            spans += these_spans
            if timewarp and timewarp_tree_state:
                state, assumed_state, node, subtrees = timewarp_tree_state
                eff_state = state
                if assumed_state != None:
                    eff_state = assumed_state
                row = {
                        "aggr_tree"            : tree,
                        "aggr_treestate"       : timewarp_tree_state,
                        "aggr_state"           : state,          # state disregarding assumptions
                        "aggr_assumed_state"   : assumed_state,  # is None, if there are no assumptions
                        "aggr_effective_state" : eff_state,      # is assumed_state, if there are assumptions, else real state
                        "aggr_name"            : node["title"],
                        "aggr_output"          : eff_state["output"],
                        "aggr_hosts"           : node["reqhosts"],
                        "aggr_function"        : node["func"],
                        "aggr_group"           : html.var("aggr_group"),
                }
                tdclass, htmlcode = bi.render_tree_foldable(row, boxes=False, omit_root=False,
                                         expansion_level=bi.load_ex_level(), only_problems=False, lazy=False)
                html.plug()
                html.write('<h3>')

                # render icons for back and forth
                if int(these_spans[0]["from"]) == timewarp:
                    html.disabled_icon_button("back_off")
                have_forth = False
                previous_span = None
                for span in these_spans:
                    if int(span["from"]) == timewarp and previous_span != None:
                        html.icon_button(html.makeuri([("timewarp", str(int(previous_span["from"])))]), _("Jump one phase back"), "back")
                    elif previous_span and int(previous_span["from"]) == timewarp and span != these_spans[-1]:
                        html.icon_button(html.makeuri([("timewarp", str(int(span["from"])))]), _("Jump one phase forth"), "forth")
                        have_forth = True
                    previous_span = span
                if not have_forth:
                    html.disabled_icon_button("forth_off")

                html.write(" &nbsp; ")
                html.icon_button(html.makeuri([("timewarp", "")]), _("Close Timewarp"), "closetimewarp")
                timewarpcode = html.drain()
                html.unplug()
                timewarpcode += '%s %s</h3>' % (_("Timewarp to "), time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timewarp))) + \
                               '<table class="data table timewarp"><tr class="data odd0"><td class="%s">' % tdclass + \
                               htmlcode + \
                               '</td></tr></table>'

        av_rawdata = availability.spans_by_object(spans)
        av_data = availability.compute_availability("bi", av_rawdata, avoptions)

        if html.output_format == "csv_export":
            output_availability_csv("bi", av_data, avoptions)
            return

        html.write(timewarpcode)
        do_render_availability("bi", av_rawdata, av_data, av_mode, None, avoptions)# ,  timewarpcode)

    html.bottom_footer()
    html.body_end()

#.
#   .--Annotations---------------------------------------------------------.
#   |         _                      _        _   _                        |
#   |        / \   _ __  _ __   ___ | |_ __ _| |_(_) ___  _ __  ___        |
#   |       / _ \ | '_ \| '_ \ / _ \| __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      / ___ \| | | | | | | (_) | || (_| | |_| | (_) | | | \__ \       |
#   |     /_/   \_\_| |_|_| |_|\___/ \__\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  This code deals with retrospective annotations and downtimes.       |
#   '----------------------------------------------------------------------'

# Example for annotations:
# {
#   ( "mysite", "foohost", "myservice" ) : # service might be None
#       [
#         {
#            "from"       : 1238288548,
#            "until"      : 1238292845,
#            "text"       : u"Das ist ein Text über mehrere Zeilen, oder was weiß ich",
#            "downtime"   : True, # Treat as scheduled Downtime,
#            "date"       : 12348854885, # Time of entry
#            "author"     : "mk",
#         },
#         # ... further entries
#      ]
# }


def save_annotations(annotations):
    path = defaults.var_dir + "/availability_annotations.mk"
    file(path + ".new", "w").write(repr(annotations) + "\n")
    os.rename(path + ".new", path)


def load_annotations(lock = False):
    path = defaults.var_dir + "/availability_annotations.mk"
    if not os.path.exists(path):
        # Try old path
        path = defaults.var_dir + "/web/statehist_annotations.mk"
    if os.path.exists(path):
        if lock:
            aquire_lock(path)
        return eval(file(path).read())
    else:
        return {}

def update_annotations(site_host_svc, annotation, replace_existing):
    annotations = load_annotations(lock = True)
    entries = annotations.get(site_host_svc, [])
    new_entries = []
    for entry in entries:
        if entry == replace_existing:
            continue # Skip existing entries with same identity
        new_entries.append(entry)
    new_entries.append(annotation)
    annotations[site_host_svc] = new_entries
    save_annotations(annotations)


def find_annotation(annotations, site_host_svc, fromtime, untiltime):
    entries = annotations.get(site_host_svc)
    if not entries:
        return None
    for annotation in entries:
        if annotation["from"] == fromtime \
            and annotation["until"] == untiltime:
            return annotation
    return None

def delete_annotation(annotations, site_host_svc, fromtime, untiltime):
    entries = annotations.get(site_host_svc)
    if not entries:
        return
    found = None
    for nr, annotation in enumerate(entries):
        if annotation["from"] == fromtime \
            and annotation["until"] == untiltime:
            found = nr
            break
    if found != None:
        del entries[nr]


def render_annotations(annotations, by_host, what, avoptions, omit_service):
    (from_time, until_time), range_title = avoptions["range"]
    format = "%H:%M:%S"
    if time.localtime(from_time)[:3] != time.localtime(until_time-1)[:3]:
        format = "%Y-%m-%d " + format
    def render_date(ts):
        return time.strftime(format, time.localtime(ts))

    annos_to_render = []
    annos_rendered = set()

    for site_host, avail_entries in by_host.iteritems():
        for service in avail_entries.keys():
            site_host_svc = site_host[0], site_host[1], (service or None)
            annotations_to_check = annotations.get(site_host_svc, [])
            if what == "service": # Also show host annotations for services
                annotations_to_check += annotations.get((site_host[0], site_host[1], None), [])
            for annotation in annotations_to_check:
                if (annotation["from"] >= from_time and annotation["from"] <= until_time) or \
                   (annotation["until"] >= from_time and annotation["until"] <= until_time):
                   if id(annotation) not in annos_rendered:
                       annos_to_render.append((site_host_svc, annotation))
                       annos_rendered.add(id(annotation))

    annos_to_render.sort(cmp=lambda a,b: cmp(a[1]["from"], b[1]["from"]) or cmp(a[0], b[0]))

    labelling = avoptions["labelling"]

    table.begin(title = _("Annotations"), omit_if_empty = True)
    for (site_id, host, service), annotation in annos_to_render:
        table.row()
        table.cell("", css="buttons")
        anno_vars = [
          ( "anno_site", site_id ),
          ( "anno_host", host ),
          ( "anno_service", service or "" ),
          ( "anno_from", int(annotation["from"]) ),
          ( "anno_until", int(annotation["until"]) ),
        ]
        edit_url = html.makeuri(anno_vars)
        html.icon_button(edit_url, _("Edit this annotation"), "edit")
        delete_url = html.makeactionuri([("_delete_annotation", "1")] + anno_vars)
        html.icon_button(delete_url, _("Delete this annotation"), "delete")

        if not omit_service:
            if not "omit_host" in labelling:
                host_url = "view.py?" + html.urlencode_vars([("view_name", "hoststatus"), ("site", site_id), ("host", host)])
                table.cell(_("Host"), '<a href="%s">%s</a>' % (host_url, host))

            if service:
                service_url = "view.py?" + html.urlencode_vars([("view_name", "service"), ("site", site_id), ("host", host), ("service", service)])
                # TODO: honor use_display_name. But we have no display names here...
                service_name = service
                table.cell(_("Service"), '<a href="%s">%s</a>' % (service_url, service_name))

        table.cell(_("From"), render_date(annotation["from"]), css="nobr narrow")
        table.cell(_("Until"), render_date(annotation["until"]), css="nobr narrow")
        table.cell(_("Annotation"), html.attrencode(annotation["text"]))
        table.cell(_("Author"), annotation["author"])
        table.cell(_("Entry"), render_date(annotation["date"]), css="nobr narrow")
    table.end()



def edit_annotation():
    site_id = html.var("anno_site") or ""
    hostname = html.var("anno_host")
    service = html.var("anno_service") or None
    fromtime = float(html.var("anno_from"))
    untiltime = float(html.var("anno_until"))
    site_host_svc = (site_id, hostname, service)

    # Find existing annotation with this specification
    annotations = load_annotations()
    annotation = find_annotation(annotations, site_host_svc, fromtime, untiltime)
    if not annotation:
        value = {
            "from"    : fromtime,
            "until"   : untiltime,
            "text"    : "",
        }
    else:
        value = annotation.copy()

    value["host"] = hostname
    value["service"] = service
    value["site"] = site_id

    # FIXME: Why use plugging here? Can we clean this up?
    html.plug()

    title = _("Edit annotation of ") + hostname
    if service:
        title += "/" + service
    html.body_start(title, stylesheets=["pages","views","status"])
    html.top_heading(title)

    html.begin_context_buttons()
    html.context_button(_("Abort"), html.makeuri([("anno_host", "")]), "abort")
    html.end_context_buttons()

    value = forms.edit_dictionary([
        ( "site",    TextAscii(title = _("Site")) ),
        ( "host",    TextUnicode(title = _("Hostname")) ),
        ( "service", Optional(TextUnicode(allow_empty=False), sameline = True, title = _("Service")) ),
        ( "from",    AbsoluteDate(title = _("Start-Time"), include_time = True) ),
        ( "until",   AbsoluteDate(title = _("End-Time"), include_time = True) ),
        ( "text",    TextAreaUnicode(title = _("Annotation"), allow_empty = False) ), ],
        value,
        varprefix = "editanno_",
        formname = "editanno",
        focus = "text")

    if value:
        site_host_svc = value["site"], value["host"], value["service"]
        del value["site"]
        del value["host"]
        value["date"] = time.time()
        value["author"] = config.user_id
        update_annotations(site_host_svc, value, replace_existing=annotation)
        html.drain() # omit previous HTML code, not needed
        html.unplug()
        html.del_all_vars(prefix = "editanno_")
        html.del_var("filled_in")
        return False

    html.unplug() # show HTML code

    html.bottom_footer()
    html.body_end()
    return True


# Called at the beginning of every availability page
def handle_delete_annotations():
    if html.var("_delete_annotation"):
        site_id = html.var("anno_site") or ""
        hostname = html.var("anno_host")
        service = html.var("anno_service") or None
        fromtime = float(html.var("anno_from"))
        untiltime = float(html.var("anno_until"))
        site_host_svc = (site_id, hostname, service)

        annotations = load_annotations()
        annotation = find_annotation(annotations, site_host_svc, fromtime, untiltime)
        if not annotation:
            return

        if not html.confirm(_("Are you sure that you want to delete the annotation '%s'?" % annotation["text"])):
            return

        delete_annotation(annotations, site_host_svc, fromtime, untiltime)
        save_annotations(annotations)

def handle_edit_annotations():
    # Avoid reshowing edit form after edit and reload
    if html.is_transaction() and not html.transaction_valid():
        return False
    if html.var("anno_host") and not html.var("_delete_annotation"):
        finished = edit_annotation()
    else:
        finished = False

    return finished

#.
#   .--CSV Export----------------------------------------------------------.
#   |         ____ ______     __  _____                       _            |
#   |        / ___/ ___\ \   / / | ____|_  ___ __   ___  _ __| |_          |
#   |       | |   \___ \\ \ / /  |  _| \ \/ / '_ \ / _ \| '__| __|         |
#   |       | |___ ___) |\ V /   | |___ >  <| |_) | (_) | |  | |_          |
#   |        \____|____/  \_/    |_____/_/\_\ .__/ \___/|_|   \__|         |
#   |                                       |_|                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def output_availability_csv(what, av_data, avoptions):
    def cells_from_row(object_titles, cell_titles, row_object, row_cells):
        for title, (name, url) in zip(object_titles, row_object):
            table.cell(title, name)
        for (title, help), (text, css) in zip(cell_titles, row_cells):
            table.cell(title, text)

    av_output_set_content_disposition(_("Check_MK-Availability"))
    availability_tables = availability.compute_availability_groups(what, av_data, avoptions)
    table.begin("av_items", output_format = "csv")
    for group_title, availability_table in availability_tables:
        av_table = availability.layout_availability_table(what, group_title, availability_table, avoptions)
        pad = 0
        for row in av_table["rows"]:
            table.row()
            cells_from_row(av_table["object_titles"], av_table["cell_titles"],
                           row["object"], row["cells"])
            # presumably all rows have the same width
            pad = len(row["object"]) - 1
        table.row()
        cells_from_row(av_table["object_titles"], av_table["cell_titles"],
                       [(_("Summary"), "")] + [("", "")] * pad, av_table["summary"])
    table.end()

def av_output_set_content_disposition(title):
    filename = '%s-%s.csv' % (title, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time())))
    if type(filename) == unicode:
        filename = filename.encode("utf-8")
    html.req.headers_out['Content-Disposition'] = 'Attachment; filename="%s"' % filename
