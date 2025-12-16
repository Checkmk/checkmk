# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.exceptions import MKUnauthenticatedException
from cmk.gui.token_auth._store import TokenType


class MKTokenExpiredOrRevokedException(MKUnauthenticatedException):
    token_type: TokenType

    def __init__(self, *args: object, token_type: TokenType) -> None:
        super().__init__(*args)
        self.token_type: TokenType = token_type
