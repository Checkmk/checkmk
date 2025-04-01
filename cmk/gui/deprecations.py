#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import auto, Enum
from pathlib import Path
from typing import Literal

from livestatus import SiteConfigurations, SiteId

from cmk.ccc import store
from cmk.ccc.site import omd_site
from cmk.ccc.version import __version__, Version

from cmk.utils import paths
from cmk.utils.html import replace_state_markers
from cmk.utils.user import UserId

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.config import active_config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.message import get_gui_messages, Message, message_gui, MessageText
from cmk.gui.site_config import get_site_config, is_wato_slave_site
from cmk.gui.sites import states
from cmk.gui.type_defs import Users
from cmk.gui.userdb import load_users
from cmk.gui.utils import gen_id
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import user_may
from cmk.gui.watolib.analyze_configuration import ACResultState, ACTestResult, perform_tests

from cmk.discover_plugins import addons_plugins_local_path, plugins_local_path
from cmk.mkp_tool import get_stored_manifests, Manifest, PackageStore, PathConfig


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


def _try_rel_path(site_id: SiteId, abs_path: Path) -> Path:
    try:
        return abs_path.relative_to(Path("/omd/sites", site_id))
    except ValueError:
        # Not a subpath, should not happen
        return abs_path


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


class _NotificationCategory(Enum):
    manage_mkps = auto()
    rule_sets = auto()
    log = auto()  # fallback


@dataclass(frozen=True)
class _ACTestResultProblem:
    ident: str
    type: Literal["mkp", "file", "unsorted"]
    notification_category: _NotificationCategory
    _ac_test_results: dict[SiteId, list[ACTestResult]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert self.ident

    def add_ac_test_result(self, site_id: SiteId, ac_test_result: ACTestResult) -> None:
        self._ac_test_results.setdefault(site_id, []).append(ac_test_result)

    def text(self) -> str:
        words = []
        for state, text in sorted(
            set((r.state, r.text) for rs in self._ac_test_results.values() for r in rs)
        ):
            match state:
                case ACResultState.CRIT:
                    words.append(f"[CRIT] Result: {text}")
                case ACResultState.WARN:
                    words.append(f"[WARN] Result: {text}")
                case _:
                    words.append(f"Result: {text}")

        return ", ".join(words)

    def html(self, version: str) -> HTML:
        if not self._ac_test_results:
            return HTML("", escape=False)

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
                return HTML("", escape=False)

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
                title = self.ident
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

        table_content = HTML("", escape=False)
        for idx, (state, text) in enumerate(
            sorted(set((r.state, r.text) for rs in self._ac_test_results.values() for r in rs))
        ):
            match state:
                case ACResultState.CRIT:
                    state_td = HTMLWriter.render_td(
                        HTML(replace_state_markers("(!!)"), escape=False),
                        class_="state svcstate",
                    )
                case ACResultState.WARN:
                    state_td = HTMLWriter.render_td(
                        HTML(replace_state_markers("(!)"), escape=False),
                        class_="state svcstate",
                    )
                case _:
                    state_td = HTMLWriter.render_td("")

            table_content += HTMLWriter.render_tr(
                HTMLWriter.render_td(text) + state_td,
                class_="even0" if idx % 2 == 0 else "odd0",
            )

        html_code += HTMLWriter.render_table(table_content, class_="data table")
        return html_code


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
                        _ACTestResultProblem(
                            manifest.name,
                            "mkp",
                            _NotificationCategory.manage_mkps,
                        ),
                    )
                else:
                    problem = problem_by_ident.setdefault(
                        str(path),
                        _ACTestResultProblem(
                            str(path),
                            "file",
                            _NotificationCategory.manage_mkps,
                        ),
                    )

            else:
                match ac_test_result.test_id:
                    case (
                        "ACTestUnknownCheckParameterRuleSets"
                        | "ACTestDeprecatedV1CheckPlugins"
                        | "ACTestDeprecatedCheckPlugins"
                        | "ACTestDeprecatedInventoryPlugins"
                        | "ACTestDeprecatedCheckManpages"
                        | "ACTestDeprecatedGUIExtensions"
                        | "ACTestDeprecatedLegacyGUIExtensions"
                        | "ACTestDeprecatedPNPTemplates"
                    ):
                        notification_category = _NotificationCategory.manage_mkps
                    case "ACTestDeprecatedRuleSets":
                        notification_category = _NotificationCategory.rule_sets
                    case _:
                        notification_category = _NotificationCategory.log

                problem = problem_by_ident.setdefault(
                    ac_test_result.text,
                    _ACTestResultProblem(
                        ac_test_result.text,
                        "unsorted",
                        notification_category,
                    ),
                )

            problem.add_ac_test_result(site_id, ac_test_result)

    return list(problem_by_ident.values())


@dataclass(frozen=True)
class _NotifiableUser:
    user_id: UserId
    notification_categories: Sequence[_NotificationCategory]
    sent_messages: Sequence[str]


def _filter_notifiable_users(users: Users) -> Iterator[_NotifiableUser]:
    for user_id, user_spec in users.items():
        notification_categories = []
        if user_may(user_id, "wato.manage_mkps"):
            notification_categories.append(_NotificationCategory.manage_mkps)
        if "admin" in user_spec["roles"] and user_may(user_id, "wato.rulesets"):
            notification_categories.append(_NotificationCategory.rule_sets)
        if notification_categories:
            yield _NotifiableUser(
                user_id,
                notification_categories,
                [m["text"]["content"] for m in get_gui_messages(user_id)],
            )


@dataclass(frozen=True)
class _ProblemToSend:
    users: Sequence[_NotifiableUser]
    content: str


def _find_problems_to_send(
    version: str, problems: Sequence[_ACTestResultProblem], users: Sequence[_NotifiableUser]
) -> Iterator[_ProblemToSend | str]:
    for problem in problems:
        if not (rendered := str(problem.html(version))):
            continue

        if notifiable_users := [
            u for u in users if problem.notification_category in u.notification_categories
        ]:
            yield _ProblemToSend(notifiable_users, rendered)

        else:
            yield (
                "Analyze configuration problem notification could not be sent to any user"
                f" (Test: {problem.ident}, Result: {problem.text()!r})"
            )


def execute_deprecation_tests_and_notify_users() -> None:
    if is_wato_slave_site():
        return

    marker_file_store = _MarkerFileStore(Path(paths.var_dir) / "deprecations")

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
                    {
                        site_id: get_site_config(active_config, site_id)
                        for site_id in site_versions_by_site_id
                    }
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

    now = int(time.time())
    for problem_to_send in _find_problems_to_send(
        Version.from_str(__version__).version_base,
        _find_ac_test_result_problems(not_ok_ac_test_results, manifests_by_path),
        list(_filter_notifiable_users(load_users())),
    ):
        match problem_to_send:
            case _ProblemToSend():
                for user in problem_to_send.users:
                    if problem_to_send.content in user.sent_messages:
                        continue

                    message_gui(
                        user.user_id,
                        Message(
                            dest=("list", [user.user_id]),
                            methods=["gui_hint"],
                            text=MessageText(
                                content_type="html",
                                content=problem_to_send.content,
                            ),
                            valid_till=None,
                            id=gen_id(),
                            time=now,
                            security=False,
                            acknowledged=False,
                        ),
                    )

            case str():
                logger.error(problem_to_send)


def register(cron_job_registry: CronJobRegistry) -> None:
    cron_job_registry.register(
        CronJob(
            name="execute_deprecation_tests_and_notify_users",
            callable=execute_deprecation_tests_and_notify_users,
            interval=datetime.timedelta(days=1),
        )
    )
