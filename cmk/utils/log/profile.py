#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A helper module for profiling code through logging."""

import time
from collections.abc import Callable
from logging import Logger
from typing import Literal


def log_duration[**P, R](
    *,
    logger: Logger,
    level: Literal["debug", "info", "warning", "critical"],
    print_params: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator factory for logging how long a function takes to run.

    A common pattern for this utility would be to create an instance in your package that
    wraps the local logger:

    >>> import logging
    >>> log_duration_debug = log_duration(logger=logging.getLogger("fetcher"), level="debug")

    Here we are specifying the log level, but you could make this a partial and then pass the log
    level later. With the decorator instance, you can wrap the function definition like so:

    >>> @log_duration_debug
    ... def fetch_site_names() -> list[str]:
    ...     return ["heute"]

    Calling `fetch_site_names()` will then produce the following log output:

    ```
    CALLING path.to.module.fetch_site_names …
    FINISHED path.to.module.fetch_site_names (3.02142s)
    ```

    Alternatively, you can wrap an existing function like a builtin function or third party library:

    >>> log_duration_debug(len)(fetch_site_names())
    1

    This call outputs the following log:

    ```
    CALLING builtins.len …
    CALLING path.to.module.fetch_site_names …
    FINISHED path.to.module.fetch_site_names (3.02142s)
    FINISHED builtins.len (1.03982s)
    ```

    If you want to see what parameters were passed to the function, set the `print_params=True`.

    The main goal of this utility is to offer an easy, consistent way to log the duration of known
    bottlenecks in the source code. This decorator may also be useful to you when debugging a live
    system on the customer side.
    """
    if level not in {"debug", "info", "warning", "critical"}:
        raise ValueError(f"Invalid log level passed: {level!r}")

    log = getattr(logger, level)

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            fn_module_path = f"{fn.__module__}.{fn.__qualname__}"

            log(f"CALLING {fn_module_path} …")

            if print_params:
                if args:
                    log(f"ARGS {fn_module_path}: {args}")
                if kwargs:
                    log(f"KWARGS {fn_module_path}: {kwargs}")

            start = time.perf_counter()
            result = fn(*args, **kwargs)
            duration = time.perf_counter() - start

            log(f"FINISHED {fn_module_path} ({duration:.5f}s)")

            return result

        return wrapper

    return decorator
