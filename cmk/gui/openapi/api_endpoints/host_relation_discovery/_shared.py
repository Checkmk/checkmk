#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What the discovery endpoints have in common."""

from typing import assert_never

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.host_config._utils import rw_permissions
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils.host_relation_kinds import is_name_token
from cmk.gui.watolib.host_relation_discovery import (
    NamesTellApart,
    SharedAttribute,
    SharedLabel,
    Suggestions,
    TellApart,
    ValueTellsApart,
)
from cmk.gui.watolib.host_relation_scan import value_source, ValueArgs
from cmk.web.utils import permission_verification as permissions

from .models.request_models import SuggestEvidenceRequestModel
from .models.response_models import (
    SuggestionsModel,
    ToldApartModel,
    ValueCountModel,
    ValueExampleModel,
    ValueFindingModel,
    WordExampleModel,
    WordFindingModel,
)

#: Storing a discovered relation is editing hosts, and nothing beyond it - hence no permission
#: of its own, and the ones the host-writing endpoints declare.
PERMISSIONS = rw_permissions(
    permissions.Perm("wato.hosts"),
    permissions.Perm("wato.edit_hosts"),
    # Read by the background job's own housekeeping when the job is started.
    permissions.Optional(permissions.Perm("background_jobs.delete_jobs")),
)


def need_discovery_permissions() -> None:
    user.need_permission("wato.hosts")
    user.need_permission("wato.edit_hosts")


def parsed_words(body: SuggestEvidenceRequestModel) -> list[str]:
    """The words the user typed, or a 400 for one no host name could ever carry."""
    for word in body.words:
        if not is_name_token(word):
            raise invalid_request(f"{word!r} cannot be read out of a host name.")
    return body.words


def parsed_values(body: SuggestEvidenceRequestModel) -> list[SharedLabel | SharedAttribute]:
    return [ValueArgs(source=value.source, name=value.name).where() for value in body.values]


def invalid_request(detail: str) -> ProblemException:
    return ProblemException(status=400, title="Invalid request", detail=detail)


def _told_apart_model(told_apart: TellApart) -> ToldApartModel | None:
    match told_apart:
        case None:
            return None
        case NamesTellApart(kind_id=kind_id, words=words, groups=groups):
            return ToldApartModel(
                by="names",
                kind=kind_id,
                words=list(words),
                groups=groups,
                source=None,
                name=None,
                values=[],
                suggested=None,
            )
        case ValueTellsApart(where=where, values=values, suggested=suggested):
            return ToldApartModel(
                by="value",
                kind=None,
                words=[],
                groups=0,
                source=value_source(where),
                name=where.name,
                values=[ValueCountModel(value=value, groups=groups) for value, groups in values],
                suggested=suggested,
            )
        case _:
            assert_never(told_apart)


def as_suggestions_model(found: Suggestions) -> SuggestionsModel:
    return SuggestionsModel(
        hosts_scanned=found.hosts_scanned,
        words=[
            WordFindingModel(
                word=finding.word,
                pairs=finding.pairs,
                examples=[
                    WordExampleModel(named=named, base=base) for named, base in finding.examples
                ],
                kind=finding.kind_id,
            )
            for finding in found.words
        ],
        values=[
            ValueFindingModel(
                source=value_source(finding.where),
                name=finding.where.name,
                groups=finding.groups,
                largest_group=finding.largest_group,
                examples=[
                    ValueExampleModel(value=value, hosts=list(hosts))
                    for value, hosts in finding.examples
                ],
                too_wide=finding.too_wide,
                told_apart=_told_apart_model(finding.told_apart),
            )
            for finding in found.values
        ],
        label_names=list(found.label_names),
        attribute_names=list(found.attribute_names),
    )
