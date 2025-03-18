#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from livestatus import SiteConfigurations, SiteId

from cmk.utils import paths, store
from cmk.utils.html import replace_state_markers
from cmk.utils.site import omd_site
from cmk.utils.user import UserId
from cmk.utils.version import __version__, Version

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.config import active_config
from cmk.gui.cron import register_job
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.message import get_gui_messages, Message, message_gui, MessageText
from cmk.gui.site_config import get_site_config, is_wato_slave_site
from cmk.gui.sites import states
from cmk.gui.userdb import load_users
from cmk.gui.utils import gen_id
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import user_may
from cmk.gui.watolib.analyze_configuration import ACResultState, ACTestResult, perform_tests

from cmk.discover_plugins import addons_plugins_local_path, plugins_local_path
from cmk.mkp_tool import get_stored_manifests, Manifest, PackageStore, PathConfig


@dataclass(frozen=True, kw_only=True)
class Paths:
    markers: Path
    last_run: Path


def create_paths(omd_root: Path) -> Paths:
    markers = omd_root / Path("var/check_mk/deprecations")
    return Paths(markers=markers, last_run=markers / ".last_run")


@dataclass(frozen=True)
class _MarkerFileStore:
    _folder: Path

    def save(
        self, site_id: SiteId, site_version: str, ac_test_results: Sequence[ACTestResult]
    ) -> None:
        marker_file = self._folder / str(site_id) / site_version
        store.makedirs(marker_file.parent)
        store.save_text_to_file(marker_file, json.dumps([repr(r) for r in ac_test_results]))

    def cleanup_site_dir(self, site_id: SiteId) -> None:
        for filepath, _mtime in sorted(
            [
                (marker_file, marker_file.stat().st_mtime)
                for marker_file in list((self._folder / site_id).iterdir())
            ],
            key=lambda t: t[1],
            reverse=True,
        )[5:]:
            filepath.unlink(missing_ok=True)

    def cleanup_empty_dirs(self) -> None:
        for path in self._folder.iterdir():
            if path.is_dir() and not list(path.iterdir()):
                try:
                    path.rmdir()
                except OSError:
                    logger.error("Cannot remove %r", path)


def _filter_non_ok_ac_test_results(
    ac_test_results_by_site_id: Mapping[SiteId, Sequence[ACTestResult]],
) -> Mapping[SiteId, Sequence[ACTestResult]]:
    return {
        s: not_ok_rs
        for s, rs in ac_test_results_by_site_id.items()
        if (not_ok_rs := [r for r in rs if r.state is not ACResultState.OK])
    }


def _filter_extension_managing_users(user_ids: Sequence[UserId]) -> Sequence[UserId]:
    return [u for u in user_ids if user_may(u, "wato.manage_mkps")]


def _make_path_config() -> PathConfig | None:
    local_path = plugins_local_path()
    addons_path = addons_plugins_local_path()
    if local_path is None:
        return None
    if addons_path is None:
        return None
    return PathConfig(
        cmk_plugins_dir=local_path,
        cmk_addons_plugins_dir=addons_path,
        agent_based_plugins_dir=paths.local_agent_based_plugins_dir,
        agents_dir=paths.local_agents_dir,
        alert_handlers_dir=paths.local_alert_handlers_dir,
        bin_dir=paths.local_bin_dir,
        check_manpages_dir=paths.local_legacy_check_manpages_dir,
        checks_dir=paths.local_checks_dir,
        doc_dir=paths.local_doc_dir,
        gui_plugins_dir=paths.local_gui_plugins_dir,
        installed_packages_dir=paths.installed_packages_dir,
        inventory_dir=paths.local_inventory_dir,
        lib_dir=paths.local_lib_dir,
        locale_dir=paths.local_locale_dir,
        local_root=paths.local_root,
        mib_dir=paths.local_mib_dir,
        mkp_rule_pack_dir=ec.mkp_rule_pack_dir(),
        notifications_dir=paths.local_notifications_dir,
        pnp_templates_dir=paths.local_pnp_templates_dir,
        manifests_dir=paths.tmp_dir,
        web_dir=paths.local_web_dir,
    )


