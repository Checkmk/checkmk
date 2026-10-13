# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
import subprocess

from bazel_devserver import process_tree


def test_kill_group_of_spares_a_later_process_of_the_same_pid() -> None:
    with subprocess.Popen(["sleep", "60"], start_new_session=True) as later:
        started = process_tree.start_time(later.pid)
        assert started is not None

        process_tree.kill_group_of(process_tree.Process(later.pid, started - 1))
        later.terminate()

        assert later.wait(timeout=5) == -signal.SIGTERM
