#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, Dict, Iterable, List, Optional, Tuple

import cmk.gui.dashboard as dashboard
import cmk.gui.site_config as site_config
import cmk.gui.sites as sites
import cmk.gui.views as views
from cmk.gui.config import active_config
from cmk.gui.htmllib.context import html
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.plugins.sidebar import search
from cmk.gui.plugins.sidebar.utils import (
    footnotelinks,
    make_topic_menu,
    show_topic_menu,
    SidebarSnapin,
    snapin_registry,
)
from cmk.gui.plugins.wato.utils.main_menu import main_module_registry, MainModuleTopic
from cmk.gui.type_defs import Choices, MegaMenu, TopicMenuItem, TopicMenuTopic, ViewSpec
from cmk.gui.utils.html import HTML
from cmk.gui.watolib.activate_changes import get_pending_changes_info
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    match_item_generator_registry,
    MatchItem,
    MatchItems,
)


def render_wato(mini):
    if not active_config.wato_enabled:
        html.write_text(_("Setup is disabled."))
        return False
    if not user.may("wato.use"):
        html.write_text(_("You are not allowed to use the setup."))
        return False

    menu = get_wato_menu_items()

    if mini:
        for topic in menu:
            for item in topic.items:
                html.icon_button(
                    url=item.url,
                    class_="show_more_mode" if item.is_show_more else None,
                    title=item.title,
                    icon=item.icon or "wato",
                    target="main",
                )
    else:
        show_topic_menu(treename="wato", menu=menu, show_item_icons=True)

    pending_info = get_pending_changes_info()
    if pending_info:
        footnotelinks([(pending_info, "wato.py?mode=changelog")])
        html.div("", class_="clear")


def get_wato_menu_items() -> List[TopicMenuTopic]:
    by_topic: Dict[MainModuleTopic, TopicMenuTopic] = {}
    for module_class in main_module_registry.values():
        module = module_class()

        if not module.may_see():
            continue

        topic = by_topic.setdefault(
            module.topic,
            TopicMenuTopic(
                name=module.topic.name,
                title=str(module.topic.title),
                icon=module.topic.icon_name,
                items=[],
            ),
        )
        topic.items.append(
            TopicMenuItem(
                name=module.mode_or_url,
                title=module.title,
                url=module.get_url(),
                sort_index=module.sort_index,
                is_show_more=module.is_show_more,
                icon=module.icon,
            )
        )

    # Sort the items of all topics
    for topic in by_topic.values():
        topic.items.sort(key=lambda i: (i.sort_index, i.title))

    # Return the sorted topics
    return [v for k, v in sorted(by_topic.items(), key=lambda e: (e[0].sort_index, e[0].title))]


mega_menu_registry.register(
    MegaMenu(
        name="setup",
        title=_l("Setup"),
        icon="main_setup",
        sort_index=15,
        topics=get_wato_menu_items,
        search=search.SetupSearch("setup_search"),
    )
)


class MatchItemGeneratorSetupMenu(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        topic_generator: Callable[[], Iterable[TopicMenuTopic]],
    ) -> None:
        super().__init__(name)
        self._topic_generator = topic_generator

    def generate_match_items(self) -> MatchItems:
        yield from (
            MatchItem(
                title=topic_menu_item.title,
                topic=_("Setup"),
                url=topic_menu_item.url,
                match_texts=[topic_menu_item.title],
            )
            for topic_menu_topic in self._topic_generator()
            for topic_menu_item in topic_menu_topic.items
        )

    @staticmethod
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    def is_localization_dependent(self) -> bool:
        return True


match_item_generator_registry.register(
    MatchItemGeneratorSetupMenu(
        "setup",
        mega_menu_registry["setup"].topics,
    )
)


@snapin_registry.register
class SidebarSnapinWATOMini(SidebarSnapin):
    @staticmethod
    def type_name():
        return "admin_mini"

    @classmethod
    def title(cls):
        return _("Quick setup")

    @classmethod
    def has_show_more_items(cls):
        return True

    @classmethod
    def description(cls):
        return _("Access to the setup menu with only icons (saves space)")

    @classmethod
    def allowed_roles(cls):
        return ["admin", "user"]

    # refresh pending changes, if other user modifies something
    @classmethod
    def refresh_regularly(cls):
        return True

    def show(self):
        render_wato(mini=True)


