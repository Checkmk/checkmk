#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cmk.utils.password_store import pending_password_store_path, save
from cmk.utils.password_store.cli import main


def test_cmkpasswordstore_existing_password(tmp_path: Path) -> None:
    password_id = "test_id"
    expected_password = "secret_password"

    save({password_id: expected_password}, pending_password_store_path())

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        exit_code = main(["--lookup", password_id])

        assert exit_code == 0
        assert mock_stdout.getvalue() == expected_password


def test_cmkpasswordstore_missing_password(tmp_path: Path) -> None:
    password_id = "test_id"

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        exit_code = main(["--lookup", password_id])

        assert exit_code == 1
        assert mock_stdout.getvalue() == ""
