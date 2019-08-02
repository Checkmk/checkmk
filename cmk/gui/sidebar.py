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

import copy
import traceback
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union  # pylint: disable=unused-import

import cmk
import cmk.utils.paths

import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.pagetypes as pagetypes
import cmk.gui.notify as notify
import cmk.gui.werks as werks
import cmk.gui.sites as sites
import cmk.gui.pages
import cmk.gui.plugins.sidebar
import cmk.gui.plugins.sidebar.quicksearch
from cmk.gui.valuespec import CascadingDropdown, Dictionary
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.log import logger

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.sidebar

if cmk.is_managed_edition():
    import cmk.gui.cme.plugins.sidebar

# Helper functions to be used by snapins
# Kept for compatibility with legacy plugins
# TODO: Drop once we don't support legacy snapins anymore
from cmk.gui.plugins.sidebar.utils import (  # pylint: disable=unused-import
    snapin_registry, snapin_width, snapin_site_choice, visuals_by_topic, render_link, heading, link,
    simplelink, bulletlink, iconlink, nagioscgilink, footnotelinks, begin_footnote_links,
    end_footnote_links, write_snapin_exception,
)

from cmk.gui.plugins.sidebar.quicksearch import QuicksearchMatchPlugin  # pylint: disable=unused-import

quicksearch_match_plugins = []  # type: List[QuicksearchMatchPlugin]

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False
search_plugins = []  # type: List

# TODO: Kept for pre 1.6 plugin compatibility
sidebar_snapins = {}  # type: Dict[str, Dict]


def load_plugins(force):
    global loaded_with_language, search_plugins
    _register_custom_snapins()

    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    # Load all snapins
    search_plugins = []

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
    # type: () -> None
    for snapin_id, snapin in sidebar_snapins.items():

        @snapin_registry.register
        class LegacySnapin(cmk.gui.plugins.sidebar.SidebarSnapin):
            _type_name = snapin_id
            _spec = snapin

            @classmethod
            def type_name(cls):
                return cls._type_name

            @classmethod
            def title(cls):
                return cls._spec["title"]

            @classmethod
            def description(cls):
                return cls._spec.get("description", "")

            def show(self):
                return self._spec["render"]()

            @classmethod
            def refresh_regularly(cls):
                return cls._spec.get("refresh", False)

            @classmethod
            def refresh_on_restart(cls):
                return cls._spec.get("restart", False)

            @classmethod
            def allowed_roles(cls):
                return cls._spec["allowed"]

            def styles(self):
                return self._spec.get("styles")

        # Help pylint a little bit, it doesn't know that the registry remembers the class above.
        _it_is_really_used = LegacySnapin


# TODO: Deprecate this one day.
def transform_old_quicksearch_match_plugins():
    # type: () -> None
    for match_plugin in quicksearch_match_plugins:
        cmk.gui.plugins.sidebar.quicksearch.match_plugin_registry.register(match_plugin)


