#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import secrets
from urllib.parse import urlsplit

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.quick_setup.v0_unstable.definitions import QSSiteSelection
from cmk.gui.quick_setup.v0_unstable.predefined import recaps, validators, widgets
from cmk.gui.quick_setup.v0_unstable.setups import (
    applicable_if,
    QuickSetup,
    QuickSetupAction,
    QuickSetupActionButtonIcon,
    QuickSetupActionMode,
    QuickSetupBackgroundStageAction,
    QuickSetupStage,
    QuickSetupStageAction,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import ActionId, ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import Collapsible, FormSpecWrapper, Text
from cmk.licensing.basics.options import OptionName
from cmk.licensing.registry import is_option_enabled
from cmk.rulesets.v1 import Help, Title
from cmk.utils import paths

from .actions import (
    finish_setup,
    recap_deployment,
    validate_configuration,
)
from .connection_forms import connection_configuration, host_configuration, pull_url_configuration
from .connection_test import validate_pull_connection
from .constants import QUICK_SETUP_ID
from .form_specs import advanced_configuration, cluster_configuration
from .settings import ADVANCED, CLUSTER, CONNECTION, HOST, PULL_URL


def configure_cluster() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure your cluster for Checkmk monitoring"),
        configure_components=[
            widgets.unique_id_formspec_wrapper(
                Title("Configuration name"),
                "kubernetes_config",
                help_text=Help(
                    "Also used as the Helm release name, converted to lowercase with underscores "
                    "replaced by hyphens. For example, kubernetes_config_1 becomes "
                    "kubernetes-config-1. The release name must be at most 53 characters long."
                ),
            ),
            FormSpecWrapper(id=CLUSTER, form_spec=cluster_configuration()),
            Collapsible(
                title=_("Advanced options"),
                items=[FormSpecWrapper(id=ADVANCED, form_spec=advanced_configuration())],
            ),
        ],
        actions=[
            QuickSetupStageAction(
                id=ActionId("continue"),
                custom_validators=[validators.validate_unique_id],
                recap=[recaps.recaps_form_spec],
            )
        ],
    )


def configure_host() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure the Checkmk host"),
        prev_button_label=_("Back"),
        configure_components=[
            FormSpecWrapper(id=HOST, form_spec=host_configuration()),
            widgets.site_formspec_wrapper(),
        ],
        actions=[
            QuickSetupStageAction(
                id=ActionId("continue"),
                custom_validators=[validate_configuration],
                recap=[recaps.recaps_form_spec],
            )
        ],
    )


def prepare_deployment() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Deploy the Kubernetes agent"),
        prev_button_label=_("Back"),
        sub_title=_("Choose the connection mode and prepare the deployment files"),
        configure_components=[
            Text(
                text=_(
                    "Choose how the Kubernetes agent connects to Checkmk, "
                    "then generate the deployment files."
                )
            ),
            FormSpecWrapper(
                id=CONNECTION,
                form_spec=connection_configuration(
                    receiver_host=urlsplit(request.requested_url).hostname or "",
                    shared_secret=secrets.token_urlsafe(48),
                    push_supported=is_option_enabled(paths.omd_root, OptionName.AGENT_REGISTRATION),
                ),
            ),
        ],
        actions=[
            QuickSetupBackgroundStageAction(
                id=ActionId("prepare_deployment"),
                custom_validators=[],
                recap=[recap_deployment],
                next_button_label=_("Generate deployment files"),
                # Validate centrally, then request push credentials from the monitoring site.
                permissions=["wato.hosts", "wato.manage_hosts"],
            )
        ],
    )


def uses_pull_mode(data: ParsedFormData) -> bool:
    match data.get(CONNECTION):
        case ("pull", _):
            return True
        case _:
            return False


@applicable_if(uses_pull_mode)
def configure_pull_url() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Connect Checkmk to the Kubernetes agent"),
        prev_button_label=_("Back"),
        sub_title=_(
            "After deploying the agent, enter its address as reachable from the Checkmk site"
        ),
        configure_components=[FormSpecWrapper(id=PULL_URL, form_spec=pull_url_configuration())],
        actions=[
            QuickSetupBackgroundStageAction(
                id=ActionId("confirm_url"),
                custom_validators=[validate_pull_connection],
                recap=[
                    recaps.recaps_form_spec,
                    lambda *_args: [
                        Text(text=_("Successfully retrieved Kubernetes agent sections."))
                    ],
                ],
                next_button_label=_("Test connection"),
                load_wait_label=_("Testing the connection to the Kubernetes agent..."),
                target_site_formspec_key=QSSiteSelection,
                permissions=["wato.edit_all_passwords"],
            ),
            QuickSetupStageAction(
                id=ActionId("skip_connection_test"),
                custom_validators=[],
                recap=[
                    recaps.recaps_form_spec,
                    lambda *_args: [Text(text=_("Skipped the connection test."))],
                ],
                next_button_label=_("Skip test"),
            ),
        ],
    )


def completion_action() -> QuickSetupAction:
    return QuickSetupAction(
        id=ActionId("save"),
        label=_("Save & go to 'Activate changes'"),
        icon=QuickSetupActionButtonIcon(name="save-to-services"),
        action=finish_setup,
        custom_validators=[validate_configuration],
        permissions=["wato.hosts", "wato.manage_hosts", "wato.rulesets", "wato.passwords"],
        modes=[QuickSetupActionMode.SAVE],
    )


quick_setup_kubernetes = QuickSetup(
    title=_("Kubernetes"),
    id=QUICK_SETUP_ID,
    stages=[configure_cluster, configure_host, prepare_deployment, configure_pull_url],
    actions=[completion_action()],
    allow_push_agent=True,
)
