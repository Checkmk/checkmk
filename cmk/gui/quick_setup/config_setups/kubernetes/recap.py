#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from html import escape

from cmk.gui.i18n import _
from cmk.gui.quick_setup.v0_unstable.widgets import Code, ListOfWidgets, Text, Widget

from .deployment import pull_deployment, push_deployment
from .settings import PullSettings, PushSettings, Settings


@dataclass(frozen=True, kw_only=True)
class PushCredentials:
    receiver_url: str
    registration_token: str = field(repr=False)
    site_ca_certificate: str = field(repr=False)


def deployment_widgets(
    settings: Settings, *, prepare_push: Callable[[PushSettings], PushCredentials]
) -> Sequence[Widget]:
    """Prepare downloads on an explicit deployment action, never while building the form."""
    common = settings.common
    if isinstance(settings, PullSettings):
        bundle = pull_deployment(
            common.monitoring,
            release_name=common.release_name,
            namespace=common.namespace,
            shared_secret=settings.shared_secret,
            node_port=settings.node_port,
            tls_secret_name=settings.tls_secret_name,
        )
        instructions = [
            Text(text=_("After deploying the agent, continue to enter the pull mode base URL.")),
            Text(text=_("The same shared secret will be saved in the Checkmk password store.")),
        ]
    else:
        credentials = prepare_push(settings)
        bundle = push_deployment(
            common.monitoring,
            release_name=common.release_name,
            namespace=common.namespace,
            receiver_url=credentials.receiver_url,
            registration_token=credentials.registration_token,
            site_ca_certificate=credentials.site_ca_certificate,
        )
        instructions = [
            Text(
                text=_(
                    "Complete this setup and <b>activate the changes</b> so the agent can register."
                )
            ),
            Text(text=_("The one-time registration token expires after <b>one hour</b>.")),
            Text(
                text=_(
                    "After successful registration, delete <tt>push-registration-secret.yaml</tt> "
                    "and its Kubernetes Secret. Remove the manifest from your deployment workflow."
                )
            ),
            Text(
                text=_(
                    "Keep <tt>cmk-signed-push-cert</tt>, the agent's persistent certificate Secret."
                )
            ),
        ]
    return [
        Text(text=_("<h2>Before you deploy</h2>")),
        ListOfWidgets(
            list_type="bullet",
            items=[
                Text(
                    text=_(
                        "The Secret file contains credentials. <b>Do not commit it unencrypted to Git.</b> "
                        "Use your organization's secret-management workflow."
                    )
                ),
                *instructions,
            ],
        ),
        Text(text=_("<h2>Download the deployment files</h2>")),
        Text(
            text=_(
                "Download both files below and save them in the same directory. "
                "Alternatively, use them with your existing deployment workflow."
            )
        ),
        *[
            Code(title=filename, code=contents, download_filename=filename)
            for filename, contents in bundle.files.items()
        ],
        Text(text=_("<h2>Deploy with Helm</h2>")),
        ListOfWidgets(
            list_type="bullet",
            items=[
                Text(
                    text=_(
                        "Helm and kubectl are required to run these commands. "
                        "Run them from the directory containing the downloaded files."
                    )
                ),
                Text(
                    text=_(
                        "Helm selects the latest stable chart release matching <b>%(version_range)s</b> "
                        "when you run the command."
                    )
                    % {"version_range": escape(bundle.chart_version_range)}
                ),
                Text(
                    text=_(
                        "For reproducible GitOps deployments, replace the range with an "
                        "<b>exact released chart version</b> within it."
                    )
                ),
            ],
        ),
        Code(code=bundle.commands),
    ]
