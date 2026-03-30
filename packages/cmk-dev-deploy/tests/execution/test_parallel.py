# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.parallel: parallel execution engine and output ordering."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixture: reset buffering state after each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_output_config() -> Iterator[None]:
    """Reset all output configuration before and after each test."""
    from cmk.dev_deploy.core.output import reset

    reset()
    yield
    reset()


# ---------------------------------------------------------------------------
# TestExecuteParallel (basic engine tests)
# ---------------------------------------------------------------------------


class TestExecuteParallel:
    """Basic parallel execution engine tests."""

    def test_empty_steps_returns_empty(self) -> None:
        """execute_parallel([]) returns an empty list."""
        from cmk.dev_deploy.execution.parallel import execute_parallel

        results = execute_parallel([])
        assert results == []

    def test_single_step_succeeds(self) -> None:
        """A single step that returns 'ok' produces a successful StepResult."""
        from cmk.dev_deploy.execution.parallel import DeployStep, execute_parallel

        step = DeployStep(name="only", action=lambda: "ok")
        results = execute_parallel([step])
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].message == "ok"
        assert results[0].elapsed > 0

    def test_dependency_ordering(self) -> None:
        """Step B depends on Step A; A must complete before B starts."""
        from cmk.dev_deploy.execution.parallel import DeployStep, execute_parallel

        order: list[str] = []

        def action_a() -> str:
            order.append("A")
            time.sleep(0.05)
            return "a-done"

        def action_b() -> str:
            order.append("B")
            return "b-done"

        steps = [
            DeployStep(name="step_a", action=action_a),
            DeployStep(name="step_b", action=action_b, depends_on=("step_a",)),
        ]
        results = execute_parallel(steps, max_workers=4)

        assert len(results) == 2
        assert order.index("A") < order.index("B"), f"Expected A before B, got: {order}"

    def test_failed_step_cascades(self) -> None:
        """When Step A fails, Step B (which depends on A) is marked as failed."""
        from cmk.dev_deploy.execution.parallel import DeployStep, execute_parallel

        def action_a() -> str:
            raise RuntimeError("boom")

        def action_b() -> str:
            return "b-done"

        steps = [
            DeployStep(name="step_a", action=action_a),
            DeployStep(name="step_b", action=action_b, depends_on=("step_a",)),
        ]
        results = execute_parallel(steps, max_workers=4)

        result_map = {r.name: r for r in results}
        assert result_map["step_a"].success is False
        assert "boom" in (result_map["step_a"].message or "")
        assert result_map["step_b"].success is False
        assert "dependency failed" in (result_map["step_b"].message or "")

    def test_max_workers_1_sequential(self) -> None:
        """Three independent steps with max_workers=1 all complete."""
        from cmk.dev_deploy.execution.parallel import DeployStep, execute_parallel

        def make_action(idx: int) -> Callable[[], str]:
            def action() -> str:
                return f"done-{idx}"

            return action

        steps = [DeployStep(name=f"step_{i}", action=make_action(i)) for i in range(3)]
        results = execute_parallel(steps, max_workers=1)

        assert len(results) == 3
        assert all(r.success for r in results)


# ---------------------------------------------------------------------------
# TestOutputOrdering (OUT-01 verification)
# ---------------------------------------------------------------------------


