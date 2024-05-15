#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pydantic import UUID4

from cmk.agent_receiver.certs import serialize_to_pem
from cmk.agent_receiver.models import CsrField

from .certs import generate_csr_pair


class TestCsrField:
    def test_validate_ok(self, uuid: UUID4) -> None:
        _key, csr = generate_csr_pair(str(uuid))
        CsrField.validate(serialize_to_pem(csr))

    def test_validate_cn_no_uuid(self) -> None:
        _key, csr = generate_csr_pair("no_uuid")
        with pytest.raises(ValueError, match="is not a valid version-4 UUID"):
            CsrField.validate(serialize_to_pem(csr))
