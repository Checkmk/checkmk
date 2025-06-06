#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable
from typing import TypedDict

from cmk.gui import site_config, sites
from cmk.gui.config import active_config, Config
from cmk.gui.dashboard import get_permitted_dashboards
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import get_main_menu_items_prefixed_by_segment, MainMenuRegistry
from cmk.gui.sidebar import (
    footnotelinks,
    make_main_menu,
    show_main_menu,
    SidebarSnapin,
    SnapinRegistry,
)
from cmk.gui.type_defs import (
    ABCMainMenuSearch,
    Choices,
    MainMenu,
    MainMenuItem,
    MainMenuTopic,
    RoleName,
    ViewSpec,
    Visual,
)
from cmk.gui.views.store import get_permitted_views
from cmk.gui.watolib.activate_changes import ActivateChanges
from cmk.gui.watolib.hosts_and_folders import folder_tree, FolderTree
from cmk.gui.watolib.main_menu import main_module_registry, MainModuleTopic
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItemGeneratorRegistry,
    MatchItems,
)


def register(
    snapin_registry: SnapinRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
    main_menu_registry: MainMenuRegistry,
) -> None:
    snapin_registry.register(SidebarSnapinWATOMini)
    snapin_registry.register(SidebarSnapinWATOFoldertree)
    match_item_generator_registry.register(MatchItemGeneratorSetup)
    main_menu_registry.register(MainMenuSetup)


def render_wato(config: Config, mini: bool) -> None:
    if not config.wato_enabled:
        html.write_text_permissive(_("Setup is disabled."))
    if not user.may("wato.use"):
        html.write_text_permissive(_("You are not allowed to use the setup."))

    menu = get_wato_menu_items()

    if mini:
        for topic in menu:
            for item in get_main_menu_items_prefixed_by_segment(topic):
                html.icon_button(
                    url=item.url,
                    class_=["show_more_mode"] if item.is_show_more else [],
                    title=item.title,
                    icon=item.icon or "wato",
                    target="main",
                )
    else:
        show_main_menu(treename="wato", menu=menu, show_item_icons=True)

    pending_info = ActivateChanges().get_pending_changes_info(count_limit=10)
    if pending_info.has_changes():
        assert pending_info.message is not None  # only for mypy, semantically useless
        footnotelinks([(pending_info.message, "wato.py?mode=changelog")])
        html.div("", class_="clear")


def get_wato_menu_items() -> list[MainMenuTopic]:
    by_topic: dict[MainModuleTopic, MainMenuTopic] = {}
    for module_class in main_module_registry.values():
        module = module_class()

        if not module.may_see():
            continue

        topic = by_topic.setdefault(
            module.topic,
            MainMenuTopic(
                name=module.topic.name,
                title=str(module.topic.title),
                icon=module.topic.icon_name,
                entries=[],
            ),
        )
        topic.entries.append(
            MainMenuItem(
                name=module.mode_or_url,
                title=module.title,
                url=module.get_url(),
                sort_index=module.sort_index,
                is_show_more=module.is_show_more,
                icon=module.icon,
                main_menu_search_terms=module.main_menu_search_terms(),
            )
        )

    # Sort the entries of all topics
    for topic in by_topic.values():
        topic.entries.sort(key=lambda i: (i.sort_index, i.title))

    # Return the sorted topics
    return [v for k, v in sorted(by_topic.items(), key=lambda e: (e[0].sort_index, e[0].title))]


def _hide_menu() -> bool:
    return site_config.is_wato_slave_site() and not active_config.wato_enabled


class SetupSearch(ABCMainMenuSearch):
    """Search field in the setup menu"""

    def show_search_field(self) -> None:
        html.open_div(id_="mk_side_search_setup")
        # TODO: Implement submit action (e.g. show all results of current query)
        with html.form_context(f"mk_side_{self.name}", add_transid=False, onsubmit="return false;"):
            tooltip = _("Search for menu entries, settings, hosts and rule sets.")
            html.input(
                id_=f"mk_side_search_field_{self.name}",
                type_="text",
                name="search",
                title=tooltip,
                autocomplete="off",
                placeholder=_("Search in Setup"),
                onkeydown="cmk.search.on_key_down('setup')",
                oninput="cmk.search.on_input_search('setup');",
            )
            html.input(
                id_=f"mk_side_search_field_clear_{self.name}",
                name="reset",
                type_="button",
                onclick="cmk.search.on_click_reset('setup');",
                # When the user searched for something, let him jump to the first result with the first
                # <TAB> key press instead of jumping to the reset button. The reset can be triggered via
                # the <ESC> key.
                tabindex="-1",
            )
        html.close_div()
        html.div("", id_="mk_side_clear")


MainMenuSetup = MainMenu(
    name="setup",
    title=_l("Setup"),
    icon="main_setup",
    sort_index=5,
    topics=get_wato_menu_items,
    search=SetupSearch("setup_search"),
    hide=_hide_menu,
)


class MatchItemGeneratorSetupMenu(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        topic_generator: Callable[[], Iterable[MainMenuTopic]] | None,
    ) -> None:
        super().__init__(name)
        self._topic_generator = topic_generator

    def generate_match_items(self) -> MatchItems:
        yield from (
            MatchItem(
                title=main_menu_item.title,
                topic=_("Setup"),
                url=main_menu_item.url,
                match_texts=[
                    main_menu_item.title,
                    *main_menu_item.main_menu_search_terms,
                ],
            )
            for main_menu_topic in (self._topic_generator() if self._topic_generator else [])
            for main_menu_item in get_main_menu_items_prefixed_by_segment(main_menu_topic)
        )

    @staticmethod
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    def is_localization_dependent(self) -> bool:
        return True


