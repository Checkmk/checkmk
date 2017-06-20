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

import pprint
import os
import copy
import urlparse
import config, views, userdb, pagetypes
import notify, werks
import sites
from lib import *
from log import logger
import cmk.paths
import cmk.store as store

try:
    import simplejson as json
except ImportError:
    import json

# Constants to be used in snapins
snapin_width = 230


# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False
sidebar_snapins = {}
search_plugins  = []

def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == current_language and not force:
        return

    # Load all snapins
    global sidebar_snapins
    sidebar_snapins = {}
    global search_plugins
    search_plugins = []
    load_web_plugins("sidebar", globals())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language

    # Declare permissions: each snapin creates one permission
    config.declare_permission_section("sidesnap", _("Sidebar snapins"), do_sort = True)
    for name, snapin in sidebar_snapins.items():
        config.declare_permission("sidesnap.%s" % name,
            snapin["title"],
            snapin["description"],
            snapin["allowed"])


# Helper functions to be used by snapins
def render_link(text, url, target="main", onclick = None):
    # Convert relative links into absolute links. We have three kinds
    # of possible links and we change only [3]
    # [1] protocol://hostname/url/link.py
    # [2] /absolute/link.py
    # [3] relative.py
    if not (":" in url[:10]) and not url.startswith("javascript") and url[0] != '/':
        url = config.url_prefix() + "check_mk/" + url
    return html.render_a(text, href=url, class_="link", target=target or '',\
                         onfocus = "if (this.blur) this.blur();",\
                         onclick = onclick or None)


def link(text, url, target="main", onclick = None):
    return html.write(render_link(text, url, target=target, onclick=onclick))


def simplelink(text, url, target="main"):
    link(text, url, target)
    html.br()


def bulletlink(text, url, target="main", onclick = None):
    html.open_li(class_="sidebar")
    link(text, url, target, onclick)
    html.close_li()


def iconlink(text, url, icon):
    html.open_a(class_=["iconlink", "link"], target="main", href=url)
    html.icon(icon=icon, help=None, cssclass="inline")
    html.write(text)
    html.close_a()
    html.br()


def nagioscgilink(text, target):
    html.open_li(class_="sidebar")
    html.a(text, class_="link", target="main", href="%snagios/cgi-bin/%s" % (html.url_prefix(), target))
    html.close_li()


def begin_footnote_links():
    html.open_div(class_="footnotelink")

def end_footnote_links():
    html.close_div()

def footnotelinks(links):
    begin_footnote_links()
    for text, target in links:
        link(text, target)
    end_footnote_links()


def heading(text):
    html.write("<h3>%s</h3>\n" % html.attrencode(text))


def snapin_site_choice(ident, choices):
    sites = config.user.load_file("sidebar_sites", {})
    site  = sites.get(ident, "")
    if site == "":
        only_sites = None
    else:
        only_sites = [site]

    site_choices = config.get_event_console_site_choices()
    if len(site_choices) <= 1:
        return None

    site_choices = [ ("", _("All sites")), ] + site_choices
    html.select("site", site_choices, site, onchange="set_snapin_site(event, %s, this)" % json.dumps(ident))

    return only_sites


# Load current state of user's sidebar. Convert from
# old format (just a snapin list) to the new format
# (dictionary) on the fly
def load_user_config():
    path = config.user.confdir + "/sidebar.mk"
    user_config = store.load_data_from_file(path)
    if user_config == None:
        user_config = {
            "snapins": config.sidebar,
            "fold":    False,
        }

    if type(user_config) == list:
        user_config = {
            "snapins" : user_config,
            "fold":     False,
        }

    # Remove entries the user is not allowed for or which have state "off" (from legacy version)
    # silently skip configured but not existant snapins
    user_config["snapins"] = [
          entry for entry in user_config["snapins"]
                if entry[0] in sidebar_snapins
                   and entry[1] != "off"
                   and config.user.may("sidesnap." + entry[0])]

    return user_config


def save_user_config(user_config):
    if config.user.may("general.configure_sidebar"):
        config.user.save_file("sidebar", user_config)


def get_check_mk_edition_title():
    import cmk
    if cmk.is_enterprise_edition():
        if cmk.is_demo():
            return "Enterprise (Demo)"
        else:
            return "Enterprise"

    elif cmk.is_managed_edition():
        return "Managed"

    else:
        return "Raw"