class UserSidebarConfig(object):
    """Manages the configuration of the users sidebar"""
    def __init__(self, user, default_config):
        super(UserSidebarConfig, self).__init__()
        self._user = user
        self._default_config = copy.deepcopy(default_config)
        self._config = self._load()

    @property
    def folded(self):
        return self._config["fold"]

    @folded.setter
    def folded(self, value):
        # type: (bool) -> None
        self._config["fold"] = value

    def add_snapin(self, snapin):
        # type: (UserSidebarSnapin) -> None
        self.snapins.append(snapin)

    def move_snapin_before(self, snapin, other):
        # type: (UserSidebarSnapin, Optional[UserSidebarSnapin]) -> None
        """Move the given snapin before the other given snapin.
        The other may be None. In this case the snapin is moved to the end.
        """
        self.snapins.remove(snapin)

        if other in self.snapins:
            other_index = self.snapins.index(other)
            self.snapins.insert(other_index, snapin)
        else:
            self.snapins.append(snapin)

    def remove_snapin(self, snapin):
        # type: (UserSidebarSnapin) -> None
        """Remove the given snapin from the users sidebar"""
        self.snapins.remove(snapin)

    def get_snapin(self, snapin_id):
        # type: (str) -> UserSidebarSnapin
        for snapin in self.snapins:
            if snapin.snapin_type.type_name() == snapin_id:
                return snapin
        raise KeyError("Snapin %r does not exist" % snapin_id)

    @property
    def snapins(self):
        # type: () -> List[UserSidebarSnapin]
        return self._config["snapins"]

    def _initial_config(self):
        # type: () -> Dict[str, Union[bool, List[Dict[str, Any]]]]
        return {
            "snapins": self._transform_legacy_tuples(self._default_config),
            "fold": False,
        }

    def _user_config(self):
        return self._user.load_file("sidebar", deflt=self._initial_config())

    def _load(self):
        """Load current state of user's sidebar

        Convert from old format (just a snapin list) to the new format
        (dictionary) on the fly"""
        user_config = self._user_config()

        user_config = self._transform_legacy_list_config(user_config)
        user_config["snapins"] = self._transform_legacy_tuples(user_config["snapins"])
        user_config["snapins"] = self._transform_legacy_off_state(user_config["snapins"])

        # Remove not existing (e.g. legacy) snapins
        user_config["snapins"] = [
            e for e in user_config["snapins"] if e["snapin_type_id"] in snapin_registry
        ]

        user_config = self._from_config(user_config)

        # Remove entries the user is not allowed for
        user_config["snapins"] = [
            e for e in user_config["snapins"] if config.user.may(e.snapin_type.permission_name())
        ]

        return user_config

    def _transform_legacy_list_config(self, user_config):
        if not isinstance(user_config, list):
            return user_config

        return {
            "snapins": user_config,
            "fold": False,
        }

    def _transform_legacy_off_state(self, snapins):
        return [e for e in snapins if e["visibility"] != "off"]

    def _transform_legacy_tuples(self, snapins):
        # type: (Any) -> List[Dict[str, Any]]
        return [{
            "snapin_type_id": e[0],
            "visibility": e[1]
        } if isinstance(e, tuple) else e for e in snapins]

    def save(self):
        # type: () -> None
        if self._user.may("general.configure_sidebar"):
            self._user.save_file("sidebar", self._to_config())

    def _from_config(self, cfg):
        return {
            "fold": cfg["fold"],
            "snapins": [UserSidebarSnapin.from_config(e) for e in cfg["snapins"]]
        }

    def _to_config(self):
        # type: () -> Dict[str, Any]
        return {
            "fold": self._config["fold"],
            "snapins": [e.to_config() for e in self._config["snapins"]]
        }


class SnapinVisibility(Enum):
    OPEN = "open"
    CLOSED = "closed"


class UserSidebarSnapin(object):
    """An instance of a snapin that is configured in the users sidebar"""
    @staticmethod
    def from_config(cfg):
        # type: (Dict[str, Type[cmk.gui.plugins.sidebar.SidebarSnapin]]) -> UserSidebarSnapin
        """ Construct a UserSidebarSnapin object from the persisted data structure"""
        snapin_class = snapin_registry[cfg["snapin_type_id"]]
        return UserSidebarSnapin(snapin_class, SnapinVisibility(cfg["visibility"]))

    @staticmethod
    def from_snapin_type_id(snapin_type_id):
        # type: (str) -> UserSidebarSnapin
        return UserSidebarSnapin(snapin_registry[snapin_type_id])

    def __init__(self, snapin_type, visibility=SnapinVisibility.OPEN):
        # type: (Type[cmk.gui.plugins.sidebar.SidebarSnapin], SnapinVisibility) -> None
        super(UserSidebarSnapin, self).__init__()
        self.snapin_type = snapin_type
        self.visible = visibility

    def to_config(self):
        # type: () -> Dict[str, Any]
        return {
            "snapin_type_id": self.snapin_type.type_name(),
            "visibility": self.visible.value,
        }

    def __eq__(self, other):
        # type: (Any) -> bool
        if not isinstance(other, UserSidebarSnapin):
            return False

        return self.snapin_type == other.snapin_type and self.visible == other.visible

    def __ne__(self, other):
        # type: (Any) -> bool
        return not self.__eq__(other)


