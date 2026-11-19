#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

import pytest

from cmk import fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.spec.spec_generator._doc_marshmallow import (
    MarshmallowResponses,
    to_dict,
)


def test_to_dict_with_examples() -> None:
    class SayHello(BaseSchema):
        message = fields.String(example="Hello world!")
        message2 = fields.String(example="Hello Bob!")

    assert to_dict(SayHello()) == {"message": "Hello world!", "message2": "Hello Bob!"}


def test_to_dict_missing_example() -> None:
    class Nobody(BaseSchema):
        expects = fields.String()

    with pytest.raises(KeyError, match="has no 'example'"):
        to_dict(Nobody())


def test_generate_error_responses_documents_a_declared_server_error() -> None:
    responses = MarshmallowResponses.generate_error_responses(
        {HTTPStatus.SERVICE_UNAVAILABLE},
        {HTTPStatus.SERVICE_UNAVAILABLE: "Livestatus is down."},
        {},
    )

    assert (
        responses[HTTPStatus.SERVICE_UNAVAILABLE]["description"]
        == "Service Unavailable: Livestatus is down."
    )
