#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

"""Simple download page for the built-in agents and plugins"""

import abc
import fnmatch
import os
from collections.abc import Callable, Collection, Generator, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Final, override

import cmk.utils.paths
import cmk.utils.render
from cmk.discover_plugins import AGENT_PLUGINS_FOLDER, discover_families
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, PageContext, PageEndpoint, PageRegistry
from cmk.gui.type_defs import IconNames, PermissionName, StaticIcon
from cmk.gui.utils import agent
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.mode import ModeRegistry, WatoMode

# Page names of the GUI handlers that stream agent plugin files which live outside
# the statically served share/check_mk/agents tree (e.g. cmk/plugins/<family>/agents/).
# Files shipped with the version are served without authentication, just like the files
# below the statically served tree. Files of locally installed plugins are not.
DOWNLOAD_AGENT_PLUGIN_PAGE = "download_agent_plugin"
DOWNLOAD_LOCAL_AGENT_PLUGIN_PAGE = "download_local_agent_plugin"


def register(page_registry: PageRegistry, mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeDownloadAgentsOther)
    mode_registry.register(ModeDownloadAgentsWindows)
    mode_registry.register(ModeDownloadAgentsLinux)

    # The endpoints handing out the files need to filter for allowed ones themselves!
    # Bonus: fills the cache of _plugin_family_agent_dirs at apache load.
    available_dirs = [d.path for d in _plugin_family_agent_dirs()]
    page_registry.register(
        PageEndpoint(
            f"noauth:{DOWNLOAD_AGENT_PLUGIN_PAGE}",
            PageDownloadAgentPlugin(
                [p for p in available_dirs if not p.is_relative_to(cmk.utils.paths.local_root)],
                require_permission=False,
            ),
        )
    )
    page_registry.register(
        PageEndpoint(
            DOWNLOAD_LOCAL_AGENT_PLUGIN_PAGE,
            PageDownloadAgentPlugin(
                available_dirs,
                require_permission=True,
            ),
        )
    )


@dataclass(frozen=True)
class PluginFamilyAgentDir:
    """An agent plugin directory of a single plugin family (cmk.bakery.v2).

    These live under lib/python3/cmk/plugins/<family>/agents/ - i.e. outside the
    statically served share/check_mk/agents tree - so files found here must be
    downloaded through a GUI handler, not the Apache alias.
    """

    path: Path
    title: str
    is_local: bool


@lru_cache  # This is based on python imports and thus never changes for a running process
def _plugin_family_agent_dirs() -> Sequence[PluginFamilyAgentDir]:
    """Discover the agent plugin directory of every plugin family.

    ``discover_families`` returns keys like ``cmk.plugins.oracle``; we use the
    last dotted component ("oracle") as a human readable section title ("Oracle")
    so that files of different families are not all lumped under one generic
    "Agents" header on the download page.

    It also finds the families installed below ``local/`` (e.g. via MKP). Those are
    not shipped with the version, so they are marked to be handled separately.
    """
    return [
        PluginFamilyAgentDir(
            path=Path(family_path, AGENT_PLUGINS_FOLDER),
            title=family.split(".")[-1].capitalize(),
            is_local=Path(family_path).is_relative_to(cmk.utils.paths.local_root),
        )
        for family, family_paths in sorted(discover_families(raise_errors=False).items())
        for family_path in family_paths
    ]


def download_href(path: str) -> str:
    """Build the download URL for an offered agent file.

    Files below share/check_mk/agents are served statically by the Apache alias
    "check_mk/agents", so a relative URL resolves against the current page. Plugin
    family agent files live outside that tree (e.g. lib/python3/cmk/plugins/<family>/
    agents/) and are streamed through a GUI handler instead - the one requiring
    authentication if the file belongs to a locally installed plugin family.
    """
    agents_dir_prefix = str(cmk.utils.paths.agents_dir) + "/"
    if path.startswith(agents_dir_prefix):
        return "agents/%s" % path[len(agents_dir_prefix) :]

    is_local = Path(path).is_relative_to(cmk.utils.paths.local_root)
    return makeuri_contextless(
        request,
        [("path", path)],
        filename=(
            f"{DOWNLOAD_LOCAL_AGENT_PLUGIN_PAGE}.py"
            if is_local
            else f"{DOWNLOAD_AGENT_PLUGIN_PAGE}.py"
        ),
    )


