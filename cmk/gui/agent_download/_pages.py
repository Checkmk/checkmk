#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

"""Simple download page for the built-in agents and plugins"""

import abc
import fnmatch
import os
from collections.abc import Callable, Collection, Generator, Iterable, Iterator, Sequence
from dataclasses import dataclass
from functools import lru_cache
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
from cmk.gui.pages import Page, PageContext
from cmk.gui.type_defs import IconNames, PermissionName, StaticIcon
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.mode import WatoMode
from cmk.web.utils.urls import makeuri_contextless

from ._utils import (
    packed_agent_path_linux_deb,
    packed_agent_path_linux_rpm,
    packed_agent_path_windows_msi,
)

# Page names of the GUI handlers that stream agent plugin files which live outside
# the statically served share/check_mk/agents tree (e.g. cmk/plugins/<family>/agents/).
# Files shipped with the version are served without authentication, just like the files
# below the statically served tree. Files of locally installed plugins are not.
DOWNLOAD_AGENT_PLUGIN_PAGE = "download_agent_plugin"
DOWNLOAD_LOCAL_AGENT_PLUGIN_PAGE = "download_local_agent_plugin"


@dataclass(frozen=True)
class DownloadFile:
    """A single file offered for download.

    The link text is not always the file name: the same file can be shipped with the
    version and installed locally, in which case both are offered and have to be told
    apart.
    """

    path: str
    label: str


@dataclass(frozen=True)
class PluginFamilyDir:
    """One agent plugin directory of a plugin family (cmk.bakery.v2).

    These live under lib/python3/cmk/plugins/<family>/agents/ - i.e. outside the
    statically served share/check_mk/agents tree - so files found here must be
    downloaded through a GUI handler, not the Apache alias.
    """

    path: Path
    is_local: bool


@dataclass(frozen=True)
class PluginFamilyAgents:
    """The agent plugin directories belonging to one plugin family."""

    title: str
    dirs: Sequence[PluginFamilyDir]


@lru_cache  # This is based on python imports and thus never changes for a running process
def _plugin_family_agents() -> Sequence[PluginFamilyAgents]:
    """Discover the agent plugin directories of every plugin family.

    ``discover_families`` returns keys like ``cmk.plugins.oracle``; we use the
    last dotted component ("oracle") as a human readable section title ("Oracle")
    so that files of different families are not all lumped under one generic
    "Agents" header on the download page.

    A family can be found in more than one place: shipped with the version and
    installed below ``local/`` (e.g. via MKP). Both belong to the same family and
    hence to the same section of the download page, so the directories are grouped
    per family, the shipped one first. Only the local ones require a login to be
    downloaded.
    """
    return [
        PluginFamilyAgents(
            title=family.split(".")[-1].capitalize(),
            dirs=sorted(
                (
                    PluginFamilyDir(
                        path=Path(family_path, AGENT_PLUGINS_FOLDER),
                        is_local=Path(family_path).is_relative_to(cmk.utils.paths.local_root),
                    )
                    for family_path in family_paths
                ),
                key=lambda pf_dir: pf_dir.is_local,
            ),
        )
        for family, family_paths in sorted(discover_families(raise_errors=False).items())
    ]


def _local_agent_file_label(filename: str) -> str:
    """Link text for an agent file of a locally installed plugin family.

    Such a file is offered right next to the one of the same name shipped with the
    version, so mark which one it is - and that it is the only one whose download
    requires a login.
    """
    return _("%(filename)s (local, download requires login)") % {"filename": filename}


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
        "/windows/mrpe": _("Scripts to integrate Nagios plug-ins"),
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

    def _extra_sections(self) -> Iterable[tuple[str, list[DownloadFile]]]:
        """Sections that are not the result of walking the ``_walk_base_dirs``."""
        return []

    @override
    def page(self, config: Config) -> None:
        html.open_div(class_="rulesets")

        if packed := self._packed_agents():
            self._download_table(
                _("Packaged agents"), [DownloadFile(p, p.split("/")[-1]) for p in packed]
            )

        sections = [
            *(entry for base_dir in self._walk_base_dirs() for entry in self._walk_dir(base_dir)),
            *self._extra_sections(),
        ]
        for title, files in sorted(sections, key=lambda section: section[0]):
            if useful_files := [f for f in files if not f.path.endswith("/CONTENTS")]:
                self._download_table(title, useful_files)
        html.close_div()

    def _walk_dir(self, dir_path: str) -> Generator[tuple[str, list[DownloadFile]]]:
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

            yield (title, [DownloadFile(p, p.split("/")[-1]) for p in sorted(file_paths)])

    def _exclude_by_pattern(self, rel_file_path: str) -> bool:
        for exclude_pattern in self._exclude_file_glob_patterns():
            if fnmatch.fnmatch(rel_file_path, exclude_pattern):
                return True
        return False

    def _title_for_root(self, root: str, relpath: str) -> str:
        """Section title for the files found directly below ``root``."""
        return self._TITLES.get(relpath, relpath)

    def _download_table(self, title: str, files: Sequence[DownloadFile]) -> None:
        forms.header(title)
        forms.container()
        for file in files:
            filename = file.path.split("/")[-1]

            file_size = os.stat(file.path).st_size

            # FIXME: Rename classes etc. to something generic
            html.open_div(class_="ruleset")
            html.open_div(style="width:300px;", class_="text")
            html.a(file.label, href=download_href(file.path), download=filename)
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
        return [str(cmk.utils.paths.agents_dir)]

    @override
    def _extra_sections(self) -> Iterator[tuple[str, list[DownloadFile]]]:
        """One section per plugin family (cmk.bakery.v2).

        The agent plugin files of a family live in their own agents directory outside
        the statically served share tree, so they are not found by walking it. They are
        not organized in sub directories either, which is why they do not go through
        ``_walk_dir`` (and its path based exclusions) at all.

        It would be nice to support some sort of meta data file per family, providing
        maybe
        * general information
        * a (allow/deny) list of the files that should be exposed for download
        * description / title for those.
        """
        for family in _plugin_family_agents():
            found = [
                (path.name, agent_dir.is_local, path)
                for agent_dir in family.dirs
                for path in self._plugin_family_agent_files(agent_dir.path)
            ]
            if found:
                # Sorting by (name, is_local) shows the locally installed version of a
                # file right below the one shipped with the version.
                yield (
                    family.title,
                    [
                        DownloadFile(str(path), _local_agent_file_label(name) if is_local else name)
                        for name, is_local, path in sorted(found)
                    ],
                )

    def _plugin_family_agent_files(self, agents_dir: Path) -> Iterator[Path]:
        try:
            candidates = agents_dir.iterdir()
        except OSError:
            return

        for path in candidates:
            if not path.is_file():
                continue
            if self._exclude_by_pattern(f"/{path.name}"):
                continue
            if "deprecated" in path.name:
                continue
            yield path

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
        return [str(packed_agent_path_windows_msi())]

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
        return [str(packed_agent_path_linux_deb()), str(packed_agent_path_linux_rpm())]

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
        except MKUserError, OSError:
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