def sidebar_head():
    html.open_div(id_="side_header")
    html.div('', id_="side_fold")
    html.open_a(href=config.user.get_attribute("start_url") or config.start_url,
                target="main", title=_("Go to main overview"))
    html.img(src="images/sidebar_top.png", id_="side_bg")
    html.open_div(id_="side_version")
    html.open_a(href="version.py", target="main", title=_("Open release notes"))
    html.write(get_check_mk_edition_title())
    html.br()
    html.write(cmk.__version__)

    if werks.may_acknowledge():
        num_unacknowledged_werks = werks.num_unacknowledged_incompatible_werks()
        if num_unacknowledged_werks:
            html.span(num_unacknowledged_werks, class_="unack_werks",
                      title=_("%d unacknowledged incompatible werks") % num_unacknowledged_werks)
    html.close_a()
    html.close_div()
    html.close_a()
    html.close_div()


def render_messages():
    for msg in notify.get_gui_messages():
        if 'gui_hint' in msg['methods']:
            html.open_div(id_="message-%s" % msg['id'], class_=["popup_msg"])
            html.a("x", href="javascript:void(0)", class_=["close"], onclick="message_close(\'%s\')" % msg['id'])
            html.write_text(msg['text'].replace('\n', '<br/>\n'))
            html.close_div()
        if 'gui_popup' in msg['methods']:
            html.javascript('alert(\'%s\'); mark_message_read("%s")' %
                (html.attrencode(msg['text']).replace('\n', '\\n'), msg['id']))

def ajax_get_messages():
    render_messages()

def ajax_message_read():
    try:
        notify.delete_gui_message(html.var('id'))
        html.write("OK")
    except:
        if config.debug:
            raise
        html.write("ERROR")

def sidebar_foot():
    html.open_div(id_="side_footer")
    if config.user.may("general.configure_sidebar"):
        html.icon_button("sidebar_add_snapin.py", _("Add snapin to the sidebar"), "sidebar_addsnapin",
                         target="main")
    # editing the profile is not possible on remote sites which are sync targets
    # of a central WATO system
    if config.wato_enabled and \
       (config.user.may("general.edit_profile") or config.user.may("general.change_password")):
        html.icon_button("user_profile.py", _("Edit your personal settings, change your password"),
            "sidebar_settings", target="main")
    if config.user.may("general.logout") and not config.auth_by_http_header:
        html.icon_button("logout.py", _("Log out"), "sidebar_logout", target="_top")

    html.icon_button("return void();", _("You have pending messages."),
                     "sidebar_messages", onclick = 'read_message()', id = 'msg_button', style = 'display:none')
    html.open_div(style="display:none;", id_="messages")
    render_messages()
    html.close_div()

    html.open_div(class_=["copyright"])
    html.write("&copy; " + html.render_a("Mathias Kettner", target="_blank", href="https://mathias-kettner.com"))
    html.close_div()
    html.close_div()

    if load_user_config()["fold"]:
        html.final_javascript("fold_sidebar();")

# Standalone sidebar
def page_side():
    if not config.user.may("general.see_sidebar"):
        return
    if config.sidebar_notify_interval is not None:
        interval = config.sidebar_notify_interval
    else:
        interval = 'null'
    html.html_head(_("Check_MK Sidebar"), javascripts=["sidebar"], stylesheets=["sidebar", "status"])
    html.write('<body class="side')
    if config.screenshotmode:
        html.write(" screenshotmode")
    html.write('" onload="initScrollPos(); set_sidebar_size(); init_messages(%s);" '
               'onunload="storeScrollPos()">\n' % interval)
    html.open_div(id_="check_mk_sidebar")

    # FIXME: Move this to the code where views are needed (snapins?)
    views.load_views()
    sidebar_head()
    user_config = load_user_config()
    refresh_snapins = []
    restart_snapins = []

    html.open_div(class_="scroll" if config.sidebar_show_scrollbar else None, id_="side_content")
    for name, state in user_config["snapins"]:
        if not name in sidebar_snapins or not config.user.may("sidesnap." + name):
            continue
        # Performs the initial rendering and might return an optional refresh url,
        # when the snapin contents are refreshed from an external source
        refresh_url = render_snapin(name, state)
        if sidebar_snapins.get(name).get("refresh", False):
            refresh_snapins.append([name, refresh_url])
        elif sidebar_snapins.get(name).get("restart", False):
            refresh_snapins.append([name, refresh_url])
            restart_snapins.append(name)
    html.close_div()
    sidebar_foot()
    html.close_div()

    html.write("<script language=\"javascript\">\n")
    if restart_snapins:
        html.write("sidebar_restart_time = %s\n" % time.time())
    html.write("sidebar_update_interval = %0.2f;\n" % config.sidebar_update_interval)
    html.write("registerEdgeListeners();\n")
    html.write("set_sidebar_size();\n")
    html.write("refresh_snapins = %s;\n" % json.dumps(refresh_snapins))
    html.write("restart_snapins = %s;\n" % json.dumps(restart_snapins))
    html.write("sidebar_scheduler();\n")
    html.write("window.onresize = function() { set_sidebar_size(); };\n")
    html.write("if (contentFrameAccessible()) { update_content_location(); };\n")
    html.write("</script>\n")

    html.body_end()

