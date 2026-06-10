#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, UTC

from cmk.gui.livestatus_utils.commands.comment import Comment
from cmk.gui.openapi.api_endpoints.comment.models.response_models import (
    CommentExtensionsModel,
    CommentObjectModel,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.utils import permission_verification as permissions

PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
            permissions.Undocumented(permissions.Perm("wato.see_all_folders")),
        ]
    )
)

RW_PERMISSIONS = permissions.AllPerm([permissions.Perm("action.addcomment"), PERMISSIONS])


def serialize_comment(comment: Comment) -> CommentObjectModel:

    entry_time = (
        datetime.strptime(comment.entry_time, "%b %d %Y %H:%M:%S").replace(tzinfo=UTC).isoformat()
    )

    return CommentObjectModel(
        domainType="comment",
        id=str(comment.id),
        title=comment.comment,
        links=generate_links(
            domain_type="comment",
            identifier=str(comment.id),
            deletable=True,
            editable=False,
        ),
        extensions=CommentExtensionsModel(
            host_name=comment.host_name,
            id=comment.id,
            author=comment.author,
            comment=comment.comment,
            persistent=comment.persistent,
            entry_time=entry_time,
            service_description=comment.service_description or ApiOmitted(),
            is_service=comment.is_service,
            site_id=comment.site,
        ),
    )
