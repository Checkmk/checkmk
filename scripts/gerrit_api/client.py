#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Abstract code related to Gerrit API calls."""

import base64
import logging
from enum import StrEnum
from typing import Any, Final
from urllib.parse import quote_plus

import httpx
from pydantic import BaseModel
from pydantic_core import from_json
from requests.auth import HTTPBasicAuth

_ACCOUNT_ID = "_account_id"
PROJECT_NAME = "check_mk"
logger = logging.getLogger(__name__)


class TChangeStatus(StrEnum):
    ALL = "ALL"
    NEW = "NEW"
    MERGED = "MERGED"
    ABANDONED = "ABANDONED"

    @staticmethod
    def cli_args() -> set["TChangeStatus"]:
        return {TChangeStatus.ALL, TChangeStatus.NEW, TChangeStatus.MERGED}


class ChangeDetails(BaseModel):
    id: str
    subject: str
    change_id: str
    status: TChangeStatus
    virtual_id_number: int
    work_in_progress: bool = False
    revert_of: int = 0
    owner: dict[str, int | str]
    submit_records: list[dict[str, Any]]
    cherry_pick_of_change: int | None = None

    @property
    def _owner_id(self) -> int:
        try:
            return int(self.owner[_ACCOUNT_ID])
        except KeyError as exc:
            exc.add_note(
                f"Owner ID missing for change-ID '{self.id}'! "
                "Has the REST-API data structure changed?\n"
                f"ref: {GerritClient.GERRIT_API_DOCs}/#change-info"
            )
            raise exc

    @property
    def is_reviewed_by_peer(self) -> bool | None:
        """Decide whether the change is peer-reviewed or not.

        Only valid when a change is MERGED.
        """
        if self.status != TChangeStatus.MERGED:
            logger.warning(
                "Change '%s' is not yet merged; skip peer-review check...", self.change_id
            )
            return None

        # iterate list
        for record in self.submit_records:
            # iterate dict
            for label in record.get("labels", []):
                try:
                    if label["label"] == "Code-Review":
                        if int(label["applied_by"][_ACCOUNT_ID]) != self._owner_id:
                            return True
                except KeyError as exc:
                    exc.add_note(
                        "Expected missing attribute! "
                        "Has the REST-API data structure changed?\n"
                        f"ref: {GerritClient.GERRIT_API_DOCs}/#submit-record-info"
                    )
                    raise exc
        return False

    @property
    def change_url(self) -> str:
        return f"{GerritClient.GERRIT_BASE_URL}/c/{PROJECT_NAME}/+/{self.virtual_id_number}"


class GerritClient:
    """httpx client used for perform REST_API calls to Checkmk's gerrit instance."""

    GERRIT_PREFIX: Final = r")]}'"
    GERRIT_BASE_URL: Final = "https://review.lan.tribe29.com"
    GERRIT_API_DOCs: Final = f"{GERRIT_BASE_URL}/Documentation/rest-api-changes.html"
    GERRIT_URL: Final = f"{GERRIT_BASE_URL}/a"

    def __init__(self, user: str, http_creds: str) -> None:
        super().__init__()
        self._client = httpx.Client(auth=HTTPBasicAuth(user, http_creds))
        self._changes_api: Final = ChangesAPI(self)

    @staticmethod
    def parse_gerrit_response(response: httpx.Response) -> str:
        """Ignore `GERRIT_PREFIX` from the response and then return the actual details."""
        for line in response.iter_lines():
            if line == GerritClient.GERRIT_PREFIX:
                continue
            return line
        raise ValueError(f"No content in the response! Response lines:\n{response.text}")

    @property
    def changes_api(self) -> "ChangesAPI":
        """Perform REST-API calls related to gerrit changes."""
        return self._changes_api

    def get(self, url: str) -> httpx.Response:
        """Wrap `httpx.get` to raise exceptions when REST-API calls result in 4xx status code."""
        response = self._client.get(url)
        response.raise_for_status()
        return response


class ChangesAPI:
    def __init__(self, client: GerritClient) -> None:
        super().__init__()
        self._client = client
        self._url = f"{GerritClient.GERRIT_URL}/changes"

    def get_changes(self, query: str = "") -> list[ChangeDetails]:
        """Return a list of changes scraped in gerrit as per the provided query string."""
        url = f"{GerritClient.GERRIT_URL}/changes"
        if query:
            url = f"{url}/?q={query}"

        resp = self._client.get(url)
        return [
            ChangeDetails(**change)
            for change in from_json(GerritClient.parse_gerrit_response(resp), allow_partial=True)
        ]

    def get_files(self, change: ChangeDetails) -> list[str]:
        """Return list of files corresponding to the latest patchset in a change."""
        url = f"{self._url}/{change.id}/revisions/current/files/"
        resp = self._client.get(url)
        return [file_path for file_path in from_json(GerritClient.parse_gerrit_response(resp))]

    def get_content_from_file(self, change: ChangeDetails, file_path: str) -> str:
        """Return the contents of a file corresponding to a change.

        Args:
            change (ChangeDetails): details corresponding to a change.
            file_path (str): Path of the file present in the change;
                path is relative to the root directory of the repository.

        Raises:
            FileNotFoundError: the content is missing as the file is not found within the change.
        """
        fpath = quote_plus(file_path)
        url = f"{self._url}/{change.id}/revisions/current/files/{fpath}/content"
        try:
            resp = self._client.get(url)
        except httpx.HTTPStatusError as exc:
            raise FileNotFoundError(
                "Content not found! "
                f"File '{file_path}' was deleted in change '{change.id}: {change.subject}'!"
            ) from exc
        return base64.b64decode(GerritClient.parse_gerrit_response(resp)).decode("utf-8")

    def get_commit_message(self, change: ChangeDetails) -> str:
        """Return the commit message of a change.

        Includes both the subject and the body of a commit message.
        """
        url = f"{self._url}/{change.id}/message"
        resp = GerritClient.parse_gerrit_response(self._client.get(url))
        resp_ = from_json(resp)
        return str(resp_.get("full_message", "N/A"))