class SidebarRenderer(object):
    def show(self):
        # type: () -> None
        if not config.user.may("general.see_sidebar"):
            return None
        if config.sidebar_notify_interval is not None:
            interval = config.sidebar_notify_interval
        else:
            interval = 'null'
        html.clear_default_javascript()
        html.html_head(_("Check_MK Sidebar"), javascripts=["side"])
        html.write('<body class="side')
        if config.screenshotmode:
            html.write(" screenshotmode")
        html.write(
            '" onload="cmk.sidebar.initialize_scroll_position(); cmk.sidebar.set_sidebar_size(); cmk.sidebar.init_messages(%s);" '
            'onunload="cmk.sidebar.store_scroll_position()">\n' % interval)
        html.open_div(id_="check_mk_sidebar")

        self._sidebar_head()
        user_config = UserSidebarConfig(config.user, config.sidebar)
        refresh_snapins = []
        restart_snapins = []

        html.open_div(class_="scroll" if config.sidebar_show_scrollbar else None,
                      id_="side_content")
        for snapin in user_config.snapins:
            name = snapin.snapin_type.type_name()

            # Performs the initial rendering and might return an optional refresh url,
            # when the snapin contents are refreshed from an external source
            refresh_url = self.render_snapin(snapin)

            if snapin.snapin_type.refresh_regularly():
                refresh_snapins.append([name, refresh_url])

            elif snapin.snapin_type.refresh_on_restart():
                refresh_snapins.append([name, refresh_url])
                restart_snapins.append(name)

        html.close_div()
        self._sidebar_foot(user_config)
        html.close_div()

        html.write("<script language=\"javascript\">\n")
        if restart_snapins:
            html.write("cmk.sidebar.set_sidebar_restart_time(%s);\n" % time.time())
        html.write("cmk.sidebar.set_sidebar_update_interval(%0.2f);\n" %
                   config.sidebar_update_interval)
        html.write("cmk.sidebar.register_edge_listeners();\n")
        html.write("cmk.sidebar.set_sidebar_size();\n")
        html.write("cmk.sidebar.set_refresh_snapins(%s);\n" % json.dumps(refresh_snapins))
        html.write("cmk.sidebar.set_restart_snapins(%s);\n" % json.dumps(restart_snapins))
        html.write("cmk.sidebar.execute_sidebar_scheduler();\n")
        html.write("cmk.sidebar.register_event_handlers();\n")
        html.write("window.onresize = function() { cmk.sidebar.set_sidebar_size(); };\n")
        html.write(
            "if (cmk.sidebar.is_content_frame_accessible()) { cmk.sidebar.update_content_location(); };\n"
        )
        html.write("</script>\n")

        html.body_end()

    def render_snapin(self, snapin):
        # type: (UserSidebarSnapin) -> str
        snapin_class = snapin.snapin_type
        name = snapin_class.type_name()
        snapin_instance = snapin_class()

        html.open_div(id_="snapin_container_%s" % name, class_="snapin")
        self._render_snapin_styles(snapin_instance)
        # When not permitted to open/close snapins, the snapins are always opened
        if snapin.visible == SnapinVisibility.OPEN or not config.user.may(
                "general.configure_sidebar"):
            style = None
        else:
            style = "display:none"

        toggle_url = "sidebar_openclose.py?name=%s&state=" % name

        # If the user may modify the sidebar then add code for dragging the snapin
        head_actions = {}  # type: Dict[str, str]
        if config.user.may("general.configure_sidebar"):
            head_actions = {
                "onmouseover": "document.body.style.cursor='move';",
                "onmouseout ": "document.body.style.cursor='';",
                "onmousedown": "cmk.sidebar.snapin_start_drag(event)",
                "onmouseup": "cmk.sidebar.snapin_stop_drag(event)"
            }

        html.open_div(class_=["head", snapin.visible.value], **head_actions)

        if config.user.may("general.configure_sidebar"):
            # Icon for mini/maximizing
            html.div("",
                     class_="minisnapin",
                     title=_("Toggle this snapin"),
                     onclick="cmk.sidebar.toggle_sidebar_snapin(this, '%s')" % toggle_url)

            # Button for closing (removing) a snapin
            html.open_div(class_="closesnapin")
            close_url = "sidebar_openclose.py?name=%s&state=off" % name
            html.icon_button(url=None,
                             title=_("Remove this snapin"),
                             icon="closesnapin",
                             onclick="cmk.sidebar.remove_sidebar_snapin(this, '%s')" % close_url)
            html.close_div()

        # The heading. A click on the heading mini/maximizes the snapin
        toggle_actions = {}  # type: Dict[str, str]
        if config.user.may("general.configure_sidebar"):
            toggle_actions = {
                "onclick": "cmk.sidebar.toggle_sidebar_snapin(this,'%s')" % toggle_url,
                "onmouseover": "this.style.cursor='pointer'",
                "onmouseout": "this.style.cursor='auto'"
            }
        html.b(HTML(snapin_class.title()), class_=["heading"], **toggle_actions)

        # End of header
        html.close_div()

        # Now comes the content
        html.open_div(class_="content", id_="snapin_%s" % name, style=style)
        refresh_url = ''
        try:
            # TODO: Refactor this confusing special case. Add deddicated method or something
            # to let the snapins make the sidebar know that there is a URL to fetch.
            url = snapin_instance.show()
            if not url is None:
                # Fetch the contents from an external URL. Don't render it on our own.
                refresh_url = url
                html.javascript(
                    "cmk.ajax.get_url(\"%s\", cmk.utils.update_contents, \"snapin_%s\")" %
                    (refresh_url, name))
        except Exception as e:
            logger.exception("error rendering snapin %s" % name)
            write_snapin_exception(e)
        html.close_div()
        html.close_div()
        return refresh_url

    def _render_snapin_styles(self, snapin_instance):
        # type: (cmk.gui.plugins.sidebar.SidebarSnapin) -> None
        styles = snapin_instance.styles()
        if styles:
            html.open_style()
            html.write(styles)
            html.close_style()

    def _sidebar_head(self):
        html.open_div(id_="side_header")
        html.div('', id_="side_fold")
        html.open_a(href=config.user.get_attribute("start_url") or config.start_url,
                    target="main",
                    title=_("Go to main overview"))
        html.div("", id_="side_bg")

        if config.sidebar_show_version_in_sidebar:
            html.open_div(id_="side_version")
            html.open_a(href="version.py", target="main", title=_("Open release notes"))
            html.write(self._get_check_mk_edition_title())
            html.br()
            html.write(cmk.__version__)

            if werks.may_acknowledge():
                num_unacknowledged_werks = werks.num_unacknowledged_incompatible_werks()
                if num_unacknowledged_werks:
                    html.span(num_unacknowledged_werks,
                              class_="unack_werks",
                              title=_("%d unacknowledged incompatible werks") %
                              num_unacknowledged_werks)

        html.close_a()
        html.close_div()
        html.close_a()
        html.close_div()

    def _get_check_mk_edition_title(self):
        if cmk.is_enterprise_edition():
            if cmk.is_demo():
                return "Enterprise (Demo)"
            return "Enterprise"

        elif cmk.is_managed_edition():
            return "Managed"

        return "Raw"

    def _sidebar_foot(self, user_config):
        html.open_div(id_="side_footer")
        if config.user.may("general.configure_sidebar"):
            html.icon_button("sidebar_add_snapin.py",
                             _("Add snapin to the sidebar"),
                             "sidebar_addsnapin",
                             target="main")
        # editing the profile is not possible on remote sites which are sync targets
        # of a central WATO system
        if config.wato_enabled and \
           (config.user.may("general.edit_profile") or config.user.may("general.change_password")):
            html.icon_button("user_profile.py",
                             _("Edit your personal settings, change your password"),
                             "sidebar_settings",
                             target="main")
        if config.user.may("general.logout") and not config.auth_by_http_header:
            html.icon_button("logout.py", _("Log out"), "sidebar_logout", target="_top")

        html.icon_button("return void();",
                         _("You have pending messages."),
                         "sidebar_messages",
                         onclick='cmk.sidebar.read_message()',
                         id_='msg_button',
                         style='display:none')
        html.open_div(style="display:none;", id_="messages")
        self.render_messages()
        html.close_div()

        html.open_div(class_=["copyright"])
        html.write("&copy; " +
                   html.render_a("tribe29 GmbH", target="_blank", href="https://checkmk.com"))
        html.close_div()
        html.close_div()

        if user_config.folded:
            html.final_javascript("cmk.sidebar.fold_sidebar();")

    def render_messages(self):
        for msg in notify.get_gui_messages():
            if 'gui_hint' in msg['methods']:
                html.open_div(id_="message-%s" % msg['id'], class_=["popup_msg"])
                html.a("x",
                       href="javascript:void(0)",
                       class_=["close"],
                       onclick="cmk.sidebar.message_close(\'%s\')" % msg['id'])
                html.write_text(msg['text'].replace('\n', '<br>\n'))
                html.close_div()
            if 'gui_popup' in msg['methods']:
                html.javascript('alert(\'%s\'); cmk.sidebar.mark_message_read("%s")' %
                                (html.attrencode(msg['text']).replace('\n', '\\n'), msg['id']))


