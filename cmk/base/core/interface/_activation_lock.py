#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager
from typing import assert_never, Literal

import cmk.utils.paths
from cmk.ccc.store import locked, try_locked
from cmk.config.paths import BaseConfigurationMKFiles

# TODO: We really should purge this strange case from being configurable
# None: No locking at all.
type LockingMode = Literal["abort", "wait"] | None


class ActivationLockedError(Exception):
    """The activation lock is held by another process"""


# TODO: lock_checkmk_configuration is doing something similar. It looks like we
# should unify these both locks. But: The lock_checkmk_configuration is currently acquired by the
# GUI process. In case the GUI calls an automation process, we would have a dead lock of these two
# processes. We'll have to check whether or not we can move the locking.
@contextmanager
def activation_lock(mode: LockingMode) -> Iterator[None]:
    """Hold the activation lock, raise ActivationLockedError if mode is "abort" and it is taken

    The lock guards the creation and activation of the monitoring configuration.
    """
    main_mk_file = BaseConfigurationMKFiles.from_omd_root(cmk.utils.paths.omd_root).main_mk
    match mode:
        case None:
            yield None  # No locking at all
            return

        case "abort":
            with try_locked(main_mk_file) as result:
                if result is False:
                    raise ActivationLockedError("Other restart currently in progress. Aborting.")
                yield None
            return

        case "wait":
            with locked(main_mk_file):
                yield None
            return

        case _:
            assert_never(mode)
