#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module is intended for utility functions. Currently, in contains only one function
for waiting until a condition is met.

Note: this module can be used both in unit and system-level tests.
"""

import contextlib
import logging
import time
from collections.abc import Callable, Iterable, Iterator

from cmk.ccc.plugin_registry import Registry

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def reset_registries[T](registries: Iterable[Registry[T]]) -> Iterator[None]:
    """Reset the given registries after completing"""
    defaults_per_registry = [(registry, list(registry)) for registry in registries]
    try:
        yield
    finally:
        for registry, defaults in defaults_per_registry:
            for entry in list(registry):
                if entry not in defaults:
                    registry.unregister(entry)


def wait_until(
    condition: Callable[[], bool],
    timeout: float = 1,
    interval: float = 0.1,
    condition_name: str = "",
) -> None:
    """Waits until a given condition is met (or timeout was reached -> TimeoutError).

    Args:
        condition (Callable[[], bool]): condition to be met. Will be called repeatedly until true.
        timeout (float, optional): Timeout in seconds. Defaults to 1.
        interval (float, optional): Time to wait (sleep) between checks. Defaults to 0.1.
        condition_name (str, optional): Name of the condition. Used for logging.

    Raises:
        TimeoutError: If the condition was not met within the given timeout.
    """
    condition_name = condition_name or repr(condition)

    start = now = time.time()
    logger.info("Waiting for '%s' to finish for %ds", condition_name, timeout)
    while now - start <= timeout:
        if condition():
            logger.info("Wait for '%s' finished after %0.2fs", condition_name, now - start)
            return
        time.sleep(interval)
        now = time.time()

    error_message = f"Timeout waiting for '{condition_name}' to finish (Timeout: {timeout} sec)"
    logger.error(error_message)
    raise TimeoutError(error_message)
