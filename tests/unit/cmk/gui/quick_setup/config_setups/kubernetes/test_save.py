#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import replace

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId
from cmk.gui.config import Config, get_default_config, make_config_object
from cmk.gui.exceptions import MKAuthException
from cmk.gui.logged_in import LoggedInUser, UserDefaultConfig
from cmk.gui.permissions import permission_registry
from cmk.gui.quick_setup.config_setups.kubernetes.helm import MonitoringSettings
from cmk.gui.quick_setup.config_setups.kubernetes.save import save_configuration
from cmk.gui.quick_setup.config_setups.kubernetes.settings import (
    CommonSettings,
    PullSettings,
    PushSettings,
    Settings,
)
from cmk.gui.role_types import BuiltInUserRole, CustomUserRole
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.configuration_bundle_store import BundleId, ConfigBundleStore
from cmk.gui.watolib.configuration_bundles import (
    BundleReferences,
    identify_single_bundle_references,
)
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.passwords import load_passwords
from cmk.gui.watolib.pending_changes import (
    ChangeEvent,
    ChangeHook,
    NoopPendingChangesStore,
    PendingChanges,
)
from cmk.ruleset_matcher.tags import get_effective_tag_config
from cmk.utils import paths
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP

pytestmark = pytest.mark.usefixtures("mock_password_file_regeneration")

_ADMIN_ID = UserId("admin")


@pytest.fixture
def config() -> Config:
    raw_config = get_default_config()
    raw_config["tags"] = get_effective_tag_config(raw_config["wato_tags"])
    return make_config_object(raw_config)


def _admin(roles: Mapping[str, BuiltInUserRole | CustomUserRole]) -> LoggedInUser:
    paths.profile_dir.mkdir(parents=True, exist_ok=True)
    return LoggedInUser(
        _ADMIN_ID,
        UserPermissions(roles, permission_registry, {_ADMIN_ID: ["admin"]}, []),
        defaults=UserDefaultConfig(
            users={}, default_language="en", default_show_mode="default_show_less"
        ),
    )


@pytest.fixture
def admin(config: Config) -> LoggedInUser:
    return _admin(config.roles)


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


def _save(
    settings: Settings,
    config: Config,
    acting_user: LoggedInUser,
    *,
    hooks: Sequence[ChangeHook] = (),
) -> BundleReferences:
    save_configuration(
        settings,
        tree=make_folder_tree(config),
        acting_user=acting_user,
        user_permissions=UserPermissions.from_config(config, permission_registry),
        pending_changes=PendingChanges(
            activation_sites=config.sites,
            local_site=omd_site(),
            acting_user=acting_user.id,
            store=NoopPendingChangesStore(),
            hooks=hooks,
        ),
        pprint_value=False,
        debug=False,
    )
    return identify_single_bundle_references(
        make_folder_tree(config),
        settings.common.bundle_id,
        acting_user=acting_user,
        program_id=PROGRAM_ID_QUICK_SETUP,
    )


def test_pull_saves_host_rule_and_the_deployed_password(
    settings: PullSettings, config: Config, admin: LoggedInUser
) -> None:
    bundle = _save(settings, config, admin)

    assert bundle.hosts and bundle.rules and bundle.passwords
    assert len(bundle.hosts) == len(bundle.rules) == len(bundle.passwords) == 1
    assert bundle.hosts[0].name() == "legacy"
    assert bundle.hosts[0].attributes["tag_agent"] == "special-agents"
    password_id, password = bundle.passwords[0]
    assert password["password"] == "deployed-secret"
    assert password["owned_by"] == admin.id
    assert bundle.rules[0].value == {
        "url": "https://agent:30050",
        "shared_secret": ("cmk_postprocessed", "stored_password", (password_id, "")),
        "verify_cert": True,
    }


def test_push_saves_a_push_host_without_pull_rule_or_password(
    settings: PullSettings, config: Config, admin: LoggedInUser
) -> None:
    bundle = _save(PushSettings(common=settings.common), config, admin)

    assert bundle.hosts and len(bundle.hosts) == 1
    assert bundle.hosts[0].attributes["tag_agent"] == "cmk-agent"
    assert bundle.hosts[0].attributes["cmk_agent_connection"] == "push-agent"
    assert bundle.rules is None
    assert bundle.passwords is None


def test_pull_cannot_save_without_the_final_url(
    settings: PullSettings, config: Config, admin: LoggedInUser
) -> None:
    with pytest.raises(ValueError, match="pull mode base URL"):
        _save(replace(settings, base_url=""), config, admin)

    assert settings.common.bundle_id not in ConfigBundleStore().load_for_reading()
    assert not make_folder_tree(config).all_hosts()


def test_pull_requires_password_store_permission_before_saving(
    settings: PullSettings, config: Config
) -> None:
    roles = deepcopy(config.roles)
    roles["admin"].setdefault("permissions", {})["wato.edit_all_passwords"] = False

    with pytest.raises(MKAuthException):
        _save(settings, config, _admin(roles))

    assert settings.common.bundle_id not in ConfigBundleStore().load_for_reading()
    assert not make_folder_tree(config).all_hosts()


def test_failed_save_removes_the_new_password_and_bundle(
    settings: PullSettings, config: Config, admin: LoggedInUser
) -> None:
    previous_passwords = load_passwords(admin)

    def unavailable_audit_log(event: ChangeEvent) -> None:
        if event.request.action_name == "add-password":
            assert load_passwords(admin) != previous_passwords
            raise OSError("Audit log unavailable")

    with pytest.raises(MKGeneralException, match="Failed to create configuration bundle"):
        _save(settings, config, admin, hooks=[unavailable_audit_log])

    assert load_passwords(admin) == previous_passwords
    assert settings.common.bundle_id not in ConfigBundleStore().load_for_reading()
    assert not make_folder_tree(config).all_hosts()


def test_existing_source_host_is_not_overwritten_by_another_bundle(
    settings: PullSettings, config: Config, admin: LoggedInUser
) -> None:
    _save(settings, config, admin)
    previous_passwords = load_passwords(admin)
    conflicting = replace(
        settings,
        common=replace(settings.common, bundle_id=BundleId("another_bundle")),
        shared_secret="new",
    )

    with pytest.raises(MKGeneralException, match="failed validation"):
        _save(conflicting, config, admin)

    assert load_passwords(admin) == previous_passwords
    assert conflicting.common.bundle_id not in ConfigBundleStore().load_for_reading()
    assert set(make_folder_tree(config).all_hosts()) == {"legacy"}
