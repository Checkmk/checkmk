#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.gui.auth import _check_internal_token
from cmk.gui.pseudo_users import SiteInternalPseudoUser
from cmk.utils.local_secrets import SiteInternalSecret


def test_check_internal_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mocked_secret_path = tmp_path / "siteinternal.secret"
    mocked_secret_path.write_bytes(b"unittestsecret")
    monkeypatch.setattr(SiteInternalSecret, "path", mocked_secret_path)

    class _RequestMock:
        environ: dict[str, str] = {}

    with patch("cmk.gui.auth.request", _RequestMock()) as request:
        assert _check_internal_token() is None

        request.environ["HTTP_AUTHORIZATION"] = "Zm9v"  # foo
        assert _check_internal_token() is None

        request.environ["HTTP_AUTHORIZATION"] = "InternalToken foo"  # invalid base64
        assert _check_internal_token() is None

        request.environ["HTTP_AUTHORIZATION"] = "InternalToken Zm9v"
        assert _check_internal_token() is None

        request.environ["HTTP_AUTHORIZATION"] = (
            "InternalToken dW5pdHRlc3RzZWNyZXQ="  # unittestsecret
        )
        assert isinstance(_check_internal_token(), SiteInternalPseudoUser)
