#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import replace

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site
from cmk.gui import login
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.quick_setup.config_setups.kubernetes.helm import MonitoringSettings
from cmk.gui.quick_setup.config_setups.kubernetes.save import save_configuration
from cmk.gui.quick_setup.config_setups.kubernetes.settings import (
    CommonSettings,
    PullSettings,
    PushSettings,
    Settings,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.configuration_bundle_store import BundleId, ConfigBundleStore
from cmk.gui.watolib.configuration_bundles import (
    BundleReferences,
    identify_single_bundle_references,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.passwords import load_passwords
from cmk.gui.watolib.pending_changes import (
    ChangeEvent,
    ChangeHook,
    NoopPendingChangesStore,
    PendingChanges,
)
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP

pytestmark = pytest.mark.usefixtures("with_admin_login", "mock_password_file_regeneration")


@pytest.fixture
def settings() -> PullSettings:
    return PullSettings(
        common=CommonSettings(
            bundle_id=BundleId("kubernetes_config_1"),
            release_name="kubernetes-config-1",
            namespace="monitoring",
            monitoring=MonitoringSettings(
                cluster_name="production", host_name="legacy", host_kinds=frozenset({"nodes"})
            ),
            host_path="",
            site_id=omd_site(),
        ),
        shared_secret="deployed-secret",
        base_url="https://agent:30050",
    )


def _save(settings: Settings, *, hooks: Sequence[ChangeHook] = ()) -> BundleReferences:
    save_configuration(
        settings,
        tree=folder_tree(),
        acting_user=user,
        user_permissions=UserPermissions.from_config(active_config, permission_registry),
        pending_changes=PendingChanges(
            activation_sites=active_config.sites,
            local_site=omd_site(),
            acting_user=user.id,
            store=NoopPendingChangesStore(),
            hooks=hooks,
        ),
        pprint_value=False,
        debug=False,
    )
    return identify_single_bundle_references(
        folder_tree(),
        settings.common.bundle_id,
        acting_user=user,
        program_id=PROGRAM_ID_QUICK_SETUP,
    )


def test_pull_saves_host_rule_and_the_deployed_password(settings: PullSettings) -> None:
    bundle = _save(settings)

    assert bundle.hosts and bundle.rules and bundle.passwords
    assert len(bundle.hosts) == len(bundle.rules) == len(bundle.passwords) == 1
    assert bundle.hosts[0].name() == "legacy"
    assert bundle.hosts[0].attributes["tag_agent"] == "special-agents"
    password_id, password = bundle.passwords[0]
    assert password["password"] == "deployed-secret"
    assert password["owned_by"] == user.id
    assert bundle.rules[0].value == {
        "url": "https://agent:30050",
        "shared_secret": ("cmk_postprocessed", "stored_password", (password_id, "")),
        "verify_cert": True,
    }


def test_push_saves_a_push_host_without_pull_rule_or_password(settings: PullSettings) -> None:
    bundle = _save(PushSettings(common=settings.common))

    assert bundle.hosts and len(bundle.hosts) == 1
    assert bundle.hosts[0].attributes["tag_agent"] == "cmk-agent"
    assert bundle.hosts[0].attributes["cmk_agent_connection"] == "push-agent"
    assert bundle.rules is None
    assert bundle.passwords is None


def test_pull_cannot_save_without_the_final_url(settings: PullSettings) -> None:
    with pytest.raises(ValueError, match="pull mode base URL"):
        _save(replace(settings, base_url=""))

    assert settings.common.bundle_id not in ConfigBundleStore().load_for_reading()
    assert not folder_tree().all_hosts()


def test_pull_requires_password_store_permission_before_saving(settings: PullSettings) -> None:
    roles = deepcopy(active_config.roles)
    roles["admin"].setdefault("permissions", {})["wato.edit_all_passwords"] = False
    assert user.id is not None
    permissions = UserPermissions(roles, permission_registry, {user.id: ["admin"]}, [])
    with login.TransactionIdContext(user.id, permissions), pytest.raises(MKAuthException):
        _save(settings)

    assert settings.common.bundle_id not in ConfigBundleStore().load_for_reading()
    assert not folder_tree().all_hosts()


def test_failed_save_removes_the_new_password_and_bundle(settings: PullSettings) -> None:
    previous_passwords = load_passwords(user)

    def unavailable_audit_log(event: ChangeEvent) -> None:
        if event.request.action_name == "add-password":
            assert load_passwords(user) != previous_passwords
            raise OSError("Audit log unavailable")

    with pytest.raises(MKGeneralException, match="Failed to create configuration bundle"):
        _save(settings, hooks=[unavailable_audit_log])

    assert load_passwords(user) == previous_passwords
    assert settings.common.bundle_id not in ConfigBundleStore().load_for_reading()
    assert not folder_tree().all_hosts()


def test_existing_source_host_is_not_overwritten_by_another_bundle(settings: PullSettings) -> None:
    _save(settings)
    previous_passwords = load_passwords(user)
    conflicting = replace(
        settings,
        common=replace(settings.common, bundle_id=BundleId("another_bundle")),
        shared_secret="new",
    )

    with pytest.raises(MKGeneralException, match="failed validation"):
        _save(conflicting)

    assert load_passwords(user) == previous_passwords
    assert conflicting.common.bundle_id not in ConfigBundleStore().load_for_reading()
    assert set(folder_tree().all_hosts()) == {"legacy"}
