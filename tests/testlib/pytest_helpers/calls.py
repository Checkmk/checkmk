#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import contextmanager
from typing import Any

import pytest

from tests.testlib import pytest_helpers


def abort_if_not_containerized(condition: bool = True) -> None:
    if pytest_helpers.not_containerized.condition and condition:
        pytest.skip(pytest_helpers.not_containerized.reason)


def abort_if_not_cloud_edition(condition: bool = True) -> None:
    if pytest_helpers.not_cloud_edition.condition and condition:
        pytest.skip(pytest_helpers.not_cloud_edition.reason)


def abort_if_raw_edition(condition: bool = True) -> None:
    if pytest_helpers.is_raw_edition.condition and condition:
        pytest.skip(pytest_helpers.is_raw_edition.reason)


def abort_if_saas_edition(condition: bool = True) -> None:
    if pytest_helpers.is_saas_edition.condition and condition:
        pytest.skip(pytest_helpers.is_saas_edition.reason)


@contextmanager
def exit_pytest_on_exceptions(exceptions: tuple[Any, ...] | None = None, exit_msg: str = "") -> Any:
    if exceptions is None:
        exceptions = (Exception,)
    try:
        yield
    except exceptions as excp:
        pytest.exit(f"{exit_msg}\n{str(excp)}", returncode=1)
