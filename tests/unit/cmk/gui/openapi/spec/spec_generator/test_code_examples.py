#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

from cmk.gui.openapi.spec.spec_generator._code_examples import (
    formatted_if_statement_for_responses,
)


class TestFormattedIfStatementForResponses:
    def test_302_redirect_adds_200_and_204(self) -> None:
        result = formatted_if_statement_for_responses(
            [HTTPStatus.FOUND], downloadable=False, code_example="requests"
        )
        assert "resp.status_code == 200:" in result
        assert "resp.status_code == 204:" in result
        assert "resp.status_code == 302:" in result