def render_snapin_styles(snapin):
    styles = snapin.get("styles")
    if styles:
        html.open_style()
        html.write(styles)
        html.close_style()

def render_snapin(name, state):
    snapin = sidebar_snapins.get(name)

    html.open_div(id_="snapin_container_%s" % name, class_="snapin")
    render_snapin_styles(snapin)
    # When not permitted to open/close snapins, the snapins are always opened
    if state == "open" or not config.user.may("general.configure_sidebar"):
        style = None
        headclass = "open"
        minimaxi = "mini"
    else:
        style = "display:none"
        headclass = "closed"
        minimaxi = "maxi"

    toggle_url = "sidebar_openclose.py?name=%s&state=" % name

    # If the user may modify the sidebar then add code for dragging the snapin
    head_actions = {}
    if config.user.may("general.configure_sidebar"):
        head_actions = { "onmouseover" : "document.body.style.cursor='move';",
                         "onmouseout " : "document.body.style.cursor='';",
                         "onmousedown" : "snapinStartDrag(event)",
                         "onmouseup"   : "snapinStopDrag(event)"}

    html.open_div(class_=["head", headclass], **head_actions)

    if config.user.may("general.configure_sidebar"):
        # Icon for mini/maximizing
        html.open_div(class_="minisnapin")
        html.icon_button(url=None, help=_("Toggle this snapin"), icon="%ssnapin" % minimaxi,
                         onclick="toggle_sidebar_snapin(this, '%s')" % toggle_url)
        html.close_div()

        # Button for closing (removing) a snapin
        html.open_div(class_="closesnapin")
        close_url = "sidebar_openclose.py?name=%s&state=off" % name
        html.icon_button(url=None, help=_("Remove this snapin"), icon="closesnapin",
                         onclick="remove_sidebar_snapin(this, '%s')" % close_url)
        html.close_div()

    # The heading. A click on the heading mini/maximizes the snapin
    toggle_actions = {}
    if config.user.may("general.configure_sidebar"):
        toggle_actions = {"onclick"    : "toggle_sidebar_snapin(this,'%s')" % toggle_url,
                          "onmouseover": "this.style.cursor='pointer'",
                          "onmouseout" : "this.style.cursor='auto'"}
    html.b(HTML(snapin["title"]), class_=["heading"], **toggle_actions)

    # End of header
    html.close_div()

    # Now comes the content
    html.open_div(class_="content", id_="snapin_%s" % name, style=style)
    refresh_url = ''
    try:
        url = snapin["render"]()
        # Fetch the contents from an external URL. Don't render it on our own.
        if not url is None:
            refresh_url = url
            html.javascript("get_url(\"%s\", updateContents, \"snapin_%s\")" % (refresh_url, name))
    except Exception, e:
        snapin_exception(e)
    html.close_div()
    html.close_div()
    return refresh_url

def snapin_exception(e):
    html.open_div(class_=["snapinexception"])
    html.h2(_('Error'))
    html.p(e)
    html.close_div()

def ajax_fold():
    config = load_user_config()
    config["fold"] = not not html.var("fold")
    save_user_config(config)


def ajax_openclose():
    config = load_user_config()
    new_snapins = []
    for name, usage in config["snapins"]:
        if html.var("name") == name:
            usage = html.var("state")
        if usage != "off":
            new_snapins.append((name, usage))
    config["snapins"] = new_snapins
    save_user_config(config)

