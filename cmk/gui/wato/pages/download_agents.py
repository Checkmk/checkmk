#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Simple download page for the builtin agents and plugins"""

import abc
import fnmatch
import os
from typing import Collection, Iterator, List

import cmk.utils.paths
import cmk.utils.render

import cmk.gui.forms as forms
import cmk.gui.watolib.bakery as bakery
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.plugins.wato.utils import mode_registry, WatoMode
from cmk.gui.type_defs import PermissionName
from cmk.gui.utils import agent
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link


class ABCModeDownloadAgents(WatoMode):
    @classmethod
    def permissions(cls) -> Collection[PermissionName]:
        return ["download_agents"]

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
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
        if bakery.has_agent_bakery():
            yield PageMenuEntry(
                title=_("Windows, Linux, Solaris, AIX"),
                icon_name="agents",
                item=make_simple_link(folder_preserving_link([("mode", "agents")])),
            )

        if self.name() != "download_agents_windows":
            yield PageMenuEntry(
                title=_("Windows files"),
                icon_name="download_agents",
                item=make_simple_link(
                    folder_preserving_link([("mode", "download_agents_windows")])
                ),
            )

        if self.name() != "download_agents_linux":
            yield PageMenuEntry(
                title=_("Linux, Solaris, AIX files"),
                icon_name="download_agents",
                item=make_simple_link(folder_preserving_link([("mode", "download_agents_linux")])),
            )

        if self.name() != "download_agents":
            yield PageMenuEntry(
                title=_("Other operating systems"),
                icon_name="download_agents",
                item=make_simple_link(folder_preserving_link([("mode", "download_agents")])),
            )

    @abc.abstractmethod
    def _packed_agents(self) -> List[str]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _walk_base_dir(self):
        raise NotImplementedError()

    def _exclude_file_glob_patterns(self):
        return []

    def _exclude_paths(self):
        return set(
            [
                "/bakery",
                "/special",
                "/windows/baked_container.msi",
                "/windows/plugins/.gitattributes",
            ]
        )

    def page(self) -> None:
        html.open_div(class_="rulesets")

        packed = self._packed_agents()
        if packed:
            self._download_table(_("Packaged Agents"), packed)

        titles = {
            "": _("Agents"),
            "/plugins": _("Plugins"),
            "/cfg_examples": _("Example Configurations"),
            "/cfg_examples/systemd": _("Example configuration for systemd"),
            "/windows": _("Windows Agent"),
            "/windows/plugins": _("Plugins"),
            "/windows/mrpe": _("Scripts to integrate Nagios plugis"),
            "/windows/cfg_examples": _("Example Configurations"),
            "/windows/ohm": _("OpenHardwareMonitor (headless)"),
            "/z_os": _("z/OS"),
            "/sap": _("SAP R/3"),
        }

        banned_paths = self._exclude_paths()

        other_sections = []
        for root, _dirs, files in os.walk(self._walk_base_dir()):
            file_paths = []
            relpath = root.split("agents")[1]
            if relpath in banned_paths:
                continue

            title = titles.get(relpath, relpath)
            for filename in files:
                rel_file_path = relpath + "/" + filename
                if rel_file_path in banned_paths:
                    continue

                if self._exclude_by_pattern(rel_file_path):
                    continue

                path = root + "/" + filename
                if path not in packed and "deprecated" not in path:
                    file_paths.append(path)

            other_sections.append((title, file_paths))

        for title, file_paths in sorted(other_sections):
            useful_file_paths = [p for p in file_paths if not p.endswith("/CONTENTS")]
            if useful_file_paths:
                self._download_table(title, sorted(useful_file_paths))
        html.close_div()

    def _exclude_by_pattern(self, rel_file_path):
        for exclude_pattern in self._exclude_file_glob_patterns():
            if fnmatch.fnmatch(rel_file_path, exclude_pattern):
                return True
        return False

    def _download_table(self, title: str, paths: List[str]) -> None:
        forms.header(title)
        forms.container()
        for path in paths:
            os_path = path
            relpath = path.replace(cmk.utils.paths.agents_dir + "/", "")
            filename = path.split("/")[-1]

            file_size = os.stat(os_path).st_size

            # FIXME: Rename classes etc. to something generic
            html.open_div(class_="ruleset")
            html.open_div(style="width:300px;", class_="text")
            html.a(filename, href="agents/%s" % relpath, download=filename)
            html.span("." * 200, class_="dots")
            html.close_div()
            html.div(cmk.utils.render.fmt_bytes(file_size), style="width:60px;", class_="rulecount")
            html.close_div()
            html.close_div()
        forms.end()


@mode_registry.register
class ModeDownloadAgentsOther(ABCModeDownloadAgents):
    @classmethod
    def name(cls) -> str:
        return "download_agents"

    def title(self) -> str:
        return _("Other operating systems")

    def _packed_agents(self) -> List[str]:
        return []

    def _walk_base_dir(self):
        return cmk.utils.paths.agents_dir

    def _exclude_file_glob_patterns(self):
        return [
            "*.rpm",
            "*.deb",
            "*.aix",
            "*.linux",
            "*.solaris",
        ]

    def _exclude_paths(self):
        exclude = super()._exclude_paths()
        exclude.add("/cfg_examples/systemd")
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


@mode_registry.register
class ModeDownloadAgentsWindows(ABCModeDownloadAgents):
    @classmethod
    def name(cls) -> str:
        return "download_agents_windows"

    def title(self) -> str:
        return _("Windows files")

    def _packed_agents(self) -> List[str]:
        return [str(agent.packed_agent_path_windows_msi())]

    def _walk_base_dir(self):
        return cmk.utils.paths.agents_dir + "/windows"


@mode_registry.register
class ModeDownloadAgentsLinux(ABCModeDownloadAgents):
    @classmethod
    def name(cls) -> str:
        return "download_agents_linux"

    def title(self) -> str:
        return _("Linux, Solaris, AIX files")

    def _packed_agents(self) -> List[str]:
        return [str(agent.packed_agent_path_linux_deb()), str(agent.packed_agent_path_linux_rpm())]

    def _walk_base_dir(self):
        return cmk.utils.paths.agents_dir

    def _exclude_file_glob_patterns(self):
        return [
            "*.hpux",
            "*.macosx",
            "*.freebsd",
            "*.openbsd",
            "*.netbsd",
            "*.openwrt",
            "*.openvms",
            "hpux_*",
        ]

    def _exclude_paths(self):
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
