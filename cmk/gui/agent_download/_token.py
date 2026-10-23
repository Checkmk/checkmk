#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus
from types import TracebackType
from typing import Final

from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import AuthToken, InvalidToken, TokenId, TokenStore

DOWNLOAD_TOKEN_FAILURE_DETAIL: Final = (
    "This one-time token has already been used, has expired or is in use by a download "
    "that is still running. Generate a new one in the host's agent dialog."
)


class AgentPackageUnavailable(ProblemException):
    """The requested agent package is not available right now, but may be later"""


class OneTimeDownloadToken:
    """Uses up a one-time download token, unless the agent package is unavailable

    The token leaves the store on entering, so parallel requests with the same token
    cannot download twice. It goes back to the store only if the block raises
    AgentPackageUnavailable, so the same install command can be retried once the
    package is there. Any other failure, e.g. invalid parameters or missing
    permissions, uses up the token.
    """

    def __init__(self, token_id: TokenId, store: TokenStore) -> None:
        self._token_id = token_id
        self._store = store
        self._taken: AuthToken | None = None

    def __enter__(self) -> None:
        try:
            self._taken = self._store.take(self._token_id)
        except InvalidToken:
            raise ProblemException(
                status=HTTPStatus.UNAUTHORIZED,
                title=HTTPStatus.UNAUTHORIZED.phrase,
                detail=DOWNLOAD_TOKEN_FAILURE_DETAIL,
            ) from None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if isinstance(exc_val, AgentPackageUnavailable) and self._taken is not None:
            self._store.restore(self._taken)