@cmk.gui.pages.register("side")
def page_side():
    SidebarRenderer().show()


@cmk.gui.pages.register("sidebar_snapin")
def ajax_snapin():
    """Renders and returns the contents of the requested sidebar snapin(s) in JSON format"""
    html.set_output_format("json")
    # Update online state of the user (if enabled)
    userdb.update_user_access_time(config.user.id)

    user_config = UserSidebarConfig(config.user, config.sidebar)

    snapin_id = html.request.var("name")
    snapin_ids = [snapin_id] if snapin_id else html.request.var("names", "").split(",")

    snapin_code = []
    for snapin_id in snapin_ids:
        snapin_instance = user_config.get_snapin(snapin_id).snapin_type()
        if not config.user.may(snapin_instance.permission_name()):
            continue

        # When restart snapins are about to be refreshed, only render
        # them, when the core has been restarted after their initial
        # rendering
        if not snapin_instance.refresh_regularly() and snapin_instance.refresh_on_restart():
            since = float(html.request.var('since', 0))
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
                snapin_instance.show()
            except Exception as e:
                write_snapin_exception(e)
                e_message = _("Exception during snapin refresh (snapin \'%s\')"
                             ) % snapin_instance.type_name()
                logger.error("%s %s: %s" %
                             (html.request.requested_url, e_message, traceback.format_exc()))
            finally:
                snapin_code.append(html.drain())

    html.write(json.dumps(snapin_code))