def ajax_snapin():
    # Update online state of the user (if enabled)
    userdb.update_user_access_time(config.user.id)

    snapname = html.var("name")
    if snapname:
        snapnames = [ snapname ]
    else:
        snapnames = html.var('names', '').split(',')

    snapin_code = []
    for snapname in snapnames:
        if not config.user.may("sidesnap." + snapname):
            continue
        snapin = sidebar_snapins.get(snapname)

        # When restart snapins are about to be refreshed, only render
        # them, when the core has been restarted after their initial
        # rendering
        if not snapin.get('refresh') and snapin.get('restart'):
            since = float(html.var('since', 0))
            newest = since
            for site in sites.states().values():
                prog_start = site.get("program_start", 0)
                if prog_start > newest:
                    newest = prog_start
            if newest <= since:
                # no restart
                snapin_code.append('')
                continue

        html.plug()
        try:
            # For testing purposes only: raise Exception("Test")
            snapin["render"]()
        except Exception, e:
            snapin_exception(e)
            e_message = _("Exception during snapin refresh (snapin \'%s\')") % snapname
            logger.error("%s %s: %s" % (html.request_uri(), e_message, traceback.format_exc()))
        finally:
            snapin_code.append(html.drain())
        html.unplug()

    html.write('[%s]' % ','.join([ '"%s"' % s.replace('"', '\\"').replace('\n', '') for s in snapin_code]))


def move_snapin():
    if not config.user.may("general.configure_sidebar"):
        return

    snapname_to_move = html.var("name")
    beforename = html.var("before")

    user_config = load_user_config()

    # Get current state of snaping being moved (open, closed)
    snap_to_move = None
    for name, state in user_config["snapins"]:
        if name == snapname_to_move:
            snap_to_move = name, state
    if not snap_to_move:
        return # snaping being moved not visible. Cannot be.

    # Build new config by removing snaping at current position
    # and add before "beforename" or as last if beforename is not set
    new_snapins = []
    for name, state in user_config["snapins"]:
        if name == snapname_to_move:
            continue # remove at this position
        elif name == beforename:
            new_snapins.append(snap_to_move)
        new_snapins.append( (name, state) )
    if not beforename: # insert as last
        new_snapins.append(snap_to_move)

    user_config["snapins"] = new_snapins
    save_user_config(user_config)

def page_add_snapin():
    if not config.user.may("general.configure_sidebar"):
        raise MKGeneralException(_("You are not allowed to change the sidebar."))

    html.header(_("Available snapins"), stylesheets=["pages", "sidebar", "status"])
    used_snapins = [name for (name, state) in load_user_config()["snapins"]]

    addname = html.var("name")
    if addname in sidebar_snapins and addname not in used_snapins and html.check_transaction():
        user_config = load_user_config()
        user_config["snapins"].append((addname, "open"))
        save_user_config(user_config)
        used_snapins = [name for (name, state) in load_user_config()["snapins"]]
        html.reload_sidebar()

    names = sidebar_snapins.keys()
    names.sort()
    html.open_div(class_=["add_snapin"])
    for name in names:
        if name in used_snapins:
            continue
        if not config.user.may("sidesnap." + name):
            continue # not allowed for this user

        snapin = sidebar_snapins[name]
        title = snapin["title"]
        description = snapin.get("description", "")
        transid = html.get_transid()
        url = 'sidebar_add_snapin.py?name=%s&_transid=%s&pos=top' % (name, transid)
        html.open_div(class_="snapinadder",
                      onmouseover="this.style.cursor=\'pointer\';",
                      onmousedown="window.location.href=\'%s\'; return false;" % url)

        html.open_div(class_=["snapin_preview"])
        html.div('', class_=["clickshield"])
        render_snapin(name, "open")
        html.close_div()
        html.div(description, class_=["description"])
        html.close_div()

    html.close_div()
    html.footer()


def ajax_speedometer():
    try:
        # Try to get values from last call in order to compute
        # driftig speedometer-needle and to reuse the scheduled
        # check reate.
        last_perc          = float(html.var("last_perc"))
        scheduled_rate     = float(html.var("scheduled_rate"))
        last_program_start = int(html.var("program_start"))

        # Get the current rates and the program start time. If there
        # are more than one site, we simply add the start times.
        data = sites.live().query_summed_stats("GET status\n"
               "Columns: service_checks_rate program_start")
        current_rate = data[0]
        program_start = data[1]

        # Recompute the scheduled_rate only if it is not known (first call)
        # or if one of the sites has been restarted. The computed value cannot
        # change during the monitoring since it just reflects the configuration.
        # That way we save CPU resources since the computation of the
        # scheduled checks rate needs to loop over all hosts and services.
        if last_program_start != program_start:
            # These days, we configure the correct check interval for Check_MK checks.
            # We do this correctly for active and for passive ones. So we can simply
            # use the check_interval of all services. Hosts checks are ignored.
            #
            # Manually added services without check_interval could be a problem, but
            # we have no control there.
            scheduled_rate = sites.live().query_summed_stats(
                        "GET services\n"
                        "Stats: suminv check_interval\n")[0] / 60.0

        percentage = 100.0 * current_rate / scheduled_rate;
        title = _("Scheduled service check rate: %.1f/s, current rate: %.1f/s, that is "
                  "%.0f%% of the scheduled rate") % \
                  (scheduled_rate, current_rate, percentage)

    except Exception, e:
        scheduled_rate = 0
        program_start = 0
        percentage = 0
        last_perc = 0
        title = _("No performance data: %s") % e

    html.write(repr([scheduled_rate, program_start, percentage, last_perc, str(title)]))


