#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from livestatus import SiteConfigurations, SiteId

from cmk.ccc import store

from cmk.utils import paths
from cmk.utils.user import UserId

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.config import active_config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.http import request
from cmk.gui.log import logger
from cmk.gui.message import Message, message_gui
from cmk.gui.site_config import get_site_config, is_wato_slave_site
from cmk.gui.sites import states
from cmk.gui.userdb import load_users
from cmk.gui.utils import gen_id
from cmk.gui.utils.roles import user_may
from cmk.gui.watolib.analyze_configuration import ACResultState, ACTestResult, perform_tests

from cmk.discover_plugins import addons_plugins_local_path, plugins_local_path
from cmk.mkp_tool import get_stored_manifests, Manifest, PackageStore, PathConfig


@dataclass(frozen=True)
class _MarkerFileStore:
    folder: Path

    def marker_file(self, site_id: SiteId, site_version: str) -> Path:
        return self.folder / str(site_id) / site_version

    def save(
        self, site_id: SiteId, site_version: str, ac_test_results: Sequence[ACTestResult]
    ) -> None:
        marker_file = self.marker_file(site_id, site_version)
        store.makedirs(marker_file.parent)
        store.save_text_to_file(marker_file, json.dumps([repr(r) for r in ac_test_results]))

    def cleanup_site_dir(self, site_id: SiteId) -> None:
        for filepath, _mtime in sorted(
            [
                (marker_file, marker_file.stat().st_mtime)
                for marker_file in list((self.folder / site_id).iterdir())
            ],
            key=lambda t: t[1],
            reverse=True,
        )[5:]:
            filepath.unlink(missing_ok=True)

    def cleanup_empty_dirs(self) -> None:
        for path in self.folder.iterdir():
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


def _group_manifests_by_path(
    path_config: PathConfig, manifests: Sequence[Manifest]
) -> Mapping[Path, Manifest]:
    manifests_by_path: dict[Path, Manifest] = {}
    for manifest in manifests:
        for part, files in manifest.files.items():
            for file in files:
                manifests_by_path[Path(path_config.get_path(part)).resolve() / file] = manifest
    return manifests_by_path


def _find_manifest(
    manifests_by_path: Mapping[Path, Manifest], ac_test_result_path: Path
) -> Manifest | None:
    for path, manifest in manifests_by_path.items():
        if str(ac_test_result_path.resolve()).endswith(str(path)):
            return manifest
    return None


@dataclass(frozen=True)
class _ACTestResultProblem:
    ident: str
    title: str
    _descriptions: list[str] = field(default_factory=list)
    _site_ids: set[SiteId] = field(default_factory=set)

    def __post_init__(self) -> None:
        assert self.ident
        assert self.title

    @property
    def descriptions(self) -> Sequence[str]:
        return self._descriptions

    def add_description(self, description: str) -> None:
        self._descriptions.append(description)

    @property
    def site_ids(self) -> Sequence[SiteId]:
        return sorted(self._site_ids)

    def add_site_id(self, site_id: SiteId) -> None:
        self._site_ids.add(site_id)

    def __repr__(self) -> str:
        return (
            f"{self.title}, sites: {', '.join(self.site_ids)}:<br>{',<br>'.join(self.descriptions)}"
        )


def _find_ac_test_result_problems(
    not_ok_ac_test_results: Mapping[SiteId, Sequence[ACTestResult]],
    manifests_by_path: Mapping[Path, Manifest],
) -> Sequence[_ACTestResultProblem]:
    problem_by_ident: dict[str, _ACTestResultProblem] = {}
    for site_id, ac_test_results in not_ok_ac_test_results.items():
        for ac_test_result in ac_test_results:
            if ac_test_result.path:
                if manifest := _find_manifest(manifests_by_path, ac_test_result.path):
                    problem = problem_by_ident.setdefault(
                        manifest.name,
                        _ACTestResultProblem(manifest.name, f"MKP {manifest.name}"),
                    )
                else:
                    problem = problem_by_ident.setdefault(
                        "unpackaged_files",
                        _ACTestResultProblem("unpackaged_files", "Unpackaged files"),
                    )
                problem.add_description(f"{ac_test_result.text} (file: {ac_test_result.path})")
            else:
                problem = problem_by_ident.setdefault(
                    "unsorted",
                    _ACTestResultProblem("unsorted", "Unsorted"),
                )
                problem.add_description(ac_test_result.text)
            problem.add_site_id(site_id)

    return list(problem_by_ident.values())


def _format_ac_test_result_problems(ac_test_result_problems: Sequence[_ACTestResultProblem]) -> str:
    return "<br><br>".join([repr(p) for p in ac_test_result_problems])


def execute_deprecation_tests_and_notify_users() -> None:
    if is_wato_slave_site():
        return

    marker_file_store = _MarkerFileStore(Path(paths.var_dir) / "deprecations")

    site_versions_by_site_id = {
        site_id: site_version
        for site_id, site_state in states().items()
        if (
            (site_version := site_state.get("program_version"))
            and not (marker_file_store.marker_file(site_id, site_version)).exists()
        )
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

    ac_test_results_message = _format_ac_test_result_problems(
        _find_ac_test_result_problems(
            not_ok_ac_test_results,
            (
                _group_manifests_by_path(
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
            ),
        )
    )

    now = int(time.time())
    for user_id in _filter_extension_managing_users(list(load_users())):
        message_gui(
            user_id,
            Message(
                dest=("list", [user_id]),
                methods=["gui_hint"],
                text=ac_test_results_message,
                id=gen_id(),
                time=now,
                security=False,
                acknowledged=False,
            ),
        )


def register(cron_job_registry: CronJobRegistry) -> None:
    cron_job_registry.register(
        CronJob(
            name="execute_deprecation_tests_and_notify_users",
            callable=execute_deprecation_tests_and_notify_users,
            interval=datetime.timedelta(days=1),
        )
    )