@cmk.gui.pages.register("sidebar_fold")
def ajax_fold():
    html.set_output_format("json")
    user_config = UserSidebarConfig(config.user, config.sidebar)
    user_config.folded = html.request.var("fold") == "yes"
    user_config.save()


@cmk.gui.pages.register("sidebar_openclose")
def ajax_openclose():
    # type: () -> None
    html.set_output_format("json")
    if not config.user.may("general.configure_sidebar"):
        return None

    snapin_id = html.request.var("name")
    state = html.request.var("state")
    if state not in [SnapinVisibility.OPEN.value, SnapinVisibility.CLOSED.value, "off"]:
        raise MKUserError("state", "Invalid state: %s" % state)

    user_config = UserSidebarConfig(config.user, config.sidebar)

    try:
        snapin = user_config.get_snapin(snapin_id)
    except KeyError:
        return None

    if state == "off":
        user_config.remove_snapin(snapin)
    else:
        snapin.visible = SnapinVisibility(state)

    user_config.save()


@cmk.gui.pages.register("sidebar_move_snapin")
def move_snapin():
    # type: () -> None
    html.set_output_format("json")
    if not config.user.may("general.configure_sidebar"):
        return None

    snapin_id = html.request.var("name")
    before_id = html.request.var("before")

    user_config = UserSidebarConfig(config.user, config.sidebar)

    try:
        snapin = user_config.get_snapin(snapin_id)
    except KeyError:
        return None

    try:
        before_snapin = user_config.get_snapin(before_id)  # type: Optional[UserSidebarSnapin]
    except KeyError:
        before_snapin = None

    user_config.move_snapin_before(snapin, before_snapin)
    user_config.save()


@cmk.gui.pages.register("sidebar_get_messages")
def ajax_get_messages():
    SidebarRenderer().render_messages()


@cmk.gui.pages.register("sidebar_message_read")
def ajax_message_read():
    html.set_output_format("json")
    try:
        notify.delete_gui_message(html.request.var('id'))
        html.write("OK")
    except Exception:
        if config.debug:
            raise
        html.write("ERROR")


#.
#   .--Custom-Snapins------------------------------------------------------.
#   |       ____          _     ____                    _                  |
#   |      / ___|   _ ___| |_  / ___| _ __   __ _ _ __ (_)_ __  ___        |
#   |     | |  | | | / __| __| \___ \| '_ \ / _` | '_ \| | '_ \/ __|       |
#   |     | |__| |_| \__ \ |_ _ ___) | | | | (_| | |_) | | | | \__ \       |
#   |      \____\__,_|___/\__(_)____/|_| |_|\__,_| .__/|_|_| |_|___/       |
#   |                                            |_|                       |
#   '----------------------------------------------------------------------'