def ajax_switch_masterstate():
    site = html.var("site")
    column = html.var("switch")
    state = int(html.var("state"))
    commands = {
        ( "enable_notifications",     1) : "ENABLE_NOTIFICATIONS",
        ( "enable_notifications",     0) : "DISABLE_NOTIFICATIONS",
        ( "execute_service_checks",   1) : "START_EXECUTING_SVC_CHECKS",
        ( "execute_service_checks",   0) : "STOP_EXECUTING_SVC_CHECKS",
        ( "execute_host_checks",      1) : "START_EXECUTING_HOST_CHECKS",
        ( "execute_host_checks",      0) : "STOP_EXECUTING_HOST_CHECKS",
        ( "enable_flap_detection",    1) : "ENABLE_FLAP_DETECTION",
        ( "enable_flap_detection",    0) : "DISABLE_FLAP_DETECTION",
        ( "process_performance_data", 1) : "ENABLE_PERFORMANCE_DATA",
        ( "process_performance_data", 0) : "DISABLE_PERFORMANCE_DATA",
        ( "enable_event_handlers",    1) : "ENABLE_EVENT_HANDLERS",
        ( "enable_event_handlers",    0) : "DISABLE_EVENT_HANDLERS",
    }

    command = commands.get((column, state))
    if command:
        sites.live().command("[%d] %s" % (int(time.time()), command), site)
        sites.live().set_only_sites([site])
        sites.live().query("GET status\nWaitTrigger: program\nWaitTimeout: 10000\nWaitCondition: %s = %d\nColumns: %s\n" % \
               (column, state, column))
        sites.live().set_only_sites()
        render_master_control()
    else:
        html.write(_("Command %s/%d not found") % (html.attrencode(column), state))

def ajax_tag_tree():
    new_tree = html.var("conf")

    tree_conf = config.user.load_file("virtual_host_tree", {"tree": 0, "cwd": {}})

    if type(tree_conf) == int:
        tree_conf = {"cwd":{}} # convert from old style

    trees = dict([ (tree["id"], tree) for tree in
                    wato.transform_virtual_host_trees(config.virtual_host_trees) ])

    if new_tree not in trees:
        raise MKUserError("conf", _("This virtual host tree does not exist."))

    tree_conf["tree"] = new_tree
    config.user.save_file("virtual_host_tree", tree_conf)
    html.write("OK")

def ajax_tag_tree_enter():
    path = html.var("path") and html.var("path").split("|") or []
    tree_conf = config.user.load_file("virtual_host_tree", {"tree": 0, "cwd": {}})
    tree_conf["cwd"][tree_conf["tree"]] = path
    config.user.save_file("virtual_host_tree", tree_conf)


def ajax_set_snapin_site():
    ident = html.var("ident")
    if ident not in sidebar_snapins:
        raise MKUserError(None, _("Invalid ident"))

    site  = html.var("site")
    site_choices = dict([ ("", _("All sites")), ] \
                 +  config.get_event_console_site_choices())

    if site not in site_choices:
        raise MKUserError(None, _("Invalid site"))

    sites = config.user.load_file("sidebar_sites", {}, lock=True)
    sites[ident] = site
    config.user.save_file("sidebar_sites", sites, unlock=True)


def ajax_switch_site():
    # _site_switch=sitename1:on,sitename2:off,...
    if not config.user.may("sidesnap.sitestatus"):
        return

    switch_var = html.var("_site_switch")
    if switch_var:
        for info in switch_var.split(","):
            sitename, onoff = info.split(":")
            if sitename not in config.sitenames():
                continue

            d = config.user.siteconf.get(sitename, {})
            d["disabled"] = onoff != "on"
            config.user.siteconf[sitename] = d
        config.user.save_site_config()


#.
#   .--Quicksearch---------------------------------------------------------.
#   |         ___        _      _                            _             |
#   |        / _ \ _   _(_) ___| | _____  ___  __ _ _ __ ___| |__          |
#   |       | | | | | | | |/ __| |/ / __|/ _ \/ _` | '__/ __| '_ \         |
#   |       | |_| | |_| | | (__|   <\__ \  __/ (_| | | | (__| | | |        |
#   |        \__\_\\__,_|_|\___|_|\_\___/\___|\__,_|_|  \___|_| |_|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Handles ajax search reuquests (like issued by the quicksearch dialog |
#   '----------------------------------------------------------------------'


