#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager, ExitStack

from cmk.ccc import store
from cmk.gui.exceptions import RequestTimeout
from cmk.gui.i18n import _
from cmk.utils.paths import configuration_lockfile


@contextmanager
def lock_checkmk_configuration() -> Iterator[None]:
    """Lock the Checkmk configuration against concurrent changes

    Waiting for the lock can only be interrupted by the timeout of a GUI request. Tell the user
    that it was the lock they were waiting for, rather than an expensive request.
    """
    with ExitStack() as stack:
        try:
            stack.enter_context(store.lock_checkmk_configuration(configuration_lockfile))
        except RequestTimeout as e:
            raise RequestTimeout(
                _(
                    "Couldn't lock the Checkmk configuration. Another "
                    "process is running that holds this lock. In order for you to be "
                    "able to perform the desired action, you have to wait until the "
                    "other process has finished. Please try again later."
                )
            ) from e
        yield
