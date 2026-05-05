#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Final

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import MultipleChoiceElement

type ServiceChoices = Sequence[MultipleChoiceElement]

GCP_SERVICES: Final[ServiceChoices] = [
    MultipleChoiceElement(name="gcs", title=Title("Google Cloud Storage (GCS)")),
    MultipleChoiceElement(name="cloud_sql", title=Title("Cloud SQL")),
    MultipleChoiceElement(name="filestore", title=Title("Filestore")),
    MultipleChoiceElement(name="gce_storage", title=Title("GCE Storage")),
    MultipleChoiceElement(name="http_lb", title=Title("HTTP(S) load balancer")),
]