# Ensures the provided search string is a regex, does some basic conversion
# and then tries to verify it is a regex
def to_regex(s):
    s = s.replace('*', '.*')
    try:
        re.compile(s)
    except re.error:
        raise MKGeneralException(_('You search statement is not valid. You need to provide a regular '
            'expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> '
            'if you like to search for a single backslash.'))
    return s


def ajax_search():
    q = html.var_utf8('q').strip()
    if not q:
        return

    try:
        generate_results(q)
    except MKException, e:
        html.show_error(e)
    except Exception, e:
        log_exception()
        if config.debug:
            raise
        import traceback
        html.show_error(traceback.format_exc())


def search_open():
    q = html.var('q').strip()
    if not q:
        return

    url = generate_search_results(q)
    html.http_redirect(url)



class LivestatusSearchBase(object):
    def _build_url(self, url_params, restore_regex = False):
        new_params = []
        if restore_regex:
            for key, value in url_params:
                new_params.append((key, value.replace("\\", "\\\\")))
        else:
            new_params.extend(url_params)
        return html.makeuri(new_params, delvars  = "q", filename = "view.py")


# Handles exactly one livestatus query
class LivestatusSearchConductor(LivestatusSearchBase):
    def __init__(self, used_filters, filter_behaviour):
        # used_filters:     {u'h': [u'heute'], u's': [u'Check_MK']}
        # filter_behaviour: "continue"
        self._used_filters       = used_filters
        self._filter_behaviour   = filter_behaviour

        self._livestatus_command = None # Computed livestatus query
        self._rows               = []   # Raw data from livestatus
        self._elements           = []   # Postprocessed rows


    def get_filter_behaviour(self):
        return self._filter_behaviour


    def do_query(self):
        self._execute_livestatus_command()


    def num_rows(self):
        return len(self._rows)


    def remove_rows_from_end(self, num):
        self._rows = self._rows[:-num]


    def row_limit_exceeded(self):
        return self._too_much_rows


    def get_elements(self):
        return self._elements


    def get_match_topic(self):
        if len(self._used_filters.keys()) > 1:
            return "Multi-Filter"
        shortname = self._used_filters.keys()[0]
        return self._get_plugin_with_shortname(shortname).get_match_topic()


    def _get_plugin_with_shortname(self, shortname):
        for plugin in quicksearch_match_plugins:
            if plugin.get_filter_shortname() == shortname:
                return plugin


    def _execute_livestatus_command(self):
        self._rows = []
        self._too_much_rows = False

        self._generate_livestatus_command()

        if not self._livestatus_command:
            return

        sites.live().set_prepend_site(True)
        results = sites.live().query(self._livestatus_command)
        sites.live().set_prepend_site(False)

        # Invalid livestatus response, missing headers..
        if not results:
            return

        headers =  ["site"] + self._queried_livestatus_columns
        self._rows = map(lambda x: dict(zip(headers, x)), results)


        limit = config.quicksearch_dropdown_limit
        if len(self._rows) > limit:
            self._too_much_rows = True
            self._rows.pop() # Remove limit+1nth element


    def _generate_livestatus_command(self):
        self._determine_livestatus_table()
        columns_to_query           = set(self._get_livestatus_default_columns())
        livestatus_filter_domains  = {} # Filters sorted by domain
        self._used_search_plugins  = [x for x in quicksearch_match_plugins if
                                        x.is_used_for_table(self._livestatus_table, self._used_filters)]

        for plugin in self._used_search_plugins:
            columns_to_query.update(set(plugin.get_livestatus_columns(self._livestatus_table)))
            name = plugin.get_filter_shortname()
            livestatus_filter_domains.setdefault(name, [])
            livestatus_filter_domains[name].append(plugin.get_livestatus_filters(self._livestatus_table,
                                                                                 self._used_filters))

        # Combine filters of same domain (h/s/sg/hg/..)
        livestatus_filters = []
        for entries in livestatus_filter_domains.values():
            livestatus_filters.append("\n".join(entries))
            if len(entries) > 1:
                livestatus_filters[-1] += "\nOr: %d" % len(entries)

        if len(livestatus_filters) > 1:
            livestatus_filters.append("And: %d" % len(livestatus_filters))

        self._queried_livestatus_columns = list(columns_to_query)
        self._livestatus_command         = "GET %s\nColumns: %s\n%s\n" % (self._livestatus_table,
                                              " ".join(self._queried_livestatus_columns),
                                              "\n".join(livestatus_filters))

        # Limit number of results
        limit = config.quicksearch_dropdown_limit
        self._livestatus_command += "Cache: reload\nLimit: %d\nColumnHeaders: off" % (limit + 1)


    # Returns the livestatus table fitting the given filters
    def _determine_livestatus_table(self):
        # Available tables
        # hosts / services / hostgroups / servicegroups

        # {table} -> {is_included_in_table}
        # Hostgroups -> Hosts -> Services
        # Servicegroups -> Services

        preferred_tables = []
        for shortname in self._used_filters.keys():
            plugin = self._get_plugin_with_shortname(shortname)
            preferred_tables.append(plugin.get_preferred_livestatus_table())


        table_to_query = ""
        if "services" in preferred_tables:
            table_to_query = "services"
        elif "servicegroups" in preferred_tables:
            if "hosts" in preferred_tables or "hostgroups" in preferred_tables:
                table_to_query = "services"
            else:
                table_to_query = "servicegroups"
        elif "hosts" in preferred_tables:
            table_to_query = "hosts"
        elif "hostgroups" in preferred_tables:
            table_to_query = "hostgroups"

        self._livestatus_table = table_to_query


    def _get_livestatus_default_columns(self):
        return {
            "services":      ["description", "host_name"],
            "hosts":         ["name"],
            "hostgroups":    ["name"],
            "servicegroups": ["name"],
        } [self._livestatus_table]


    def get_search_url_params(self):
        exact_match = self.num_rows() == 1
        target_view = self._get_target_view(exact_match = exact_match)

        url_params = [("view_name", target_view), ("filled_in", "filter")]
        for plugin in self._used_search_plugins:
            match_info = plugin.get_matches(target_view,
                                            exact_match and self._rows[0] or None,
                                            self._livestatus_table,
                                            self._used_filters,
                                            rows = self._rows)
            if not match_info:
                continue
            text, url_filters = match_info
            url_params.extend(url_filters)

        return url_params


    def create_result_elements(self):
        self._elements = []
        if not self._rows:
            return

        target_view = self._get_target_view()

        # Feed each row to the filters and let them add additional text/url infos
        for row in self._rows:
            entry = {"text_tokens": []}
            url_params = []
            for filter_shortname in self._used_filters:
                plugin = self._get_plugin_with_shortname(filter_shortname)

                match_info = plugin.get_matches(target_view, row, self._livestatus_table, self._used_filters)
                if not match_info:
                    continue
                text, url_filters = match_info
                url_params.extend(url_filters)
                entry["text_tokens"].append((plugin.get_filter_shortname(), text))

            entry["url"]      = self._build_url([("view_name", target_view),
                                                 ("site", row.get("site"))] + url_params, restore_regex = True)

            entry["raw_data"] = row
            self._elements.append(entry)

        self._generate_display_texts()



    def _get_target_view(self, exact_match = True):
        if exact_match:
            if self._livestatus_table == "hosts":
                return "host"
            elif self._livestatus_table == "services":
                return "allservices"
            elif self._livestatus_table == "hostgroups":
                return "hostgroup"
            elif self._livestatus_table == "servicegroups":
                return "servicegroup"
        else:
            if self._livestatus_table == "hosts":
                return "searchhost"
            elif self._livestatus_table == "services":
                return "searchsvc"
            elif self._livestatus_table == "hostgroups":
                return "hostgroups"
            elif self._livestatus_table == "servicegroups":
                return "svcgroups"


    def _generate_display_texts(self):
        for element in self._elements:
            if self._livestatus_table == "services":
                element["display_text"] = element["raw_data"]["description"]
            else:
                element["display_text"] = element["text_tokens"][0][1]


        if self._element_texts_unique():
            return

        # Some (ugly) special handling when the results are not unique
        # Whenever this happens we try to find a fitting second value

        if self._livestatus_table in ["hostgroups", "servicegroups"]:
            # Discard redundant hostgroups
            new_elements = []
            used_groups  = set()
            for element in self._elements:
                if element["display_text"] in used_groups:
                    continue
                new_elements.append(element)
                used_groups.add(element["display_text"])
            self._elements = new_elements
        else:
            # Add additional info to the display text
            for element in self._elements:
                hostname = element["raw_data"].get("host_name", element["raw_data"].get("name"))
                if "&host_regex=" not in element["url"]:
                    element["url"] += "&host_regex=%s" % hostname

                for shortname, text in element["text_tokens"]:
                    if shortname in ["h", "al"] and text not in element["display_text"]:
                        element["display_text"] += " <b>%s</b>" % text
                        break
                else:
                    element["display_text"] += " <b>%s</b>" % hostname


    def _element_texts_unique(self):
        used_texts = set()
        for entry in self._elements:
            if entry["display_text"] in used_texts:
                return False
            used_texts.add(entry["display_text"])
        return True



