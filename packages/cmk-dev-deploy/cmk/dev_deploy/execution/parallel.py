# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""DAG-based parallel deployment engine using topological sorting."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import as_completed, Future, ThreadPoolExecutor
from dataclasses import dataclass
from graphlib import TopologicalSorter

from cmk.dev_deploy.types import StepResult


@dataclass(frozen=True)
class DeployStep:
    """A single unit of deployment work in the DAG."""

    name: str
    action: Callable[[], str | None]
    depends_on: tuple[str, ...] = ()


def execute_parallel(
    steps: list[DeployStep],
    max_workers: int = 4,
) -> list[StepResult]:
    """Execute deployment steps wave-by-wave respecting dependency ordering.

    Failed steps cause all transitive dependents to be marked as failed.
    """
    if not steps:
        return []

    # Build dependency graph and action lookup
    graph: dict[str, set[str]] = {step.name: set(step.depends_on) for step in steps}
    actions: dict[str, Callable[[], str | None]] = {
        step.name: step.action for step in steps
    }

    ts = TopologicalSorter(graph)
    ts.prepare()  # raises CycleError if circular

    results: list[StepResult] = []
    failed_names: set[str] = set()
    cycle_start = time.monotonic()

    # Spinner for visual progress on TTY
    from cmk.dev_deploy.core.output import Spinner

    spinner = Spinner()
    spinner.start()
    from cmk.dev_deploy.core.output import clear_active_spinner, set_active_spinner

    set_active_spinner(spinner)

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            while ts.is_active():
                ready = ts.get_ready()
                if not ready:
                    break  # safety: avoid infinite loop

                # Partition ready steps into runnable vs dependency-failed
                futures: dict[Future[StepResult], str] = {}
                for name in ready:
                    # Check whether any dependency (transitively) failed
                    if graph[name] & failed_names:
                        results.append(
                            StepResult(
                                name=name,
                                success=False,
                                message="skipped: dependency failed",
                                elapsed=0.0,
                            )
                        )
                        failed_names.add(name)
                        ts.done(name)
                    else:
                        spinner.add_label(name)
                        futures[
                            pool.submit(_run_step, name, actions[name], cycle_start)
                        ] = name

                # Wait for all futures in this wave
                wave_results: list[StepResult] = []
                for future in as_completed(futures):
                    name = futures[future]
                    step_result: StepResult = future.result()
                    wave_results.append(step_result)
                    spinner.remove_label(name)
                    if not step_result.success:
                        failed_names.add(name)
                    ts.done(name)

                # Flush captured output per-wave in deterministic (alphabetical) order
                from cmk.dev_deploy.core.output import write_buffered_output

                spinner.pause()
                for wr in sorted(wave_results, key=lambda r: r.name):
                    if wr.captured_output:
                        write_buffered_output(list(wr.captured_output))
                spinner.resume()

                results.extend(wave_results)
    finally:
        clear_active_spinner()
        spinner.stop()

    return results


def _run_step(
    name: str, action: Callable[[], str | None], cycle_start: float
) -> StepResult:
    """Execute a single step action, capturing timing, output, and exceptions."""
    from cmk.dev_deploy.core.output import flush_buffer, start_buffering

    start_buffering()
    t0 = time.monotonic()
    start_offset = t0 - cycle_start
    try:
        message = action()
        elapsed = time.monotonic() - t0
        captured = flush_buffer()
        return StepResult(
            name=name,
            success=True,
            message=message,
            elapsed=elapsed,
            start_offset=start_offset,
            captured_output=tuple(tuple(e) for e in captured),
        )
    except Exception as exc:
        elapsed = time.monotonic() - t0
        captured = flush_buffer()
        return StepResult(
            name=name,
            success=False,
            message=str(exc),
            elapsed=elapsed,
            start_offset=start_offset,
            captured_output=tuple(tuple(e) for e in captured),
        )