class TestOutputOrdering:
    """Verify contiguous per-deployer output blocks (OUT-01)."""

    def test_output_not_interleaved(self) -> None:
        """Three steps each emit identifiable lines; their output blocks must be contiguous.

        Each step calls output.info() with step-specific prefixed messages.
        After execute_parallel(), we verify that all lines from each step
        appear in a contiguous subsequence (no other step's lines between them).
        """
        from cmk.dev_deploy.execution.parallel import DeployStep, execute_parallel

        printed_lines: list[str] = []

        def make_action(label: str) -> Callable[[], str]:
            def action() -> str:
                from cmk.dev_deploy.core import output

                output.info(f"{label}-line-1")
                time.sleep(0.05)
                output.info(f"{label}-line-2")
                output.info(f"{label}-line-3")
                return f"{label}-done"

            return action

        steps = [
            DeployStep(name=f"step_{label}", action=make_action(label))
            for label in ("A", "B", "C")
        ]

        with patch(
            "builtins.print", side_effect=lambda msg, **_kw: printed_lines.append(msg)
        ):
            execute_parallel(steps, max_workers=3)

        # Verify each step's lines appear contiguously
        for label in ("A", "B", "C"):
            indices = [
                i for i, line in enumerate(printed_lines) if f"{label}-line-" in line
            ]
            assert len(indices) == 3, (
                f"Expected 3 lines for step {label}, found {len(indices)} in: {printed_lines}"
            )
            # Contiguity check: indices should be consecutive
            assert indices == list(range(indices[0], indices[0] + 3)), (
                f"Step {label} lines are not contiguous. Indices: {indices}, all lines: {printed_lines}"
            )

    def test_sequential_output_order_matches(self) -> None:
        """With max_workers=1, output appears in dependency/wave order.

        Steps in wave 1 should produce output before wave 2 steps.
        """
        from cmk.dev_deploy.execution.parallel import DeployStep, execute_parallel

        printed_lines: list[str] = []

        def make_action(label: str) -> Callable[[], str]:
            def action() -> str:
                from cmk.dev_deploy.core import output

                output.info(f"{label}-seq-line")
                return f"{label}-done"

            return action

        # step_a and step_b are independent (wave 1); step_c depends on both (wave 2)
        steps = [
            DeployStep(name="step_a", action=make_action("A")),
            DeployStep(name="step_b", action=make_action("B")),
            DeployStep(
                name="step_c", action=make_action("C"), depends_on=("step_a", "step_b")
            ),
        ]

        with patch(
            "builtins.print", side_effect=lambda msg, **_kw: printed_lines.append(msg)
        ):
            execute_parallel(steps, max_workers=1)

        # Find indices for each step's output
        idx_a = next(i for i, line in enumerate(printed_lines) if "A-seq-line" in line)
        idx_b = next(i for i, line in enumerate(printed_lines) if "B-seq-line" in line)
        idx_c = next(i for i, line in enumerate(printed_lines) if "C-seq-line" in line)

        # Wave 1 (A, B) must appear before wave 2 (C)
        assert idx_a < idx_c, f"A ({idx_a}) should appear before C ({idx_c})"
        assert idx_b < idx_c, f"B ({idx_b}) should appear before C ({idx_c})"


# ---------------------------------------------------------------------------
# TestStepResultCapturedOutput
# ---------------------------------------------------------------------------


class TestStepResultCapturedOutput:
    """Verify captured_output field on StepResult."""

    def test_captured_output_field_exists(self) -> None:
        """StepResult has a captured_output field with default empty tuple."""
        from cmk.dev_deploy.types import StepResult

        result = StepResult(name="test", success=True, message=None, elapsed=0.0)
        assert result.captured_output == ()

    def test_captured_output_populated_by_execution(self) -> None:
        """Running a step that calls output.info() populates captured_output."""
        from cmk.dev_deploy.execution.parallel import DeployStep, execute_parallel

        def action() -> str:
            from cmk.dev_deploy.core import output

            output.info("buffered")
            return "done"

        steps = [DeployStep(name="producer", action=action)]

        with patch("builtins.print"):
            results = execute_parallel(steps)

        assert len(results) == 1
        assert len(results[0].captured_output) > 0
        # At least one captured entry should contain "buffered"
        all_msgs = [msg for msg, _file in results[0].captured_output]
        assert any("buffered" in msg for msg in all_msgs)


# ---------------------------------------------------------------------------
# TestWaveFlushOrdering (OUT-02 verification)
# ---------------------------------------------------------------------------


class TestWaveFlushOrdering:
    """Verify wave output is flushed after wave completes."""

    def test_wave_output_flushed_after_wave_completes(self) -> None:
        """Steps in 2 waves produce output; wave 1 output appears before wave 2.

        Wave 1: step_a, step_b (independent)
        Wave 2: step_c (depends on both)

        Output from wave 1 steps must appear before wave 2 step output.
        """
        from cmk.dev_deploy.execution.parallel import DeployStep, execute_parallel

        printed_lines: list[str] = []

        def make_action(label: str) -> Callable[[], str]:
            def action() -> str:
                from cmk.dev_deploy.core import output

                output.info(f"wave-{label}-output")
                time.sleep(0.05)
                return f"{label}-done"

            return action

        steps = [
            DeployStep(name="step_a", action=make_action("A")),
            DeployStep(name="step_b", action=make_action("B")),
            DeployStep(
                name="step_c", action=make_action("C"), depends_on=("step_a", "step_b")
            ),
        ]

        with patch(
            "builtins.print", side_effect=lambda msg, **_kw: printed_lines.append(msg)
        ):
            execute_parallel(steps, max_workers=3)

        # Find the last wave-1 line and first wave-2 line
        wave1_indices = [
            i
            for i, line in enumerate(printed_lines)
            if "wave-A-output" in line or "wave-B-output" in line
        ]
        wave2_indices = [
            i for i, line in enumerate(printed_lines) if "wave-C-output" in line
        ]

        assert wave1_indices, f"Expected wave 1 output, got: {printed_lines}"
        assert wave2_indices, f"Expected wave 2 output, got: {printed_lines}"

        last_wave1 = max(wave1_indices)
        first_wave2 = min(wave2_indices)

        assert last_wave1 < first_wave2, (
            f"Wave 1 output (last at {last_wave1}) should appear before "
            f"wave 2 output (first at {first_wave2}). Lines: {printed_lines}"
        )