def _group_manifests_by_rel_path(
    site_id: SiteId, path_config: PathConfig, manifests: Sequence[Manifest]
) -> Mapping[Path, Manifest]:
    manifests_by_path: dict[Path, Manifest] = {}
    for manifest in manifests:
        for part, files in manifest.files.items():
            for file in files:
                manifests_by_path[
                    _try_rel_path(site_id, Path(path_config.get_path(part)) / file)
                ] = manifest
    return manifests_by_path


def _try_rel_path(site_id: SiteId, abs_path: Path) -> Path:
    try:
        return abs_path.relative_to(Path("/omd/sites", site_id))
    except ValueError:
        # Not a subpath, should not happen
        return abs_path


@dataclass(frozen=True)
class _ACTestResultProblem:
    ident: str
    type: Literal["mkp", "file", "unsorted"]
    _ac_test_results: dict[SiteId, list[ACTestResult]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert self.ident

    def add_ac_test_result(self, site_id: SiteId, ac_test_result: ACTestResult) -> None:
        self._ac_test_results.setdefault(site_id, []).append(ac_test_result)

    def render(self, version: str) -> str:
        if not self._ac_test_results:
            return ""

        match ACResultState.worst(r.state for rs in self._ac_test_results.values() for r in rs):
            case ACResultState.CRIT:
                error = _("This does not work in Checkmk %s.") % version
            case ACResultState.WARN:
                error = (
                    _(
                        "This may partially work in Checkmk %s but will stop working from the"
                        " next major version onwards."
                    )
                    % version
                )
            case _:
                return ""

        match self.type:
            case "mkp":
                title = _("Deprecated extension package: %s") % self.ident
                info = (
                    _(
                        "The extension package uses APIs which are deprecated or removed in"
                        " Checkmk %s so that this extension will not work anymore once you upgrade"
                        " your site to next major version."
                    )
                    % version
                )
                recommendation = _(
                    "We highly recommend solving this issue already in your installation by"
                    " updating the extension package. Otherwise the extension package will be"
                    " deactivated after an upgrade."
                )
            case "file":
                title = _("Deprecated plug-in: %s") % self.ident
                info = (
                    _(
                        "The plug-in uses APIs which are deprecated or removed in"
                        " Checkmk %s, so that this extension will not work anymore once you upgrade"
                        " your site to next major version."
                    )
                    % version
                )
                recommendation = _(
                    "We highly recommend solving this issue already in your installation either"
                    " by migrating or removing this plug-in."
                )
            case "unsorted":
                title = _("Unsorted")
                info = ""
                recommendation = _(
                    "We highly recommend solving this issue already in your installation."
                )

        html_code = HTMLWriter.render_h2(title)
        html_code += HTMLWriter.render_div(error, class_="error")
        if info:
            html_code += HTMLWriter.render_p(info)
        html_code += HTMLWriter.render_p(recommendation)
        html_code += HTMLWriter.render_p(
            _("Affected sites: %s") % ", ".join(sorted(self._ac_test_results))
        )
        html_code += HTMLWriter.render_p(_("Details:"))

        table_content = HTML()
        for idx, (state, text, rel_path) in enumerate(
            sorted(
                set(
                    (
                        r.state,
                        r.text,
                        _try_rel_path(s, r.path) if r.path else None,
                    )
                    for s, rs in self._ac_test_results.items()
                    for r in rs
                )
            )
        ):
            match state:
                case ACResultState.CRIT:
                    state_td = HTMLWriter.render_td(
                        HTML(replace_state_markers("(!!)")),
                        rowspan="2",
                        class_="state svcstate",
                    )
                case ACResultState.WARN:
                    state_td = HTMLWriter.render_td(
                        HTML(replace_state_markers("(!)")),
                        rowspan="2",
                        class_="state svcstate",
                    )
                case _:
                    state_td = HTMLWriter.render_td("")

            class_ = "even0" if idx % 2 == 0 else "odd0"
            table_content += HTMLWriter.render_tr(
                HTMLWriter.render_td(text) + state_td,
                class_=class_,
            )
            table_content += HTMLWriter.render_tr(
                (
                    HTMLWriter.render_td(f"File: {rel_path}")
                    if rel_path
                    else HTMLWriter.render_td("")
                ),
                class_=class_,
            )

        html_code += HTMLWriter.render_table(table_content, class_="data table")
        return str(html_code)


def _find_ac_test_result_problems(
    not_ok_ac_test_results: Mapping[SiteId, Sequence[ACTestResult]],
    manifests_by_path: Mapping[Path, Manifest],
) -> Sequence[_ACTestResultProblem]:
    problem_by_ident: dict[str, _ACTestResultProblem] = {}
    for site_id, ac_test_results in not_ok_ac_test_results.items():
        for ac_test_result in ac_test_results:
            if ac_test_result.path:
                path = _try_rel_path(site_id, ac_test_result.path)

                if manifest := manifests_by_path.get(path):
                    problem = problem_by_ident.setdefault(
                        manifest.name,
                        _ACTestResultProblem(manifest.name, "mkp"),
                    )
                else:
                    problem = problem_by_ident.setdefault(
                        str(path),
                        _ACTestResultProblem(str(path), "file"),
                    )

            else:
                problem = problem_by_ident.setdefault(
                    "unsorted",
                    _ACTestResultProblem("unsorted", "unsorted"),
                )

            problem.add_ac_test_result(site_id, ac_test_result)

    return list(problem_by_ident.values())


def execute_deprecation_tests_and_notify_users() -> None:
    deprecation_paths = create_paths(paths.omd_root)
    deprecation_paths.markers.mkdir(parents=True, exist_ok=True)
    now = time.time()

    try:
        last_run_ts = deprecation_paths.last_run.stat().st_mtime
    except FileNotFoundError:
        last_run_ts = 0

    if (now - last_run_ts) < 86400:
        return

    if is_wato_slave_site():
        return

    deprecation_paths.last_run.touch()

    marker_file_store = _MarkerFileStore(deprecation_paths.markers)

    site_versions_by_site_id = {
        site_id: site_version
        for site_id, site_state in states().items()
        if (site_version := site_state.get("program_version"))
    }

    if not (
        not_ok_ac_test_results := _filter_non_ok_ac_test_results(
            perform_tests(
                logger,
                active_config,
                request,
                SiteConfigurations(
                    {site_id: get_site_config(site_id) for site_id in site_versions_by_site_id}
                ),
                categories=["deprecations"],
            )
        )
    ):
        return

    for site_id, ac_test_results in not_ok_ac_test_results.items():
        marker_file_store.save(site_id, site_versions_by_site_id[site_id], ac_test_results)
        marker_file_store.cleanup_site_dir(site_id)

    marker_file_store.cleanup_empty_dirs()

    manifests_by_path = (
        _group_manifests_by_rel_path(
            omd_site(),
            path_config,
            get_stored_manifests(
                PackageStore(
                    shipped_dir=paths.optional_packages_dir,
                    local_dir=paths.local_optional_packages_dir,
                    enabled_dir=paths.local_enabled_packages_dir,
                )
            ).local,
        )
        if (path_config := _make_path_config())
        else {}
    )

    ac_test_results_messages = [
        r
        for p in _find_ac_test_result_problems(not_ok_ac_test_results, manifests_by_path)
        if (r := p.render(Version.from_str(__version__).version_base))
    ]

    now = int(time.time())
    for user_id in _filter_extension_managing_users(list(load_users())):
        sent_messages = [m["text"]["content"] for m in get_gui_messages(user_id)]
        for ac_test_results_message in ac_test_results_messages:
            if ac_test_results_message in sent_messages:
                continue
            message_gui(
                user_id,
                Message(
                    dest=("list", [user_id]),
                    methods=["gui_hint"],
                    text=MessageText(content_type="html", content=ac_test_results_message),
                    valid_till=None,
                    id=gen_id(),
                    time=now,
                ),
            )


def register() -> None:
    register_job(execute_deprecation_tests_and_notify_users)
