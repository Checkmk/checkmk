#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.quick_setup.v0_unstable.setups import (
    ProgressLogger,
    QuickSetupActionMode,
    QuickSetupContext,
    StepStatus,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import Widget
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.config_domain_name import CORE
from cmk.gui.watolib.configuration_bundle_store import ConfigBundleStore
from cmk.gui.watolib.mode import mode_url
from cmk.gui.watolib.pending_changes import (
    Change,
    ChangeScope,
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.sidebar_reload import sidebar_reload_change_hook
from cmk.livestatus_client import SiteConfiguration

from .bootstrap import push_receiver_url, PushRegistration, request_push_registration
from .constants import QUICK_SETUP_ID
from .recap import deployment_widgets, PushCredentials
from .save import save_configuration
from .settings import PullSettings, PushSettings, read_common_settings, read_settings, Settings


def validate_configuration(
    _quick_setup_id: QuickSetupId,
    data: ParsedFormData,
    _progress_logger: ProgressLogger,
    ctx: QuickSetupContext,
) -> GeneralStageErrors:
    try:
        settings = read_common_settings(data, default_site=omd_site())
        host_name = HostName(settings.monitoring.host_name)
    except ValueError as error:
        return [str(error)]
    for existing_id in ConfigBundleStore().load_for_reading():
        if existing_id.lower().replace("_", "-") == settings.release_name:
            return [
                _(
                    "A configuration with this Helm release name already exists. Choose another name."
                )
            ]
    if ctx.tree.host(host_name):
        return [
            _(
                "The source host already exists. Choose another host name or remove the old source host first."
            )
        ]
    # These configuration checks must run centrally, before deployment and again before saving.
    ctx.tree.folder(settings.host_path).prepare_create_hosts(acting_user=user)
    return []


def prepare_push_credentials(
    settings: Settings,
    site_configs: Mapping[SiteId, SiteConfiguration],
    *,
    request_registration: Callable[
        [SiteConfiguration, HostName, UserId], PushRegistration
    ] = request_push_registration,
) -> PushCredentials:
    """Called after central configuration validation; obtain credentials from the selected site."""
    if not isinstance(settings, PushSettings):
        raise ValueError("Push registration must run in push mode")
    user.need_permission("wato.manage_hosts")
    common = settings.common
    site_config = site_configs[common.site_id]
    assert user.id is not None
    registration = request_registration(site_config, HostName(common.monitoring.host_name), user.id)
    receiver_url = push_receiver_url(
        site_id=common.site_id,
        site_url=site_config.get("multisiteurl", ""),
        browser_host=settings.receiver_host,
        port=registration.port,
        override_host=settings.receiver_host_override,
    )
    return PushCredentials(
        receiver_url=receiver_url,
        registration_token=registration.registration_token,
        site_ca_certificate=registration.site_ca_certificate,
    )


def recap_deployment(
    quick_setup_id: QuickSetupId,
    _stage_index: StageIndex,
    data: ParsedFormData,
    progress_logger: ProgressLogger,
    ctx: QuickSetupContext,
    *,
    prepare_push: Callable[
        [PushSettings, Mapping[SiteId, SiteConfiguration]], PushCredentials
    ] = prepare_push_credentials,
) -> Sequence[Widget]:
    # Authorize centrally on every generation request, including requests that skip earlier stages.
    if errors := validate_configuration(quick_setup_id, data, progress_logger, ctx):
        raise MKUserError(None, " ".join(errors))
    settings = read_settings(data, default_site=omd_site())
    if isinstance(settings, PullSettings):
        user.need_permission("wato.edit_all_passwords")
    return deployment_widgets(
        settings, prepare_push=lambda push_settings: prepare_push(push_settings, ctx.site_configs)
    )


def finish_setup(
    data: ParsedFormData,
    mode: QuickSetupActionMode,
    progress_logger: ProgressLogger,
    _object_id: str | None,
    ctx: QuickSetupContext,
) -> str:
    if mode != QuickSetupActionMode.SAVE:
        raise ValueError(
            "Editing an existing Kubernetes deployment through Quick Setup is not supported"
        )
    if errors := validate_configuration(QUICK_SETUP_ID, data, progress_logger, ctx):
        raise MKUserError(None, " ".join(errors))
    settings = read_settings(data, default_site=omd_site())
    pending_changes = PendingChanges(
        activation_sites=activation_sites(active_config.sites),
        local_site=omd_site(),
        acting_user=user.id,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=ctx.use_git),
            sidebar_reload_change_hook,
            index_update_change_hook,
        ),
    )
    progress_logger.log_new_progress_step(
        "create_config_bundle", _("Create underlying configurations")
    )
    save_configuration(
        settings,
        tree=ctx.tree,
        acting_user=user,
        user_permissions=UserPermissions.from_config(active_config, permission_registry),
        pending_changes=pending_changes,
        pprint_value=ctx.pprint_value,
        debug=active_config.debug,
    )
    pending_changes.add(
        Change(
            action_name="create-quick-setup",
            text=_("Created Kubernetes configuration %(name)s")
            % {"name": settings.common.bundle_id},
            prevent_discard_changes=True,
            domains=[CORE],
        ),
        ChangeScope.all_activation_sites(),
    )
    progress_logger.update_progress_step_status("create_config_bundle", StepStatus.COMPLETED)
    return mode_url("changelog", origin="quick_setup")
