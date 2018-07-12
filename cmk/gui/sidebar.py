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

import re
import abc
import pprint
import os
import copy
import urlparse
import traceback
import json
import time

import cmk.paths
import cmk.store as store

import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.htmllib import HTML
import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.views as views
import cmk.gui.userdb as userdb
import cmk.gui.pagetypes as pagetypes
import cmk.gui.notify as notify
import cmk.gui.werks as werks
import cmk.gui.sites as sites
import cmk.gui.modules as modules
import cmk.gui.plugin_registry
import cmk.gui.plugins.sidebar
import cmk.gui.plugins.sidebar.quicksearch
from cmk.gui.exceptions import MKGeneralException, MKUserError, MKException
from cmk.gui.log import logger

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.sidebar

if cmk.is_managed_edition():
    import cmk.gui.cme.plugins.sidebar

# Helper functions to be used by snapins
# Kept for compatibility with legacy plugins
# TODO: Drop once we don't support legacy snapins anymore
from cmk.gui.plugins.sidebar.utils import (
    sidebar_snapins,
    snapin_width,
    snapin_site_choice,
    visuals_by_topic,
    render_link,
    heading,
    link,
    simplelink,
    bulletlink,
    iconlink,
    nagioscgilink,
    footnotelinks,
    begin_footnote_links,
    end_footnote_links,
    write_snapin_exception,
)

quicksearch_match_plugins = []
QuicksearchMatchPlugin = cmk.gui.plugins.sidebar.quicksearch.QuicksearchMatchPlugin

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    # Load all snapins
    global search_plugins
    search_plugins = []

    config.declare_permission_section("sidesnap", _("Sidebar snapins"), do_sort = True)

    utils.load_web_plugins("sidebar", globals())

    transform_old_dict_based_snapins()
    transform_old_quicksearch_match_plugins()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()


# Pre Check_MK 1.5 the snapins were declared with dictionaries like this:
#
# sidebar_snapins["about"] = {
#     "title" : _("About Check_MK"),
#     "description" : _("Version information and Links to Documentation, "
#                       "Homepage and Download of Check_MK"),
#     "render" : render_about,
#     "allowed" : [ "admin", "user", "guest" ],
# }
#
# Convert it to objects to be compatible
# TODO: Deprecate this one day.
def transform_old_dict_based_snapins():
    for snapin_id, snapin in sidebar_snapins.items():
        snapin_registry.register(GenericSnapin(snapin_id, snapin))


# TODO: Deprecate this one day.
def transform_old_quicksearch_match_plugins():
    for match_plugin in quicksearch_match_plugins:
        cmk.gui.plugins.sidebar.quicksearch.match_plugin_registry.register(match_plugin)


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
                if entry[0] in snapin_registry
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

    if config.sidebar_show_version_in_sidebar:
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
            html.write_text(msg['text'].replace('\n', '<br>\n'))
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
        if not name in snapin_registry or not config.user.may("sidesnap." + name):
            continue
        # Performs the initial rendering and might return an optional refresh url,
        # when the snapin contents are refreshed from an external source
        refresh_url = render_snapin(name, state)

        if snapin_registry.get(name).refresh_regularly():
            refresh_snapins.append([name, refresh_url])

        elif snapin_registry.get(name).refresh_on_restart():
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
    styles = snapin.styles()
    if styles:
        html.open_style()
        html.write(styles)
        html.close_style()

def render_snapin(name, state):
    snapin = snapin_registry.get(name)

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
    html.b(HTML(snapin.title()), class_=["heading"], **toggle_actions)

    # End of header
    html.close_div()

    # Now comes the content
    html.open_div(class_="content", id_="snapin_%s" % name, style=style)
    refresh_url = ''
    try:
        # TODO: Refactor this confusing special case. Add deddicated method or something
        # to let the snapins make the sidebar know that there is a URL to fetch.
        url = snapin.show()
        if not url is None:
            # Fetch the contents from an external URL. Don't render it on our own.
            refresh_url = url
            html.javascript("get_url(\"%s\", updateContents, \"snapin_%s\")" % (refresh_url, name))
    except Exception, e:
        logger.exception()
        write_snapin_exception(e)
    html.close_div()
    html.close_div()
    return refresh_url


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
        snapin = snapin_registry.get(snapname)

        # When restart snapins are about to be refreshed, only render
        # them, when the core has been restarted after their initial
        # rendering
        if not snapin.refresh_regularly() and snapin.refresh_on_restart():
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

        with html.plugged():
            try:
                snapin.show()
            except Exception, e:
                write_snapin_exception(e)
                e_message = _("Exception during snapin refresh (snapin \'%s\')") % snapname
                logger.error("%s %s: %s" % (html.request.requested_url, e_message, traceback.format_exc()))
            finally:
                snapin_code.append(html.drain())

    # write all snapins
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
    if addname in snapin_registry and addname not in used_snapins and html.check_transaction():
        user_config = load_user_config()
        user_config["snapins"].append((addname, "open"))
        save_user_config(user_config)
        used_snapins = [name for (name, state) in load_user_config()["snapins"]]
        html.reload_sidebar()

    html.open_div(class_=["add_snapin"])
    for name, snapin in sorted(snapin_registry.items()):
        if name in used_snapins:
            continue
        if not config.user.may("sidesnap." + name):
            continue # not allowed for this user

        title = snapin.title()
        description = snapin.description()
        transid = html.transaction_manager.get()
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


def ajax_set_snapin_site():
    ident = html.var("ident")
    if ident not in snapin_registry:
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
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'


class SnapinRegistry(cmk.gui.plugin_registry.Registry):
    """The management object for all available plugins.

    The snapins are loaded by importing cmk.gui.plugins.sidebar. These plugins
    contain subclasses of the cmk.gui.plugins.SidebarSnapin class.
    SnapinRegistry.load_plugins() will register all snapins with this management
    object and make them available for use.
    """
    def plugin_base_class(self):
        return cmk.gui.plugins.sidebar.SidebarSnapin


    def register(self, snapin):
        snapin_id = snapin.type_name()
        self._entries[snapin_id] = snapin

        config.declare_permission("sidesnap.%s" % snapin_id,
            snapin.title(),
            snapin.description(),
            snapin.allowed_roles())

        modules.register_handlers(snapin.page_handlers())


snapin_registry = SnapinRegistry()
snapin_registry.load_plugins()


class GenericSnapin(cmk.gui.plugins.sidebar.SidebarSnapin):
    """Generic wrapper class. Needed for compatiblity with old dict based snapins"""
    def __init__(self, snapin_id, dict_spec):
        super(GenericSnapin, self).__init__()
        self._type_name = snapin_id
        self._spec = dict_spec


    def type_name(self):
        return self._type_name


    def title(self):
        return self._spec["title"]


    def description(self):
        return self._spec.get("description", "")


    def show(self):
        return self._spec["render"]()


    def refresh_regularly(self):
        return self._spec.get("refresh", False)


    def styles(self):
        return self._spec.get("styles")
