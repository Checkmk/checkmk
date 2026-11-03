#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import threading

from cmk.plugins.aws_v2.special_agent.job_pool import JobPool


def _submit_in_the_background(pool: JobPool) -> threading.Thread:
    submitter = threading.Thread(target=pool.submit, args=(lambda: None,), daemon=True)
    submitter.start()
    return submitter


def _fail() -> None:
    raise RuntimeError("job failed")


def test_submit_waits_while_every_thread_is_busy() -> None:
    release = threading.Event()
    with JobPool(1) as pool:
        pool.submit(release.wait)
        submitter = _submit_in_the_background(pool)
        submitter.join(timeout=0.05)
        waited = submitter.is_alive()
        release.set()
        submitter.join()

    assert waited


def test_submit_goes_on_once_a_job_is_done() -> None:
    with JobPool(1) as pool:
        pool.submit(lambda: None).result()
        submitter = _submit_in_the_background(pool)
        submitter.join(timeout=1)

        assert not submitter.is_alive()


def test_slot_takes_a_thread_for_work_in_the_caller() -> None:
    with JobPool(1) as pool:
        with pool.slot():
            submitter = _submit_in_the_background(pool)
            submitter.join(timeout=0.05)
            waited = submitter.is_alive()
        submitter.join()

    assert waited


def test_failing_job_frees_its_thread() -> None:
    with JobPool(1) as pool:
        pool.submit(_fail).exception()
        submitter = _submit_in_the_background(pool)
        submitter.join(timeout=1)

        assert not submitter.is_alive()