def compute_foldertree():
    sites.live().set_prepend_site(True)
    query = "GET hosts\nStats: state >= 0\nColumns: filename"
    hosts = sites.live().query(query)
    sites.live().set_prepend_site(False)

    def get_folder(path, num=0):
        folder = Folder.folder(path)
        return {
            "title": folder.title() or path.split("/")[-1],
            ".path": path,
            ".num_hosts": num,
            ".folders": {},
        }

    # After the query we have a list of lists where each
    # row is a folder with the number of hosts on this level.
    #
    # Now get number of hosts by folder
    # Count all childs for each folder
    user_folders = {}
    for _site, filename, num in sorted(hosts):
        # Remove leading /wato/
        wato_folder_path = filename[6:]

        # Loop through all levels of this folder to add the
        # host count to all parent levels
        path_parts = wato_folder_path.split("/")
        for num_parts in range(0, len(path_parts)):
            this_folder_path = "/".join(path_parts[:num_parts])

            if Folder.folder_exists(this_folder_path):
                if this_folder_path not in user_folders:
                    user_folders[this_folder_path] = get_folder(this_folder_path, num)
                else:
                    user_folders[this_folder_path][".num_hosts"] += num

    #
    # Now build the folder tree
    #
    for folder_path, folder in sorted(user_folders.items(), reverse=True):
        if not folder_path:
            continue
        folder_parts = folder_path.split("/")
        parent_folder = "/".join(folder_parts[:-1])

        user_folders[parent_folder][".folders"][folder_path] = folder
        del user_folders[folder_path]

    #
    # Now reduce the tree by e.g. removing top-level parts which the user is not
    # permitted to see directly. Example:
    # Locations
    #  -> Hamburg: Permitted to see all hosts
    #  -> Munich:  Permitted to see no host
    # In this case, where only a single child with hosts is available, remove the
    # top level
    def reduce_tree(folders):
        for folder_path, folder in folders.items():
            if len(folder[".folders"]) == 1 and folder[".num_hosts"] == 0:
                child_path, child_folder = list(folder[".folders"].items())[0]
                folders[child_path] = child_folder
                del folders[folder_path]

                reduce_tree(folders)

    reduce_tree(user_folders)
    return user_folders


# Note: the dictionary that represents the folder here is *not*
# the datastructure from WATO but a result of compute_foldertree(). The reason:
# We fetch the information via livestatus - not from WATO.
def render_tree_folder(tree_id, folder, js_func):
    subfolders = folder.get(".folders", {}).values()
    is_leaf = len(subfolders) == 0

    # Suppress indentation for non-emtpy root folder
    if folder[".path"] == "" and is_leaf:
        html.open_ul()  # empty root folder
    elif folder and folder[".path"] != "":
        html.open_ul(style="padding-left:0px;")

    title = html.render_a(
        "%s (%d)" % (folder["title"], folder[".num_hosts"]),
        href="#",
        class_="link",
        onclick="%s(this, '%s');" % (js_func, folder[".path"]),
    )

    if not is_leaf:
        with foldable_container(
            treename=tree_id,
            id_="/" + folder[".path"],
            isopen=False,
            title=HTML(title),
            icon="foldable_sidebar",
            padding=6,
        ):
            for subfolder in sorted(subfolders, key=lambda x: x["title"].lower()):
                render_tree_folder(tree_id, subfolder, js_func)
    else:
        html.li(title)

    html.close_ul()


@snapin_registry.register
class SidebarSnapinWATOFoldertree(SidebarSnapin):
    @staticmethod
    def type_name():
        return "wato_foldertree"

    @classmethod
    def title(cls):
        return _("Tree of folders")

    @classmethod
    def description(cls):
        return _(
            "This snapin shows the folders defined in WATO. It can be used to "
            "open views filtered by the WATO folder. It works standalone, without "
            "interaction with any other snapin."
        )

    def show(self):
        if not site_config.is_wato_slave_site():
            if not active_config.wato_enabled:
                html.write_text(_("Setup is disabled."))
                return False

        user_folders = compute_foldertree()

        #
        # Render link target selection
        #
        # Apply some view specific filters
        views_to_show: List[Tuple[str, ViewSpec]] = []
        dflt_target_name: str = "allhosts"
        dflt_topic_name: str = ""
        for name, view in views.get_permitted_views().items():
            if (not active_config.visible_views or name in active_config.visible_views) and (
                not active_config.hidden_views or name not in active_config.hidden_views
            ):
                views_to_show.append((name, view))
                if name == dflt_target_name:
                    dflt_topic_name = view["topic"]

        selected_topic_name: str
        selected_target_name: str
        selected_topic_name, selected_target_name = user.load_file(
            "foldertree", (dflt_topic_name, dflt_target_name)
        )

        visuals_to_show = [("views", e) for e in views_to_show]
        visuals_to_show += [("dashboards", e) for e in dashboard.get_permitted_dashboards().items()]

        topics = make_topic_menu(visuals_to_show)
        topic_choices: Choices = [(topic.title, topic.title) for topic in topics]

        html.open_table()
        html.open_tr()
        html.open_td()
        html.dropdown(
            "topic",
            topic_choices,
            deflt=selected_topic_name,
            onchange="cmk.sidebar.wato_tree_topic_changed(this)",
        )
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()

        for topic in topics:
            targets: Choices = []
            for item in topic.items:
                if item.url and item.url.startswith("dashboard.py"):
                    name = "dashboard|" + item.name
                else:
                    name = item.name
                targets.append((name, item.title))

            if topic.name != selected_topic_name:
                default = ""
                style: Optional[str] = "display:none"
            else:
                default = selected_target_name
                style = None
            html.dropdown(
                "target_%s" % topic.title,
                targets,
                deflt=default,
                onchange="cmk.sidebar.wato_tree_target_changed(this)",
                style=style,
            )

        html.close_td()
        html.close_tr()
        html.close_table()

        # Now render the whole tree
        if user_folders:
            render_tree_folder(
                "wato-hosts", list(user_folders.values())[0], "cmk.sidebar.wato_tree_click"
            )
