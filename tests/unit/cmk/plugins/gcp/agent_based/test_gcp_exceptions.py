#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow_untyped_defs

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.gcp.agent_based.gcp_exceptions import _ExceptionSection, check, discover, parse


@dataclass(frozen=True)
class GCPException:
    section: _ExceptionSection
    results: Sequence[Result]


EXCEPTIONS = [
    pytest.param(
        GCPException(
            section=_ExceptionSection(
                type="PermissionDenied",
                message="""403 Cloud Asset API has not been used in project 1074106860578 before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578 then retry. If you enabled this API recently, wait a few minutes for the action to propagate to our systems and retry. [links {  description: "Google developers console API activation"  url: "https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578"}, reason: "SERVICE_DISABLED"domain: "googleapis.com"metadata {  key: "consumer"  value: "projects/1074106860578"}metadata {  key: "service"  value: "cloudasset.googleapis.com"}]""",
                gcp_source="Cloud Asset",
            ),
            results=[
                Result(
                    state=State.CRIT,
                    summary="The Google Cloud API reported an error. Please read the error message on how to fix it:",
                    details="PermissionDenied when trying to access Cloud Asset: 403 Cloud Asset API has not been used in project 1074106860578 before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578 then retry. If you enabled this API recently, wait a few minutes for the action to propagate to our systems and retry.",
                )
            ],
        ),
        id="permission denied asset API",
    ),
    pytest.param(
        GCPException(
            section=_ExceptionSection(
                type="PermissionDenied",
                message="""403 Request denied by Cloud IAM. [links {  description: "To check permissions required for this RPC:"  url: "https://cloud.google.com/asset-inventory/docs/access-control#required_permissions"}links {  description: "To get a valid organization id:"  url: "https://cloud.google.com/resource-manager/docs/creating-managing-organization#retrieving_your_organization_id"}links {  description: "To get a valid folder or project id:"  url: "https://cloud.google.com/resource-manager/docs/creating-managing-folders#viewing_or_listing_folders_and_projects"}]""",
                gcp_source="Cloud Asset",
            ),
            results=[
                Result(
                    state=State.CRIT,
                    summary="The Google Cloud API reported an error. Please read the error message on how to fix it:",
                    details="PermissionDenied when trying to access Cloud Asset: 403 Request denied by Cloud IAM. To check permissions required for this RPC: https://cloud.google.com/asset-inventory/docs/access-control#required_permissions. To get a valid organization id: https://cloud.google.com/resource-manager/docs/creating-managing-organization#retrieving_your_organization_id. To get a valid folder or project id: https://cloud.google.com/resource-manager/docs/creating-managing-folders#viewing_or_listing_folders_and_projects",
                )
            ],
        ),
        id="permission denied cloud IAM",
    ),
    pytest.param(
        GCPException(
            section=_ExceptionSection(
                type="HttpError",
                message="""<HttpError 403 when requesting https://bigquery.googleapis.com/bigquery/v2/projects/checkmk-cost-analytics/queries?alt=json returned "Access Denied: Project checkmk-cost-analytics: User does not have bigquery.jobs.create permission in project checkmk-cost-analytics.". Details: "[{'message': 'Access Denied: Project checkmk-cost-analytics: User does not have bigquery.jobs.create permission in project checkmk-cost-analytics.', 'domain': 'global', 'reason': 'accessDenied'}]">""",
                gcp_source="BigQuery",
            ),
            results=[
                Result(
                    state=State.CRIT,
                    summary="The Google Cloud API reported an error. Please read the error message on how to fix it:",
                    details="HttpError when trying to access BigQuery: Access Denied: Project checkmk-cost-analytics: User does not have bigquery.jobs.create permission in project checkmk-cost-analytics.",
                )
            ],
        ),
        id="access denied BigQuery",
    ),
    pytest.param(
        GCPException(
            section=_ExceptionSection(
                type="PermissionDenied",
                message="""403 Permission monitoring.timeSeries.list denied (or the resource may not exist)""",
                gcp_source="Monitoring",
            ),
            results=[
                Result(
                    state=State.CRIT,
                    summary="The Google Cloud API reported an error. Please read the error message on how to fix it:",
                    details="PermissionDenied when trying to access Monitoring: 403 Permission monitoring.timeSeries.list denied (or the resource may not exist)",
                )
            ],
        ),
        id="access denied monitoring",
    ),
    pytest.param(
        GCPException(
            section=_ExceptionSection(
                type="PermissionDenied",
                message="""403 Cloud Asset API has not been used in project 1074106860578 before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578 then retry. If you enabled this API recently, wait a few minutes for the action to propagate to our systems and retry. [links {  description: "Google developers console API activation"  url: "https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578"}, reason: "SERVICE_DISABLED"domain: "googleapis.com"metadata {  key: "consumer"  value: "projects/1074106860578"}metadata {  key: "service"  value: "cloudasset.googleapis.com"}]""",
                gcp_source=None,
            ),
            results=[
                Result(
                    state=State.CRIT,
                    summary="The Google Cloud API reported an error. Please read the error message on how to fix it:",
                    details="PermissionDenied: 403 Cloud Asset API has not been used in project 1074106860578 before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578 then retry. If you enabled this API recently, wait a few minutes for the action to propagate to our systems and retry.",
                )
            ],
        ),
        id="no source",
    ),
    pytest.param(
        GCPException(
            section=_ExceptionSection(
                type="Unauthenticated",
                message="""Cloud Asset:401 Request had invalid authentication credentials. Expected OAuth 2 access token, login cookie or other valid authentication credential. See https://developers.google.com/identity/sign-in/web/devconsole-project. [reason: "ACCOUNT_STATE_INVALID"domain: "googleapis.com"metadata {  key: "email"  value: "test-metric-access@checkmk-check-development.iam.gserviceaccount.com"}metadata {  key: "method"  value: "google.cloud.asset.v1.AssetService.ListAssets"}metadata {  key: "service"  value: "cloudasset.googleapis.com"}]""",
                gcp_source=None,
            ),
            results=[
                Result(
                    state=State.CRIT,
                    summary="The Google Cloud API reported an error. Please read the error message on how to fix it:",
                    details="Unauthenticated: Cloud Asset:401 Request had invalid authentication credentials. Expected OAuth 2 access token, login cookie or other valid authentication credential. See https://developers.google.com/identity/sign-in/web/devconsole-project.",
                )
            ],
        ),
        id="unauthenticated",
    ),
    pytest.param(
        GCPException(
            section=_ExceptionSection(type=None, message=None, gcp_source=None),
            results=[Result(state=State.OK, notice="No exceptions")],
        ),
        id="no exceptions",
    ),
]