class ABCModeDownloadAgents(WatoMode):
    _TITLES = {
        "": _("Agents"),
        "/plugins": _("Plug-ins"),
        "/cfg_examples": _("Example configurations"),
        "/cfg_examples/systemd": _("Example configuration for systemd"),
        "/windows": _("Windows agent"),
        "/windows/plugins": _("Plug-ins"),
        "/windows/mrpe": _("Scripts to integrate Nagios plugis"),
        "/windows/cfg_examples": _("Example configurations"),
        "/z_os": _("z/OS"),
        "/sap": _("SAP R/3"),
    }

    related_page_menu_hook: Callable[[], Iterator[PageMenuEntry]] = lambda: iter([])

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["download_agents"]

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield from ABCModeDownloadAgents.related_page_menu_hook()

        if self.name() != "download_agents_windows":
            yield PageMenuEntry(
                title=_("Windows files"),
                icon_name=StaticIcon(IconNames.download_agents),
                item=make_simple_link(
                    folder_preserving_link(request, [("mode", "download_agents_windows")])
                ),
            )

        if self.name() != "download_agents_linux":
            yield PageMenuEntry(
                title=_("Linux, Solaris, AIX files"),
                icon_name=StaticIcon(IconNames.download_agents),
                item=make_simple_link(
                    folder_preserving_link(request, [("mode", "download_agents_linux")])
                ),
            )

        if self.name() != "download_agents":
            yield PageMenuEntry(
                title=_("Other operating systems"),
                icon_name=StaticIcon(IconNames.download_agents),
                item=make_simple_link(
                    folder_preserving_link(request, [("mode", "download_agents")])
                ),
            )

    @abc.abstractmethod
    def _packed_agents(self) -> list[str]: ...

    @abc.abstractmethod
    def _walk_base_dirs(self) -> list[str]: ...

    def _exclude_file_glob_patterns(self) -> list[str]:
        return []

    def _exclude_paths(self) -> set[str]:
        return {
            "/bakery",
            "/special",
            "/windows/baked_container.msi",
            "/windows/plugins/.gitattributes",
        }

    @override
    def page(self, config: Config) -> None:
        html.open_div(class_="rulesets")

        if packed := self._packed_agents():
            self._download_table(_("Packaged agents"), packed)

        for title, file_paths in sorted(
            entry for base_dir in self._walk_base_dirs() for entry in self._walk_dir(base_dir)
        ):
            useful_file_paths = [p for p in file_paths if not p.endswith("/CONTENTS")]
            if useful_file_paths:
                self._download_table(title, sorted(useful_file_paths))
        html.close_div()

    def _walk_dir(self, dir_path: str) -> Generator[tuple[str, list[str]]]:
        banned_paths = self._exclude_paths()
        packed = self._packed_agents()

        for root, _dirs, files in os.walk(dir_path):
            file_paths = []
            relpath = root.split("agents")[1]
            if relpath in banned_paths:
                continue

            title = self._title_for_root(root, relpath)
            for filename in files:
                rel_file_path = relpath + "/" + filename
                if rel_file_path in banned_paths:
                    continue

                if self._exclude_by_pattern(rel_file_path):
                    continue

                path = root + "/" + filename
                if path not in packed and "deprecated" not in path:
                    file_paths.append(path)

            yield (title, file_paths)

    def _exclude_by_pattern(self, rel_file_path: str) -> bool:
        for exclude_pattern in self._exclude_file_glob_patterns():
            if fnmatch.fnmatch(rel_file_path, exclude_pattern):
                return True
        return False

    def _title_for_root(self, root: str, relpath: str) -> str:
        """Section title for the files found directly below ``root``."""
        return self._TITLES.get(relpath, relpath)

    def _download_table(self, title: str, paths: list[str]) -> None:
        forms.header(title)
        forms.container()
        for path in paths:
            os_path = path
            filename = path.split("/")[-1]

            file_size = os.stat(os_path).st_size

            # FIXME: Rename classes etc. to something generic
            html.open_div(class_="ruleset")
            html.open_div(style="width:300px;", class_="text")
            html.a(filename, href=download_href(path), download=filename)
            html.span("." * 200, class_="dots")
            html.close_div()
            html.div(cmk.utils.render.fmt_bytes(file_size), style="width:60px;", class_="rulecount")
            html.close_div()
        forms.end()