MatchItemGeneratorSetup = MatchItemGeneratorSetupMenu("setup", MainMenuSetup.topics)


class SidebarSnapinWATOMini(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "admin_mini"

    @classmethod
    def title(cls) -> str:
        return _("Setup shortcuts")

    @classmethod
    def has_show_more_items(cls) -> bool:
        return True

    @classmethod
    def description(cls) -> str:
        return _("Access to the setup menu with only icons (saves space)")

    @classmethod
    def allowed_roles(cls) -> list[RoleName]:
        return ["admin", "user"]

    # refresh pending changes, if other user modifies something
    @classmethod
    def refresh_regularly(cls) -> bool:
        return True

    def show(self, config: Config) -> None:
        render_wato(config, mini=True)


FolderEntry = TypedDict(
    "FolderEntry",
    {
        ".folders": dict[str, "FolderEntry"],
        ".num_hosts": int,
        ".path": str,
        "title": str,
    },
)


def compute_foldertree() -> dict[str, FolderEntry]:
    sites.live().set_prepend_site(True)
    query = "GET hosts\nStats: state >= 0\nColumns: filename"
    hosts = sites.live().query(query)
    sites.live().set_prepend_site(False)

    def get_folder(tree: FolderTree, path: str, num: int = 0) -> FolderEntry:
        folder = tree.folder(path)
        return FolderEntry(
            {
                "title": folder.title() or path.split("/")[-1],
                ".path": path,
                ".num_hosts": num,
                ".folders": {},
            }
        )

    # After the query we have a list of lists where each
    # row is a folder with the number of hosts on this level.
    #
    # Now get number of hosts by folder
    # Count all children for each folder
    user_folders: dict[str, FolderEntry] = {}
    tree = folder_tree()
    for _site, filename, num in sorted(hosts):
        # Remove leading /wato/
        wato_folder_path = filename[6:]

        # Loop through all levels of this folder to add the
        # host count to all parent levels
        path_parts = wato_folder_path.split("/")
        for num_parts in range(0, len(path_parts)):
            this_folder_path = "/".join(path_parts[:num_parts])

            if tree.folder_exists(this_folder_path):
                if this_folder_path not in user_folders:
                    user_folders[this_folder_path] = get_folder(tree, this_folder_path, num)
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


def render_tree_folder(tree_id: str, folder: FolderEntry, js_func: str) -> None:
    subfolders = folder.get(".folders", {}).values()
    is_leaf = len(subfolders) == 0

    # Suppress indentation for non-emtpy root folder
    if folder[".path"] == "" and is_leaf:
        html.open_ul()  # empty root folder
    elif folder and folder[".path"] != "":
        html.open_ul(style="padding-left:0px;")

    title = HTMLWriter.render_a(
        "%s (%d)" % (folder["title"], folder[".num_hosts"]),
        href="#",
        class_="link",
        onclick="{}(this, '{}');".format(js_func, folder[".path"]),
    )

    if not is_leaf:
        with foldable_container(
            treename=tree_id,
            id_="/" + folder[".path"],
            isopen=False,
            title=title,
            padding=6,
        ):
            for subfolder in sorted(subfolders, key=lambda x: x["title"].lower()):
                render_tree_folder(tree_id, subfolder, js_func)
    else:
        html.li(title, class_="single")

    html.close_ul()


class SidebarSnapinWATOFoldertree(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "wato_foldertree"

    @classmethod
    def title(cls) -> str:
        return _("Tree of folders")

    @classmethod
    def description(cls) -> str:
        return _(
            "This snap-in shows the folders defined in Setup. It can be used to "
            "open views filtered by the Setup folder. It works standalone, without "
            "interaction with any other snap-in."
        )

    def show(self, config: Config) -> None:
        if not site_config.is_wato_slave_site():
            if not config.wato_enabled:
                html.write_text_permissive(_("Setup is disabled."))

        user_folders = compute_foldertree()

        #
        # Render link target selection
        #
        # Apply some view specific filters
        views_to_show: list[tuple[str, ViewSpec]] = []
        dflt_target_name: str = "allhosts"
        dflt_topic_name: str = ""
        for name, view in get_permitted_views().items():
            if (not config.visible_views or name in config.visible_views) and (
                not config.hidden_views or name not in config.hidden_views
            ):
                views_to_show.append((name, view))
                if name == dflt_target_name:
                    dflt_topic_name = view["topic"]

        selected_topic_name: str
        selected_target_name: str
        selected_topic_name, selected_target_name = user.load_file(
            "foldertree", (dflt_topic_name, dflt_target_name)
        )

        visuals_to_show: list[tuple[str, tuple[str, Visual]]] = [
            ("views", (k, v)) for k, v in views_to_show
        ]
        visuals_to_show += [("dashboards", (k, v)) for k, v in get_permitted_dashboards().items()]

        topics = make_main_menu(visuals_to_show)
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
            for item in get_main_menu_items_prefixed_by_segment(topic):
                if item.url and item.url.startswith("dashboard.py"):
                    name = "dashboard|" + item.name
                else:
                    name = item.name
                targets.append((name, item.title))

            if topic.title.lower() != selected_topic_name.lower():
                default = ""
                style: str | None = "display:none"
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
                "wato-hosts",
                list(user_folders.values())[0],
                "cmk.sidebar.wato_tree_click",
            )