@pytest.mark.parametrize(
    "string_table,expected_section",
    [
        pytest.param(
            [["ExceptionType:Source:ExceptionMessage"]],
            _ExceptionSection(
                type="ExceptionType", message="ExceptionMessage", gcp_source="Source"
            ),
            id="exception exists",
        ),
        pytest.param(
            [["ExceptionType::ExceptionMessage"]],
            _ExceptionSection(type="ExceptionType", message="ExceptionMessage", gcp_source=None),
            id="exception without source",
        ),
        pytest.param(
            [["ExceptionType:Source:ExceptionMessagePart1:ExceptionMessagePart2"]],
            _ExceptionSection(
                type="ExceptionType",
                message="ExceptionMessagePart1:ExceptionMessagePart2",
                gcp_source="Source",
            ),
            id="exception message with split char",
        ),
        pytest.param(
            [], _ExceptionSection(type=None, message=None, gcp_source=None), id="no exceptions"
        ),
    ],
)
def test_parse_exception(string_table: StringTable, expected_section: _ExceptionSection) -> None:
    assert parse(string_table) == expected_section


@pytest.mark.parametrize("exception", EXCEPTIONS)
def test_discover_exception(exception: GCPException) -> None:
    assert len(list(discover(exception.section))) == 1


@pytest.mark.parametrize("exception", EXCEPTIONS)
def test_check_exception(exception: GCPException) -> None:
    assert list(check(exception.section)) == exception.results