class ModeDownloadAgentsOther(ABCModeDownloadAgents):
    @classmethod
    @override
    def name(cls) -> str:
        return "download_agents"

    @override
    def title(self) -> str:
        return _("Other operating systems")

    @override
    def _packed_agents(self) -> list[str]:
        return []

    @override
    def _walk_base_dirs(self) -> list[str]:
        return [
            str(cmk.utils.paths.agents_dir),
            # With cmk.bakery.v2, agent plugin files are grouped according to their plugin family.
            # This does not play nicely with the structure of this page.
            # We just include all of those files here for now (discarding the information about their family).
            # It would be nice to support some sort of meta data file per family, providing maybe
            # * general information
            # * a (allow/deny) list of the files that should be exposed for download
            # * description / title for those.
            *(str(d.path) for d in _plugin_family_agent_dirs()),
        ]

    @override
    def _exclude_file_glob_patterns(self) -> list[str]:
        return [
            "*.rpm",
            "*.deb",
            "*.aix",
            "*.linux",
            "*.solaris",
            "*robotmk*",
        ]

    @cached_property
    def _title_map(self) -> Mapping[str, str]:
        return {
            str(d.path): (
                # Downloading these requires a login, while all other offered files
                # are served without authentication. Say so.
                _("%(family)s (locally installed, download requires login)") % {"family": d.title}
                if d.is_local
                else d.title
            )
            for d in _plugin_family_agent_dirs()
        }

    @override
    def _title_for_root(self, root: str, relpath: str) -> str:
        # Files of a plugin family live in their own agents directory outside the
        # share tree; title their section by the family instead of the generic
        # "Agents" that the path based lookup would yield.
        try:
            return self._title_map[root]
        except KeyError:
            return super()._title_for_root(root, relpath)

    @override
    def _exclude_paths(self) -> set[str]:
        exclude = super()._exclude_paths()
        exclude.add("/cfg_examples/systemd")
        exclude.add("/__pycache__")
        exclude.add("/sap")
        exclude.add("/scripts")
        exclude.add("/linux")
        exclude.add("/windows")
        exclude.add("/windows/cfg_examples")
        exclude.add("/windows/mrpe")
        exclude.add("/windows/mrpe")
        exclude.add("/windows/ohm")
        exclude.add("/windows/plugins")
        return exclude


class ModeDownloadAgentsWindows(ABCModeDownloadAgents):
    @classmethod
    @override
    def name(cls) -> str:
        return "download_agents_windows"

    @override
    def title(self) -> str:
        return _("Windows files")

    @override
    def _packed_agents(self) -> list[str]:
        return [str(agent.packed_agent_path_windows_msi())]

    @override
    def _walk_base_dirs(self) -> list[str]:
        return [
            str(cmk.utils.paths.agents_dir / "windows"),
            str(cmk.utils.paths.agents_dir / "robotmk/windows"),
        ]


class ModeDownloadAgentsLinux(ABCModeDownloadAgents):
    @classmethod
    @override
    def name(cls) -> str:
        return "download_agents_linux"

    @override
    def title(self) -> str:
        return _("Linux, Solaris, AIX files")

    @override
    def _packed_agents(self) -> list[str]:
        return [str(agent.packed_agent_path_linux_deb()), str(agent.packed_agent_path_linux_rpm())]

    @override
    def _walk_base_dirs(self) -> list[str]:
        return [str(cmk.utils.paths.agents_dir)]

    @override
    def _exclude_file_glob_patterns(self) -> list[str]:
        return [
            "*.hpux",
            "*.macosx",
            "*.freebsd",
            "*.openbsd",
            "*.netbsd",
            "*.openwrt",
            "*.openvms",
            "hpux_*",
            "*robotmk/windows*",
        ]

    @override
    def _exclude_paths(self) -> set[str]:
        exclude = super()._exclude_paths()
        exclude.add("/z_os")
        exclude.add("/sap")
        exclude.add("/windows")
        exclude.add("/windows/cfg_examples")
        exclude.add("/windows/mrpe")
        exclude.add("/windows/mrpe")
        exclude.add("/windows/ohm")
        exclude.add("/windows/plugins")
        return exclude


class PageDownloadAgentPlugin(Page):
    """Stream an agent plugin file that lives outside the statically served agents tree.

    Files grouped by plugin family (cmk/plugins/<family>/agents/) are not reachable
    through the "check_mk/agents" Apache alias, so ``ModeDownloadAgentsOther`` links
    them here. The requested path is validated against the passed set of plugin family
    agent directories before serving to prevent reading arbitrary files.

    Authentication is decided before the page is called, so serving the files shipped
    with the version without a login (as the Apache alias does) and the files of locally
    installed plugin families with one requires two instances, registered under a
    "noauth:" and a regular page name respectively.
    """

    def __init__(
        self,
        allowed_dirs: Sequence[Path],
        *,
        require_permission: bool,
    ) -> None:
        self.allowed_dirs: Final = [p.resolve() for p in allowed_dirs]
        self.require_permission: Final = require_permission

    @override
    def page(self, ctx: PageContext) -> None:
        if self.require_permission:
            user.need_permission("wato.download_agents")

        try:
            requested = Path(ctx.request.get_str_input_mandatory("path")).resolve(strict=True)
        except (MKUserError, OSError):
            raise MKUserError("path", _("The requested file does not exist."))

        if not (
            requested.is_file() and any(requested.is_relative_to(d) for d in self.allowed_dirs)
        ):
            raise MKUserError("path", _("The requested file is not available for download."))

        filename = requested.name
        if '"' in filename or "\\" in filename:
            raise MKUserError("path", _("Invalid file name."))

        response.set_content_type("application/octet-stream")
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.set_data(requested.read_bytes())
