#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk.crash import CrashReportStore, make_crash_report_base_path
from cmk.gui.crash_handler import JavascriptCrashReport, JavascriptDetails
from cmk.gui.http import request
from cmk.gui.i18n import get_current_language
from cmk.gui.log import logger
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href

from ._family import CRASH_REPORT_FAMILY
from .models.request_models import CreateJavascriptCrashReport
from .models.response_models import (
    JavascriptCrashReportExtensions,
    JavascriptCrashReportObjectModel,
)


def create_javascript_crash_report_v1(
    api_context: ApiContext, body: CreateJavascriptCrashReport
) -> ApiResponse[JavascriptCrashReportObjectModel]:
    """Store an error caught in the browser as a crash report."""
    crash = JavascriptCrashReport.from_browser_error(
        version_info=cmk_version.get_general_version_infos(cmk.utils.paths.omd_root),
        error_name=body.error_name,
        error_message=body.error_message,
        stack=body.stack,
        details=JavascriptDetails(
            url=body.url,
            component=body.component,
            user_agent=request.user_agent.string,
            username=api_context.user.id,
            language=get_current_language(),
            context=body.context,
        ),
        crash_report_base_path=make_crash_report_base_path(cmk.utils.paths.omd_root),
    )
    CrashReportStore().save(crash)
    logger.warning(
        "Unhandled exception in the Checkmk frontend (Crash ID: %(crash_id)s)",
        {"crash_id": crash.ident_to_text()},
    )
    return ApiResponse(
        JavascriptCrashReportObjectModel(
            domainType="javascript_crash_report",
            id=crash.ident_to_text(),
            title=f"{crash.crash_info['exc_type']}: {crash.crash_info['exc_value']}",
            links=[],
            extensions=JavascriptCrashReportExtensions(
                crash_type=crash.type(),
                crash_report_url=crash.url(),
            ),
        ),
        status_code=201,
    )


ENDPOINT_CREATE_JAVASCRIPT_CRASH_REPORT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("javascript_crash_report"),
        link_relation="cmk/create",
        method="post",
    ),
    permissions=EndpointPermissions(required=None),
    doc=EndpointDoc(family=CRASH_REPORT_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=create_javascript_crash_report_v1)},
)
