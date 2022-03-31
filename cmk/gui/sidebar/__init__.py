#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Status sidebar rendering"""

import copy
import json
import textwrap
import traceback
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING, Union

from livestatus import SiteId

import cmk.utils.paths

import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.pagetypes as pagetypes
import cmk.gui.sites as sites
import cmk.gui.utils as utils
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.config import register_post_config_load_hook
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.globals import config, html, output_funnel, request, response, theme
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import PageMenu, PageMenuDropdown, PageMenuTopic
from cmk.gui.utils.logged_in import LoggedInUser, user
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import CascadingDropdown, Dictionary
from cmk.gui.werks import may_acknowledge

if TYPE_CHECKING:
    from cmk.gui.utils.html import HTML

# Kept for compatibility with legacy plugins
# TODO: Drop once we don't support legacy snapins anymore
from cmk.gui.plugins.sidebar.utils import (  # noqa: F401 # pylint: disable=unused-import
    begin_footnote_links,
    bulletlink,
    end_footnote_links,
    footnotelinks,
    heading,
    iconlink,
    link,
    render_link,
    SidebarSnapin,
    snapin_registry,
    snapin_site_choice,
    snapin_width,
    write_snapin_exception,
)

from .main_menu import MainMenuRenderer

# TODO: Kept for pre 1.6 plugin compatibility
sidebar_snapins: Dict[str, Dict] = {}


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("sidebar", globals())
    transform_old_dict_based_snapins()


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.
    """
    # Needs to be a local import to not influence the regular plugin loading order
    import cmk.gui.plugins.sidebar as api_module
    import cmk.gui.plugins.sidebar.utils as plugin_utils

    for name in (
        "begin_footnote_links",
        "bulletlink",
        "CustomizableSidebarSnapin",
        "end_footnote_links",
        "footnotelinks",
        "heading",
        "iconlink",
        "link",
        "make_topic_menu",
        "PageHandlers",
        "render_link",
        "show_topic_menu",
        "SidebarSnapin",
        "snapin_registry",
        "snapin_site_choice",
        "snapin_width",
        "write_snapin_exception",
    ):
        api_module.__dict__[name] = plugin_utils.__dict__[name]


# Pre Checkmk 1.5 the snapins were declared with dictionaries like this:
#
# sidebar_snapins["about"] = {
#     "title" : _("About Checkmk"),
#     "description" : _("Version information and Links to Documentation, "
#                       "Homepage and Download of Checkmk"),
#     "render" : render_about,
#     "allowed" : [ "admin", "user", "guest" ],
# }
#
# Convert it to objects to be compatible
# TODO: Deprecate this one day.
def transform_old_dict_based_snapins() -> None:
    for snapin_id, snapin in sidebar_snapins.items():

        @snapin_registry.register
        class LegacySnapin(SidebarSnapin):
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
        _it_is_really_used = LegacySnapin  # noqa: F841


class UserSidebarConfig:
    """Manages the configuration of the users sidebar"""

    def __init__(self, usr: LoggedInUser, default_config: List[Tuple[str, str]]) -> None:
        super().__init__()
        self._user = usr
        self._default_config = copy.deepcopy(default_config)
        self._config = self._load()

    @property
    def folded(self) -> bool:
        return self._config["fold"]

    @folded.setter
    def folded(self, value: bool) -> None:
        self._config["fold"] = value

    def add_snapin(self, snapin: "UserSidebarSnapin") -> None:
        self.snapins.append(snapin)

    def move_snapin_before(
        self, snapin: "UserSidebarSnapin", other: "Optional[UserSidebarSnapin]"
    ) -> None:
        """Move the given snapin before the other given snapin.
        The other may be None. In this case the snapin is moved to the end.
        """
        self.snapins.remove(snapin)

        if other in self.snapins:
            other_index = self.snapins.index(other)
            self.snapins.insert(other_index, snapin)
        else:
            self.snapins.append(snapin)

    def remove_snapin(self, snapin: "UserSidebarSnapin") -> None:
        """Remove the given snapin from the users sidebar"""
        self.snapins.remove(snapin)

    def get_snapin(self, snapin_id: str) -> "UserSidebarSnapin":
        for snapin in self.snapins:
            if snapin.snapin_type.type_name() == snapin_id:
                return snapin
        raise KeyError("Snapin %r does not exist" % snapin_id)

    @property
    def snapins(self) -> "List[UserSidebarSnapin]":
        return self._config["snapins"]

    def _initial_config(self) -> Dict[str, Union[bool, List[Dict[str, Any]]]]:
        return {
            "snapins": self._transform_legacy_tuples(self._default_config),
            "fold": False,
        }

    def _user_config(self) -> Dict[str, Any]:
        return self._user.get_sidebar_configuration(self._initial_config())

    def _load(self) -> Dict[str, Any]:
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
        user_config["snapins"] = [e for e in user_config["snapins"] if e.snapin_type.may_see()]

        return user_config

    def _transform_legacy_list_config(self, user_config: Any) -> Dict[str, Any]:
        if not isinstance(user_config, list):
            return user_config

        return {
            "snapins": user_config,
            "fold": False,
        }

    def _transform_legacy_off_state(self, snapins: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return [e for e in snapins if e["visibility"] != "off"]

    def _transform_legacy_tuples(self, snapins: Any) -> List[Dict[str, Any]]:
        return [
            {"snapin_type_id": e[0], "visibility": e[1]} if isinstance(e, tuple) else e
            for e in snapins
        ]

    def save(self) -> None:
        if self._user.may("general.configure_sidebar"):
            self._user.set_sidebar_configuration(self._to_config())

    def _from_config(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "fold": cfg["fold"],
            "snapins": [UserSidebarSnapin.from_config(e) for e in cfg["snapins"]],
        }

    def _to_config(self) -> Dict[str, Any]:
        return {
            "fold": self._config["fold"],
            "snapins": [e.to_config() for e in self._config["snapins"]],
        }


class SnapinVisibility(Enum):
    OPEN = "open"
    CLOSED = "closed"


class UserSidebarSnapin:
    """An instance of a snapin that is configured in the users sidebar"""

    @staticmethod
    def from_config(cfg: Dict[str, Any]) -> "UserSidebarSnapin":
        """Construct a UserSidebarSnapin object from the persisted data structure"""
        snapin_class = snapin_registry[cfg["snapin_type_id"]]
        return UserSidebarSnapin(snapin_class, SnapinVisibility(cfg["visibility"]))

    @staticmethod
    def from_snapin_type_id(snapin_type_id: str) -> "UserSidebarSnapin":
        return UserSidebarSnapin(snapin_registry[snapin_type_id])

    def __init__(
        self,
        snapin_type: Type[SidebarSnapin],
        visibility: SnapinVisibility = SnapinVisibility.OPEN,
    ) -> None:
        super().__init__()
        self.snapin_type = snapin_type
        self.visible = visibility

    def to_config(self) -> Dict[str, Any]:
        return {
            "snapin_type_id": self.snapin_type.type_name(),
            "visibility": self.visible.value,
        }

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, UserSidebarSnapin):
            return False

        return self.snapin_type == other.snapin_type and self.visible == other.visible

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)


class SidebarRenderer:
    def show(self, title: Optional[str] = None, content: Optional["HTML"] = None) -> None:
        # TODO: Right now the method renders the full HTML page, i.e.
        # the header, sidebar, and page content. Ideallly we should
        # split this up. Possible solutions might be:
        #
        #     1. If we remove the page side.py the code for the header
        #        and the page content can be moved to the page index.py.
        #     2. Alternatively, we could extract a helper function that
        #        provides the header and body (without content). Then
        #        helper could then be used by index.py and side.py.
        #
        # In both cases this method would only render the sidebar
        # content afterwards.

        html.clear_default_javascript()
        html.html_head(title or _("Checkmk Sidebar"), javascripts=["side"])

        self._show_body_start()
        self._show_sidebar()
        self._show_page_content(content)

        html.body_end()

    def _show_body_start(self) -> None:
        body_classes = ["side", "screenshotmode" if config.screenshotmode else None]

        if not user.may("general.see_sidebar"):
            html.open_body(class_=body_classes, data_theme=theme.get())
            return

        interval = (
            config.sidebar_notify_interval if config.sidebar_notify_interval is not None else "null"
        )
        html.open_body(
            class_=body_classes,
            onload="cmk.sidebar.initialize_scroll_position(); cmk.sidebar.init_messages_and_werks(%s, %s); "
            % (json.dumps(interval), json.dumps(bool(may_acknowledge()))),
            data_theme=theme.get(),
        )

    def _show_sidebar(self) -> None:
        if not user.may("general.see_sidebar"):
            html.div("", id_="check_mk_navigation")
            return

        user_config = UserSidebarConfig(user, config.sidebar)

        html.open_div(
            id_="check_mk_navigation",
            class_="min" if user.get_attribute("nav_hide_icons_title") else None,
        )
        self._show_sidebar_head()
        html.close_div()

        assert user.id is not None
        sidebar_position = cmk.gui.userdb.load_custom_attr(
            user.id, "ui_sidebar_position", lambda x: None if x == "None" else "left"
        )
        html.open_div(id_="check_mk_sidebar", class_=[sidebar_position])

        self._show_snapin_bar(user_config)

        html.close_div()

        if user_config.folded:
            html.final_javascript("cmk.sidebar.fold_sidebar();")

    def _show_snapin_bar(self, user_config: UserSidebarConfig) -> None:
        html.open_div(
            class_="scroll" if config.sidebar_show_scrollbar else None, id_="side_content"
        )

        refresh_snapins, restart_snapins, static_snapins = self._show_snapins(user_config)
        self._show_add_snapin_button()

        html.close_div()

        html.javascript(
            "cmk.sidebar.initialize_sidebar(%0.2f, %s, %s, %s);\n"
            % (
                config.sidebar_update_interval,
                json.dumps(refresh_snapins),
                json.dumps(restart_snapins),
                json.dumps(static_snapins),
            )
        )

    def _show_snapins(self, user_config: UserSidebarConfig) -> Tuple[List, List, List]:
        refresh_snapins = []
        restart_snapins = []
        static_snapins = []

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
            else:
                static_snapins.append(name)

        return refresh_snapins, restart_snapins, static_snapins

    def _show_add_snapin_button(self) -> None:
        html.open_div(id_="add_snapin")
        html.open_a(
            href=makeuri_contextless(request, [], filename="sidebar_add_snapin.py"), target="main"
        )
        html.icon("add", title=_("Add elements to your sidebar"))
        html.close_a()
        html.close_div()

    def render_snapin(self, snapin: UserSidebarSnapin) -> str:
        snapin_class = snapin.snapin_type
        name = snapin_class.type_name()
        snapin_instance = snapin_class()

        more_id = "sidebar_snapin_%s" % name

        show_more = user.get_show_more_setting(more_id)
        html.open_div(
            id_="snapin_container_%s" % name, class_=["snapin", ("more" if show_more else "less")]
        )

        self._render_snapin_styles(snapin_instance)
        # When not permitted to open/close snapins, the snapins are always opened
        if snapin.visible == SnapinVisibility.OPEN or not user.may("general.configure_sidebar"):
            style = None
        else:
            style = "display:none"

        toggle_url = "sidebar_openclose.py?name=%s&state=" % name

        # If the user may modify the sidebar then add code for dragging the snapin
        head_actions: Dict[str, str] = {}
        if user.may("general.configure_sidebar"):
            head_actions = {
                "onmouseover": "document.body.style.cursor='move';",
                "onmouseout ": "document.body.style.cursor='';",
                "onmousedown": "cmk.sidebar.snapin_start_drag(event)",
                "onmouseup": "cmk.sidebar.snapin_stop_drag(event)",
            }

        html.open_div(class_=["head", snapin.visible.value], **head_actions)

        show_more = snapin_instance.has_show_more_items()
        may_configure = user.may("general.configure_sidebar")

        if show_more or may_configure:

            html.open_div(class_="snapin_buttons")

            if show_more:
                html.open_span(class_="moresnapin")
                html.more_button(more_id, dom_levels_up=4)
                html.close_span()

            if may_configure:
                # Button for closing (removing) a snapin
                html.open_span(class_="closesnapin")
                close_url = "sidebar_openclose.py?name=%s&state=off" % name
                html.icon_button(
                    url=None,
                    title=_("Remove this element"),
                    icon="close",
                    onclick="cmk.sidebar.remove_sidebar_snapin(this, '%s')" % close_url,
                )
                html.close_span()

            html.close_div()

        # The heading. A click on the heading mini/maximizes the snapin
        toggle_actions: Dict[str, str] = {}
        if user.may("general.configure_sidebar"):
            toggle_actions = {
                "onclick": "cmk.sidebar.toggle_sidebar_snapin(this,'%s')" % toggle_url,
                "onmouseover": "this.style.cursor='pointer'",
                "onmouseout": "this.style.cursor='auto'",
            }
        html.b(
            textwrap.shorten(snapin_class.title(), width=27, placeholder="..."),
            class_=["heading"],
            **toggle_actions,
        )

        if may_configure:
            # Icon for mini/maximizing
            html.span(
                "",
                class_="minisnapin",
                title=_("Open/close this element"),
                onclick="cmk.sidebar.toggle_sidebar_snapin(this, '%s')" % toggle_url,
            )

        # End of header
        html.close_div()

        # Now comes the content
        html.open_div(class_="content", id_="snapin_%s" % name, style=style)
        refresh_url = ""
        try:
            # TODO: Refactor this confusing special case. Add deddicated method or something
            # to let the snapins make the sidebar know that there is a URL to fetch.
            url = snapin_instance.show()
            if url is not None:
                # Fetch the contents from an external URL. Don't render it on our own.
                refresh_url = url
                html.javascript(
                    'cmk.ajax.get_url("%s", cmk.utils.update_contents, "snapin_%s")'
                    % (refresh_url, name)
                )
        except Exception as e:
            logger.exception("error rendering snapin %s", name)
            write_snapin_exception(e)
        html.close_div()
        html.close_div()
        return refresh_url

    def _render_snapin_styles(self, snapin_instance: SidebarSnapin) -> None:
        styles = snapin_instance.styles()
        if styles:
            html.open_style()
            html.write_text(styles)
            html.close_style()

    def _show_page_content(self, content: Optional["HTML"]):
        html.open_div(id_="content_area")
        if content is not None:
            html.write_html(content)
        html.close_div()

    def _show_sidebar_head(self):
        html.open_div(id_="side_header")
        html.open_a(
            href=user.start_url or config.start_url,
            target="main",
            title=_("Go to main page"),
        )
        _render_header_icon()
        html.close_a()
        html.close_div()

        MainMenuRenderer().show()

        html.open_div(
            id_="side_fold", title=_("Toggle the sidebar"), onclick="cmk.sidebar.toggle_sidebar()"
        )
        html.icon("sidebar_folded", class_="folded")
        html.icon("sidebar")
        if not user.get_attribute("nav_hide_icons_title"):
            html.div(_("Sidebar"))
        html.close_div()


def _render_header_icon() -> None:
    if user.get_attribute("nav_hide_icons_title"):
        if theme.has_custom_logo():
            html.img(theme.detect_icon_path(icon_name="logo", prefix="mk-"), class_="custom")
        else:
            html.img(theme.detect_icon_path(icon_name="icon_min", prefix="tribe29_"))
    else:
        if theme.has_custom_logo():
            html.img(theme.detect_icon_path(icon_name="logo", prefix="mk-"))
        else:
            html.img(theme.detect_icon_path(icon_name="icon", prefix="tribe29_"))


@cmk.gui.pages.register("side")
def page_side():
    SidebarRenderer().show()


@cmk.gui.pages.register("sidebar_snapin")
def ajax_snapin():
    """Renders and returns the contents of the requested sidebar snapin(s) in JSON format"""
    response.set_content_type("application/json")
    user_config = UserSidebarConfig(user, config.sidebar)

    snapin_id = request.var("name")
    snapin_ids = (
        [snapin_id] if snapin_id else request.get_str_input_mandatory("names", "").split(",")
    )

    snapin_code: List[str] = []
    for snapin_id in snapin_ids:
        try:
            snapin_instance = user_config.get_snapin(snapin_id).snapin_type()
        except KeyError:
            continue  # Skip not existing snapins

        if not snapin_instance.may_see():
            continue

        # When restart snapins are about to be refreshed, only render
        # them, when the core has been restarted after their initial
        # rendering
        if not snapin_instance.refresh_regularly() and snapin_instance.refresh_on_restart():
            since = request.get_float_input_mandatory("since", 0)
            newest = since
            for site in sites.states().values():
                prog_start = site.get("program_start", 0)
                if prog_start > newest:
                    newest = prog_start
            if newest <= since:
                # no restart
                snapin_code.append("")
                continue

        with output_funnel.plugged():
            try:
                snapin_instance.show()
            except Exception as e:
                write_snapin_exception(e)
                e_message = (
                    _("Exception during element refresh (element '%s')")
                    % snapin_instance.type_name()
                )
                logger.error("%s %s: %s", request.requested_url, e_message, traceback.format_exc())
            finally:
                snapin_code.append(output_funnel.drain())

    response.set_data(json.dumps(snapin_code))


@cmk.gui.pages.register("sidebar_fold")
def ajax_fold():
    response.set_content_type("application/json")
    user_config = UserSidebarConfig(user, config.sidebar)
    user_config.folded = request.var("fold") == "yes"
    user_config.save()


@cmk.gui.pages.register("sidebar_openclose")
def ajax_openclose() -> None:
    response.set_content_type("application/json")
    if not user.may("general.configure_sidebar"):
        return None

    snapin_id = request.var("name")
    if snapin_id is None:
        return None

    state = request.var("state")
    if state not in [SnapinVisibility.OPEN.value, SnapinVisibility.CLOSED.value, "off"]:
        raise MKUserError("state", "Invalid state: %s" % state)

    user_config = UserSidebarConfig(user, config.sidebar)

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
def move_snapin() -> None:
    response.set_content_type("application/json")
    if not user.may("general.configure_sidebar"):
        return None

    snapin_id = request.var("name")
    if snapin_id is None:
        return None

    user_config = UserSidebarConfig(user, config.sidebar)

    try:
        snapin = user_config.get_snapin(snapin_id)
    except KeyError:
        return None

    before_id = request.var("before")
    before_snapin: Optional[UserSidebarSnapin] = None
    if before_id:
        try:
            before_snapin = user_config.get_snapin(before_id)
        except KeyError:
            pass

    user_config.move_snapin_before(snapin, before_snapin)
    user_config.save()


# .
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
    def type_icon(cls):
        return "custom_snapin"

    @classmethod
    def type_is_show_more(cls) -> bool:
        return True

    @classmethod
    def phrase(cls, phrase):
        return {
            "title": _("Custom sidebar element"),
            "title_plural": _("Custom sidebar elements"),
            # "add_to"         : _("Add to custom element list"),
            "clone": _("Clone element"),
            "create": _("Create element"),
            "edit": _("Edit element"),
            "new": _("New element"),
        }.get(phrase, pagetypes.Base.phrase(phrase))

    @classmethod
    def parameters(cls, mode):
        parameters = super().parameters(mode)

        parameters += [
            (
                cls.phrase("title"),
                # sort-index, key, valuespec
                [
                    (
                        2.5,
                        "custom_snapin",
                        CascadingDropdown(
                            title=_("Element type"),
                            choices=cls._customizable_snapin_type_choices,
                        ),
                    )
                ],
            )
        ]

        return parameters

    @classmethod
    def _customizable_snapin_type_choices(cls):
        choices = []
        for snapin_type_id, snapin_type in sorted(snapin_registry.get_customizable_snapin_types()):
            choices.append(
                (
                    snapin_type_id,
                    snapin_type.title(),
                    Dictionary(
                        title=_("Parameters"),
                        elements=snapin_type.vs_parameters(),
                        optional_keys=[],
                    ),
                )
            )
        return choices


pagetypes.declare(CustomSnapins)


def _register_custom_snapins():
    """First remove all previously registered custom snapins, then register
    the currently configured ones"""
    CustomSnapins.load()
    snapin_registry.register_custom_snapins(CustomSnapins.instances_sorted())


register_post_config_load_hook(_register_custom_snapins)

# .
#   .--Add Snapin----------------------------------------------------------.
#   |           _       _     _   ____                    _                |
#   |          / \   __| | __| | / ___| _ __   __ _ _ __ (_)_ __           |
#   |         / _ \ / _` |/ _` | \___ \| '_ \ / _` | '_ \| | '_ \          |
#   |        / ___ \ (_| | (_| |  ___) | | | | (_| | |_) | | | | |         |
#   |       /_/   \_\__,_|\__,_| |____/|_| |_|\__,_| .__/|_|_| |_|         |
#   |                                              |_|                     |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("sidebar_add_snapin")
def page_add_snapin() -> None:
    if not user.may("general.configure_sidebar"):
        raise MKGeneralException(_("You are not allowed to change the sidebar."))

    title = _("Add sidebar element")
    breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_customize(), title)
    html.header(title, breadcrumb, _add_snapins_page_menu(breadcrumb))

    used_snapins = _used_snapins()

    html.open_div(class_=["add_snapin"])
    for name, snapin_class in sorted(snapin_registry.items()):
        if name in used_snapins:
            continue
        if not snapin_class.may_see():
            continue  # not allowed for this user

        html.open_div(
            class_="snapinadder",
            onmouseover="this.style.cursor='pointer';",
            onclick="window.top.cmk.sidebar.add_snapin('%s')" % name,
        )

        html.open_div(class_=["snapin_preview"])
        html.div("", class_=["clickshield"])
        SidebarRenderer().render_snapin(UserSidebarSnapin.from_snapin_type_id(name))
        html.close_div()
        html.div(snapin_class.description(), class_=["description"])
        html.close_div()

    html.close_div()
    html.footer()


def _add_snapins_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    return PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Configure"),
                        entries=list(CustomSnapins.page_menu_entry_list()),
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )


def _used_snapins() -> List[Any]:
    user_config = UserSidebarConfig(user, config.sidebar)
    return [snapin.snapin_type.type_name() for snapin in user_config.snapins]


@cmk.gui.pages.page_registry.register_page("sidebar_ajax_add_snapin")
class AjaxAddSnapin(cmk.gui.pages.AjaxPage):
    def page(self):
        if not user.may("general.configure_sidebar"):
            raise MKGeneralException(_("You are not allowed to change the sidebar."))

        addname = request.var("name")

        if addname is None or addname not in snapin_registry:
            raise MKUserError(None, _("Invalid sidebar element %s") % addname)

        if addname in _used_snapins():
            raise MKUserError(None, _("Element %s is already enabled") % addname)

        user_config = UserSidebarConfig(user, config.sidebar)
        snapin = UserSidebarSnapin.from_snapin_type_id(addname)
        user_config.add_snapin(snapin)
        user_config.save()

        with output_funnel.plugged():
            try:
                url = SidebarRenderer().render_snapin(snapin)
            finally:
                snapin_code = output_funnel.drain()

        return {
            "name": addname,
            "url": url,
            "content": snapin_code,
            "refresh": snapin.snapin_type.refresh_regularly(),
            "restart": snapin.snapin_type.refresh_on_restart(),
        }


# TODO: This is snapin specific. Move this handler to the snapin file
@cmk.gui.pages.register("sidebar_ajax_set_snapin_site")
def ajax_set_snapin_site():
    response.set_content_type("application/json")
    ident = request.var("ident")
    if ident not in snapin_registry:
        raise MKUserError(None, _("Invalid ident"))

    site = request.var("site")
    site_choices = dict([(SiteId(""), _("All sites"))] + sites.get_configured_site_choices())

    if site not in site_choices:
        raise MKUserError(None, _("Invalid site"))

    snapin_sites = user.load_file("sidebar_sites", {}, lock=True)
    snapin_sites[ident] = site
    user.save_file("sidebar_sites", snapin_sites)
