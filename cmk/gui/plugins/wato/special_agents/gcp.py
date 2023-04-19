#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Final

from cmk.utils.version import is_cloud_edition

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupVMCloudContainer
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    MigrateNotUpdated,
    MigrateToIndividualOrStoredPassword,
    rulespec_registry,
)
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import Dictionary, ListChoice, TextInput

RAW_GCP_SERVICES: Final = [
    ("gcs", "Google Cloud Storage (GCS)"),
    ("cloud_sql", "Cloud SQL"),
    ("filestore", "Filestore"),
    ("gce_storage", "GCE Storage"),
    ("http_lb", "HTTP(S) load balancer"),
]

CCE_GCP_SERVICES: Final = [
    ("cloud_run", "Cloud Run"),
    ("cloud_functions", "Cloud Functions"),
    ("redis", "Memorystore Redis"),
]


def get_gcp_services() -> Sequence[tuple[str, str]]:
    if is_cloud_edition():
        return RAW_GCP_SERVICES + CCE_GCP_SERVICES

    return RAW_GCP_SERVICES


def _valuespec_special_agents_gcp():
    valid_service_choices = {c[0] for c in get_gcp_services()}
    return Dictionary(
        title=_("Google Cloud Platform"),
        elements=[
            ("project", TextInput(title=_("Project ID"), allow_empty=False, size=50)),
            (
                "credentials",
                MigrateToIndividualOrStoredPassword(
                    title=_("JSON credentials for service account"), allow_empty=False
                ),
            ),
            (
                "services",
                MigrateNotUpdated(
                    valuespec=ListChoice(
                        title=_("GCP services to monitor"),
                        choices=get_gcp_services(),
                        default_value=[s[0] for s in get_gcp_services()],
                        allow_empty=True,
                    ),
                    # silently cut off invalid CCE only choices if we're CEE now.
                    migrate=lambda slist: [s for s in slist if s in valid_service_choices],
                ),
            ),
            (
                "piggyback",
                Dictionary(
                    title=_("GCP piggyback services"),
                    elements=[
                        (
                            "prefix",
                            TextInput(
                                title=_("Custom host name prefix"),
                                help=_(
                                    "Prefix for GCE piggyback host names. Defaults to project ID"
                                ),
                            ),
                        ),
                        (
                            "piggyback_services",
                            ListChoice(
                                title=_("Piggyback services to monitor"),
                                choices=[("gce", _("Google Compute Engine (GCE)"))],
                                default_value=["gce"],
                                allow_empty=True,
                            ),
                        ),
                    ],
                    optional_keys=["prefix"],
                ),
            ),
            (
                "cost",
                Dictionary(
                    title="Costs",
                    elements=[
                        (
                            "tableid",
                            TextInput(
                                title="BigQuery table ID",
                                help=_(
                                    "Table ID found in the Details of the table in the SQL workspace of BigQuery"
                                ),
                            ),
                        )
                    ],
                    required_keys=["tableid"],
                ),
            ),
        ],
        optional_keys=["cost"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:gcp",
        title=lambda: _("Google Cloud Platform (GCP)"),
        valuespec=_valuespec_special_agents_gcp,
        doc_references={DocReference.GCP: _("Monitoring Google Cloud Platform (GCP)")},
    )
)