class CustomSnapins(pagetypes.Overridable):
    @classmethod
    def type_name(cls):
        return "custom_snapin"

    @classmethod
    def phrase(cls, phrase):
        return {
            "title": _("Custom snapin"),
            "title_plural": _("Custom snapins"),
            #"add_to"         : _("Add to custom snapin list"),
            "clone": _("Clone snapin"),
            "create": _("Create snapin"),
            "edit": _("Edit snapin"),
            "new": _("New snapin"),
        }.get(phrase, pagetypes.Base.phrase(phrase))

    @classmethod
    def parameters(cls, mode):
        parameters = super(CustomSnapins, cls).parameters(mode)

        parameters += [(
            cls.phrase("title"),
            # sort-index, key, valuespec
            [(2.5, "custom_snapin",
              CascadingDropdown(
                  title=_("Snapin type"),
                  choices=cls._customizable_snapin_type_choices,
              ))])]

        return parameters

    @classmethod
    def _customizable_snapin_type_choices(cls):
        choices = []
        for snapin_type_id, snapin_type in sorted(snapin_registry.get_customizable_snapin_types()):
            choices.append((snapin_type_id, snapin_type.title(),
                            Dictionary(
                                title=_("Parameters"),
                                elements=snapin_type.vs_parameters(),
                                optional_keys=[],
                            )))
        return choices


pagetypes.declare(CustomSnapins)


def _register_custom_snapins():
    """First remove all previously registered custom snapins, then register
    the currently configured ones"""
    CustomSnapins.load()
    snapin_registry.register_custom_snapins(CustomSnapins.instances_sorted())


#.
#   .--Add Snapin----------------------------------------------------------.
#   |           _       _     _   ____                    _                |
#   |          / \   __| | __| | / ___| _ __   __ _ _ __ (_)_ __           |
#   |         / _ \ / _` |/ _` | \___ \| '_ \ / _` | '_ \| | '_ \          |
#   |        / ___ \ (_| | (_| |  ___) | | | | (_| | |_) | | | | |         |
#   |       /_/   \_\__,_|\__,_| |____/|_| |_|\__,_| .__/|_|_| |_|         |
#   |                                              |_|                     |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("sidebar_add_snapin")
def page_add_snapin():
    PageAddSnapin(config.user, config.sidebar).show()


class PageAddSnapin(object):
    def __init__(self, user, default_config):
        super(PageAddSnapin, self).__init__()
        self._user_config = UserSidebarConfig(user, default_config)

    def show(self):
        # type: () -> None
        if not config.user.may("general.configure_sidebar"):
            raise MKGeneralException(_("You are not allowed to change the sidebar."))

        html.header(_("Available snapins"))

        html.begin_context_buttons()
        CustomSnapins.context_button_list()
        html.end_context_buttons()

        addname = html.request.var("name")
        if addname in snapin_registry and addname not in self._used_snapins(
        ) and html.check_transaction():
            self._user_config.add_snapin(UserSidebarSnapin.from_snapin_type_id(addname))
            self._user_config.save()
            html.reload_sidebar()

        self._show_builtin_snapins()

    def _show_builtin_snapins(self):
        # type: () -> None
        used_snapins = self._used_snapins()

        html.open_div(class_=["add_snapin"])
        for name, snapin_class in sorted(snapin_registry.items()):
            if name in used_snapins:
                continue
            if not config.user.may(snapin_class.permission_name()):
                continue  # not allowed for this user

            transid = html.transaction_manager.get()
            url = 'sidebar_add_snapin.py?name=%s&_transid=%s&pos=top' % (name, transid)
            html.open_div(class_="snapinadder",
                          onmouseover="this.style.cursor=\'pointer\';",
                          onmousedown="window.location.href=\'%s\'; return false;" % url)

            html.open_div(class_=["snapin_preview"])
            html.div('', class_=["clickshield"])
            SidebarRenderer().render_snapin(UserSidebarSnapin.from_snapin_type_id(name))
            html.close_div()
            html.div(snapin_class.description(), class_=["description"])
            html.close_div()

        html.close_div()
        html.footer()

    def _used_snapins(self):
        # type: () -> List[Any]
        return [snapin.snapin_type.type_name() for snapin in self._user_config.snapins]


# TODO: This is snapin specific. Move this handler to the snapin file
@cmk.gui.pages.register("sidebar_ajax_set_snapin_site")
def ajax_set_snapin_site():
    html.set_output_format("json")
    ident = html.request.var("ident")
    if ident not in snapin_registry:
        raise MKUserError(None, _("Invalid ident"))

    site = html.request.var("site")
    site_choices = dict([ ("", _("All sites")), ] \
                 +  config.site_choices())

    if site not in site_choices:
        raise MKUserError(None, _("Invalid site"))

    snapin_sites = config.user.load_file("sidebar_sites", {}, lock=True)
    snapin_sites[ident] = site
    config.user.save_file("sidebar_sites", snapin_sites, unlock=True)
