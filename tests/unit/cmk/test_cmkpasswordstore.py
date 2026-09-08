#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from io import StringIO
from unittest.mock import patch

import pytest

from cmk.utils.password_store import pending_secrets_path_site, save
from cmk.utils.password_store.cli import main


@pytest.mark.usefixtures("tmp_path")
def test_cmkpasswordstore_existing_password() -> None:
    password_id = "test_id"
    expected_password = "secret_password"

    save({password_id: expected_password}, pending_secrets_path_site())

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        exit_code = main(["--lookup", password_id])

        assert exit_code == 0
        assert mock_stdout.getvalue() == expected_password


@pytest.mark.usefixtures("tmp_path")
def test_cmkpasswordstore_missing_password() -> None:
    password_id = "test_id"

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        exit_code = main(["--lookup", password_id])

        assert exit_code == 1
        assert mock_stdout.getvalue() == ""
