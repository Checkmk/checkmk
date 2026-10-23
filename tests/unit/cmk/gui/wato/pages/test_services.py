#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from collections.abc import Generator, Mapping
from functools import partial

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.checkengine.discovery import CheckPreviewEntry
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.rule_specs.legacy_converter import convert_to_legacy_valuespec
from cmk.gui.wato.pages.services import DiscoveryPageRenderer
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree, Host
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.gui.watolib.rulespec_groups import RulespecGroupCheckParametersApplications
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithoutItem,
    FormSpecDefinition,
    Rulespec,
)
from cmk.gui.watolib.services import (
    DiscoveryAction,
    DiscoveryOptions,
    DiscoveryResult,
    DiscoveryState,
)
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, Integer


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


def _changed_entry() -> CheckPreviewEntry:
    return CheckPreviewEntry(
        check_source=DiscoveryState.CHANGED,
        check_plugin_name="cpu_loads",
        ruleset_name="cpu_load",
        discovery_ruleset_name=None,
        item=None,
        old_discovered_parameters={},
        new_discovered_parameters={},
        effective_parameters={},
        description="CPU load",
        state=0,
        output="",
        metrics=[],
        old_labels={},
        new_labels={},
        found_on_nodes=[],
    )


def _discovery_options() -> DiscoveryOptions:
    return DiscoveryOptions(
        action=DiscoveryAction.NONE,
        show_checkboxes=False,
        show_parameters=False,
        show_discovered_labels=False,
        show_plugin_names=False,
        ignore_errors=True,
    )


class TestDiscoveryPageRendererFolder:
    """The service discovery action menu must preserve the host's folder (CMK-35216).

    Hosts living in a subfolder used to trigger "The given host does not exist." when
    clicking any action menu entry, because the AJAX popup did not carry the folder.
    """

    @pytest.fixture
    def sub_host(self, tree: FolderTree) -> Generator[Host]:
        root_folder = tree.root_folder()
        sub = root_folder.create_subfolder(
            name="sub",
            title="",
            attributes={},
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
            acting_user=LoggedInSuperUser(),
        )
        sub.create_hosts(
            [(HostName("sub_host"), {}, None)],
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
            acting_user=LoggedInSuperUser(),
        )
        yield sub.load_host(HostName("sub_host"))
        self._cleanup_fs(root_folder)

    def _cleanup_fs(self, root_folder: Folder) -> None:
        shutil.rmtree(root_folder.filesystem_path(), ignore_errors=True)
        os.makedirs(root_folder.filesystem_path())

    def test_action_menu_url_vars_carry_the_hosts_folder(self, sub_host: Host) -> None:
        renderer = DiscoveryPageRenderer(host=sub_host, options=_discovery_options(), rulespecs={})

        url_vars = renderer._action_menu_url_vars("checkbox_name", _changed_entry())  # noqa: SLF001

        assert ("folder", "sub") in url_vars
        assert ("hostname", "sub_host") in url_vars

    @pytest.mark.usefixtures("request_context")
    def test_link_builders_point_to_the_hosts_folder(self, sub_host: Host) -> None:
        rulesets_link = DiscoveryPageRenderer.rulesets_button_link(
            sub_host.folder(), "CPU load", "sub_host"
        )
        assert "folder=sub" in rulesets_link
        assert "mode=object_parameters" in rulesets_link

        check_params_link = DiscoveryPageRenderer.check_parameters_button_link(
            sub_host.folder(), _changed_entry(), "sub_host"
        )
        assert check_params_link is not None
        assert "folder=sub" in check_params_link


_RULESET_NAME = "some_check_group"


def _rulespec_without_valuespec() -> Rulespec:
    form_spec = TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=Dictionary(
            elements={"levels": DictElement(parameter_form=Integer(title=Title("Levels")))}
        ),
        from_disk=lambda value: value,
        to_disk=lambda value: value,
    )
    return CheckParameterRulespecWithoutItem(
        check_group_name=_RULESET_NAME,
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=partial(convert_to_legacy_valuespec, form_spec, lambda s: s),
        create_manual_check=False,
        form_spec_definition=FormSpecDefinition(lambda: form_spec, None),
    )


def _entry(effective_parameters: Mapping[str, object]) -> CheckPreviewEntry:
    return CheckPreviewEntry(
        check_source=DiscoveryState.UNDECIDED,
        check_plugin_name="some_plugin",
        ruleset_name=_RULESET_NAME,
        discovery_ruleset_name=None,
        item=None,
        old_discovered_parameters={},
        new_discovered_parameters={},
        effective_parameters=effective_parameters,
        description="Some service",
        state=0,
        output="",
        metrics=[],
        old_labels={},
        new_labels={},
        found_on_nodes=[],
    )


def _discovery_result(entry: CheckPreviewEntry) -> DiscoveryResult:
    return DiscoveryResult(
        job_status={"is_active": False},
        check_table_created=0,
        check_table=[entry],
        nodes_check_table={},
        host_labels={},
        new_labels={},
        vanished_labels={},
        changed_labels={},
        labels_by_host={},
        sources=[],
        config_warnings=[],
    )


@pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")
class TestDiscoveryPageRendererCheckParameters:
    @pytest.fixture
    def host(self, tree: FolderTree) -> Generator[Host]:
        root_folder = tree.root_folder()
        root_folder.create_hosts(
            [(HostName("host"), {}, None)],
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
            acting_user=LoggedInSuperUser(),
        )
        yield root_folder.load_host(HostName("host"))
        shutil.rmtree(root_folder.filesystem_path(), ignore_errors=True)
        os.makedirs(root_folder.filesystem_path())

    def _render(self, host: Host, effective_parameters: Mapping[str, object]) -> str:
        renderer = DiscoveryPageRenderer(
            host=host,
            options=_discovery_options()._replace(show_parameters=True),
            rulespecs={
                RuleGroup.CheckgroupParameters(_RULESET_NAME): _rulespec_without_valuespec()
            },
        )
        return renderer.render(
            _discovery_result(_entry(effective_parameters)),
            update_services=[],
            changed_entry=None,
            debug=False,
            escape_plugin_output=True,
        )

    def test_parameters_of_a_ruleset_without_valuespec_are_rendered(self, host: Host) -> None:
        page = self._render(host, {"levels": 42})

        assert "Invalid check parameter" not in page
        assert "cmk-form-spec" in page

    def test_invalid_parameters_of_a_ruleset_without_valuespec_name_the_key(
        self, host: Host
    ) -> None:
        page = self._render(host, {"levels": "42"})

        assert "Invalid check parameter</b>: levels:" in page