class LivestatusQuicksearch(LivestatusSearchBase):
    def __init__(self, query):
        self._query = query
        self._search_objects     = []    # Each of these objects do exactly one ls query
        super(LivestatusQuicksearch, self).__init__()


    def generate_dropdown_results(self):
        self._query_data()
        self._evaluate_results()
        self._render_dropdown_elements()


    def generate_search_url(self):
        self._query_data()

        # Generate a search page for the topmost search_object with results
        url_params = []

        restore_regex = False
        for search_object in self._search_objects:
            if search_object.num_rows() > 0:
                url_params.extend(search_object.get_search_url_params())
                if search_object.num_rows() == 1:
                    restore_regex = True
                break
        else:
            url_params.extend([("view_name", "allservices"),
                               ("filled_in", "filter"),
                               ("service_regex", self._query)])

        return self._build_url(url_params, restore_regex = restore_regex)


    def _query_data(self):
        self._determine_search_objects()
        self._conduct_search()


    def _determine_search_objects(self):
        filter_names = set(map(lambda x: "%s" % x.get_filter_shortname(), quicksearch_match_plugins))
        filter_regex = "|".join(filter_names)

        # Goal: "((^| )(hg|h|sg|s|al|tg|ad):)"
        regex = "((^| )(%(filter_regex)s):)" % {"filter_regex": filter_regex}
        found_filters = []
        matches = re.finditer(regex, self._query)
        for match in matches:
            found_filters.append((match.group(1), match.start()))

        if found_filters:
            filter_spec = {}
            current_string = self._query
            for filter_type, offset in found_filters[-1::-1]:
                filter_text = to_regex(current_string[offset+len(filter_type):]).strip()
                filter_name = filter_type.strip().rstrip(":")
                filter_spec.setdefault(filter_name, []).append(filter_text)
                current_string = current_string[:offset]
            self._search_objects.append(LivestatusSearchConductor(filter_spec, "continue"))
        else:
            # No explicit filters set.
            # Use configured quicksearch search order
            for (filter_name, filter_behaviour) in config.quicksearch_search_order:
                self._search_objects.append(LivestatusSearchConductor({filter_name: [to_regex(self._query)]}, filter_behaviour))


    # Collect the raw data from livestatus
    def _conduct_search(self):
        too_much_rows = False
        total_rows = 0
        for idx, search_object in enumerate(self._search_objects):
            search_object.do_query()
            total_rows += search_object.num_rows()

            if total_rows > config.quicksearch_dropdown_limit:
                search_object.remove_rows_from_end(total_rows - config.quicksearch_dropdown_limit)
                too_much_rows = True
                break

            if search_object.row_limit_exceeded():
                too_much_rows = True
                break

            if search_object.num_rows() > 0 and search_object.get_filter_behaviour() != "continue":
                if search_object.get_filter_behaviour() == "finished_distinct":
                    # Discard all data of previous filters and break
                    for i in range(idx-1, -1, -1):
                        self._search_objects[i].remove_rows_from_end(config.quicksearch_dropdown_limit)
                break

        if too_much_rows:
            html.show_warning(_("More than %d results") % config.quicksearch_dropdown_limit)


    # Generates elements out of the raw data
    def _evaluate_results(self):
        for search_object in self._search_objects:
            search_object.create_result_elements()


    # Renders the elements
    def _render_dropdown_elements(self):
        # Show search topic if at least two search objects provide elements
        show_match_topics = len([x for x in self._search_objects if x.num_rows() > 0]) > 1

        for search_object in self._search_objects:
            if not search_object.num_rows():
                continue
            elements = search_object.get_elements()
            elements.sort(key = lambda x: x["display_text"])
            if show_match_topics:
                match_topic = search_object.get_match_topic()
                html.div(_("Results for %s") % match_topic, class_="topic")

            for entry in elements:
                html.a(entry["display_text"], id="result_%s" % self._query, href=entry["url"], target="main")



def generate_results(query):
    quicksearch = LivestatusQuicksearch(query)
    quicksearch.generate_dropdown_results()


def generate_search_results(query):
    quicksearch = LivestatusQuicksearch(query)
    return quicksearch.generate_search_url()

