#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import traceback
from contextlib import contextmanager
from subprocess import CalledProcessError
from typing import Any

import pytest

from tests.testlib import pytest_helpers
from tests.testlib.utils import verbose_called_process_error


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
def exit_pytest_on_exceptions(
    exceptions: tuple[type[BaseException]] | None = None, exit_msg: str = ""
) -> Any:
    exceptions = (BaseException,) if exceptions is None else exceptions
    msg = f"{exit_msg}\n"
    try:
        yield
    except exceptions as excp:
        msg += _exception_traceback(excp)
        # TODO: find a way to trigger teardown.
        pytest.exit(msg, returncode=3)


def _exception_traceback(excp: BaseException) -> str:
    """Return a message consisting of an exception's traceback and notes.

    The message consists of the raised exception and it's `__cause__`s.
    Additionally, messages for `CalledProcessError` also include `stdout` and `stderr` information.
    """
    msg = [f"> Details of '{excp.__class__.__name__}'"]
    msg += traceback.format_exception(excp)
    if isinstance(excp, CalledProcessError):
        excp.add_note(verbose_called_process_error(excp))
    msg.append("Notes:")
    msg += getattr(excp, "__notes__", ["None"])

    if excp.__cause__:
        msg.append("-" * 80)
        msg.append(_exception_traceback(excp.__cause__))

    return "\n".join(msg)
