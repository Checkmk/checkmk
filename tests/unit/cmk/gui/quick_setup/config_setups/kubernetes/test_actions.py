#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from copy import deepcopy

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.quick_setup.config_setups.kubernetes.actions import (
    finish_setup,
    prepare_push_credentials,
    recap_deployment,
    validate_configuration,
)
from cmk.gui.quick_setup.config_setups.kubernetes.bootstrap import (
    local_push_registration,
    PushRegistration,
)
from cmk.gui.quick_setup.config_setups.kubernetes.constants import QUICK_SETUP_ID
from cmk.gui.quick_setup.config_setups.kubernetes.recap import PushCredentials
from cmk.gui.quick_setup.config_setups.kubernetes.settings import (
    CONNECTION,
    PushSettings,
    read_common_settings,
    read_settings,
)
from cmk.gui.quick_setup.handlers.utils import InfoLogger
from cmk.gui.quick_setup.v0_unstable.setups import (
    QuickSetupActionMode,
    QuickSetupContext,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData, StageIndex
from cmk.gui.quick_setup.v0_unstable.widgets import Code, FormSpecId
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.configuration_bundle_store import BundleId, ConfigBundle, ConfigBundleStore
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.livestatus_client import SiteConfiguration
from cmk.utils import paths

pytestmark = pytest.mark.usefixtures("with_admin_login")


def test_pull_recap_works_without_a_push_receiver_or_site_ca(data: ParsedFormData) -> None:
    widgets = recap_deployment(
        QUICK_SETUP_ID,
        StageIndex(2),
        {**data, CONNECTION: ("pull", {"shared_secret": "kept-secret"})},
        InfoLogger(),
        QuickSetupContext(site_configs={}, debug=False, use_git=False, pprint_value=False),
    )

    assert {widget.download_filename for widget in widgets if isinstance(widget, Code)} == {
        None,
        "values.yaml",
        "pull-secret.yaml",
    }


def test_push_uses_selected_sites_credentials_and_centrally_configured_hostname(
    data: ParsedFormData,
) -> None:
    settings = read_settings({**data, CONNECTION: ("push", {})}, default_site=SiteId("remote"))
    assert isinstance(settings, PushSettings)
    selected_site = active_config.sites[omd_site()].copy()
    selected_site["multisiteurl"] = "https://remote.example/checkmk/"

    def request_registration(
        site_config: SiteConfiguration, host_name: HostName, issuer: UserId
    ) -> PushRegistration:
        assert site_config == selected_site
        assert host_name == "production"
        assert issuer == user.id
        return PushRegistration(
            port=8001, registration_token="remote-token", site_ca_certificate="remote-ca"
        )

    credentials = prepare_push_credentials(
        settings,
        {settings.common.site_id: selected_site},
        request_registration=request_registration,
    )

    assert credentials == PushCredentials(
        receiver_url="https://remote.example:8001/remote",
        registration_token="remote-token",
        site_ca_certificate="remote-ca",
    )


def test_empty_site_ca_fails_before_issuing_a_token(data: ParsedFormData) -> None:
    settings = read_common_settings(data, default_site=omd_site())
    paths.root_cert_file.parent.mkdir(parents=True, exist_ok=True)
    paths.root_cert_file.write_text("", encoding="utf-8")
    assert user.id is not None
    with pytest.raises(ValueError, match="CA certificate is empty"):
        local_push_registration(
            HostName(settings.monitoring.host_name), user.id, push_supported=True
        )


def test_push_issuance_rejects_pull_mode(data: ParsedFormData) -> None:
    settings = read_settings(
        {**data, CONNECTION: ("pull", {"shared_secret": "kept-secret"})},
        default_site=omd_site(),
    )

    with pytest.raises(ValueError, match="push mode"):
        prepare_push_credentials(settings, {})


def test_host_validation_does_not_require_a_connection_mode(data: ParsedFormData) -> None:
    assert (
        validate_configuration(
            QUICK_SETUP_ID,
            data,
            InfoLogger(),
            QuickSetupContext(site_configs={}, debug=False, use_git=False, pprint_value=False),
        )
        == []
    )


def test_deployment_without_a_mode_does_not_prepare_push_credentials(data: ParsedFormData) -> None:
    def unexpected_credentials(
        _settings: PushSettings, _sites: Mapping[SiteId, SiteConfiguration]
    ) -> PushCredentials:
        pytest.fail("Do not issue credentials without a connection mode")

    with pytest.raises(ValueError, match="Choose a connection mode"):
        recap_deployment(
            QUICK_SETUP_ID,
            StageIndex(2),
            data,
            InfoLogger(),
            QuickSetupContext(site_configs={}, debug=False, use_git=False, pprint_value=False),
            prepare_push=unexpected_credentials,
        )


def test_save_without_a_mode_does_not_create_configuration(data: ParsedFormData) -> None:
    with pytest.raises(ValueError, match="Choose a connection mode"):
        finish_setup(
            data,
            QuickSetupActionMode.SAVE,
            InfoLogger(),
            None,
            QuickSetupContext(site_configs={}, debug=False, use_git=False, pprint_value=False),
        )

    assert not ConfigBundleStore().load_for_reading()
    assert not folder_tree().all_hosts()


def test_pull_deployment_requires_password_store_permission(data: ParsedFormData) -> None:
    roles = deepcopy(active_config.roles)
    roles["admin"].setdefault("permissions", {})["wato.edit_all_passwords"] = False
    assert user.id is not None
    permissions = UserPermissions(roles, permission_registry, {user.id: ["admin"]}, [])

    with login.TransactionIdContext(user.id, permissions), pytest.raises(MKAuthException):
        recap_deployment(
            QUICK_SETUP_ID,
            StageIndex(2),
            {**data, CONNECTION: ("pull", {"shared_secret": "kept-secret"})},
            InfoLogger(),
            QuickSetupContext(site_configs={}, debug=False, use_git=False, pprint_value=False),
        )


def test_configuration_name_must_be_a_helm_release_name(data: ParsedFormData) -> None:
    errors = validate_configuration(
        QUICK_SETUP_ID,
        {**data, FormSpecId("formspec_unique_id"): {"bundle_id": "not.a.helm.name"}},
        InfoLogger(),
        QuickSetupContext(site_configs={}, debug=False, use_git=False, pprint_value=False),
    )

    assert errors and "Helm release name" in errors[0]


def test_configuration_names_cannot_normalize_to_the_same_release(data: ParsedFormData) -> None:
    ConfigBundleStore().save(
        {
            BundleId("kubernetes-config-1"): ConfigBundle(
                title="existing",
                comment="",
                group=QUICK_SETUP_ID,
                program_id="quick_setup",
            )
        },
        pprint_value=False,
    )

    assert validate_configuration(
        QUICK_SETUP_ID,
        data,
        InfoLogger(),
        QuickSetupContext(site_configs={}, debug=False, use_git=False, pprint_value=False),
    )

    def unexpected_credentials(
        _settings: PushSettings, _sites: Mapping[SiteId, SiteConfiguration]
    ) -> PushCredentials:
        pytest.fail("Do not issue credentials if central validation fails")

    with pytest.raises(MKUserError, match="Helm release name already exists"):
        recap_deployment(
            QUICK_SETUP_ID,
            StageIndex(2),
            data,
            InfoLogger(),
            QuickSetupContext(site_configs={}, debug=False, use_git=False, pprint_value=False),
            prepare_push=unexpected_credentials,
        )


def test_editing_through_quick_setup_is_rejected(data: ParsedFormData) -> None:
    with pytest.raises(ValueError, match="Editing an existing"):
        finish_setup(
            data,
            QuickSetupActionMode.EDIT,
            InfoLogger(),
            "existing",
            QuickSetupContext(site_configs={}, debug=False, use_git=False, pprint_value=False),
        )
