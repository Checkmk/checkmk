# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.output: combined mode prefixing, timing display, and output buffering."""

from __future__ import annotations

import sys
import threading
from collections.abc import Iterator
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixture: reset all output state before and after each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_output_config() -> Iterator[None]:
    """Reset all output configuration before and after each test."""
    from cmk.dev_deploy.core.output import reset

    reset()
    yield
    reset()


# ---------------------------------------------------------------------------
# TestDeployPrefix
# ---------------------------------------------------------------------------


class TestDeployPrefix:
    """_deploy_prefix() returns the [deploy] prefix conditionally."""

    def test_returns_empty_when_default(self) -> None:
        from cmk.dev_deploy.core.output import _deploy_prefix

        assert _deploy_prefix() == ""

    def test_returns_prefix_when_combined_mode(self) -> None:
        from cmk.dev_deploy.core.output import _deploy_prefix, set_combined_mode

        set_combined_mode(True)
        result = _deploy_prefix()
        assert "[deploy]" in result
        assert result.endswith(" ")

    def test_toggle_on_off(self) -> None:
        from cmk.dev_deploy.core.output import _deploy_prefix, set_combined_mode

        set_combined_mode(True)
        assert "[deploy]" in _deploy_prefix()
        set_combined_mode(False)
        assert _deploy_prefix() == ""


# ---------------------------------------------------------------------------
# TestInfoWithPrefix
# ---------------------------------------------------------------------------


class TestInfoWithPrefix:
    """info() output includes [deploy] only when combined mode is on."""

    def test_info_no_prefix_by_default(self) -> None:
        from cmk.dev_deploy.core.output import info

        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            info("hello world")
            call_text = mock_print.call_args[0][0]
            assert "[deploy]" not in call_text
            assert "[info]" in call_text
            assert "hello world" in call_text

    def test_info_with_deploy_prefix(self) -> None:
        from cmk.dev_deploy.core.output import info, set_combined_mode

        set_combined_mode(True)
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            info("deploying files")
            call_text = mock_print.call_args[0][0]
            assert "[deploy]" in call_text
            assert "[info]" in call_text
            assert "deploying files" in call_text


# ---------------------------------------------------------------------------
# TestWarnWithPrefix
# ---------------------------------------------------------------------------


class TestWarnWithPrefix:
    """warn() output includes [deploy] on stderr in combined mode."""

    def test_warn_no_prefix_by_default(self) -> None:
        from cmk.dev_deploy.core.output import warn

        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            warn("something off")
            call_text = mock_print.call_args[0][0]
            assert "[deploy]" not in call_text
            assert "[warn]" in call_text
            # Verify it writes to stderr
            assert mock_print.call_args[1].get("file") is sys.stderr

    def test_warn_with_deploy_prefix(self) -> None:
        from cmk.dev_deploy.core.output import set_combined_mode, warn

        set_combined_mode(True)
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            warn("caution")
            call_text = mock_print.call_args[0][0]
            assert "[deploy]" in call_text
            assert "[warn]" in call_text


# ---------------------------------------------------------------------------
# TestErrorWithPrefix
# ---------------------------------------------------------------------------


class TestErrorWithPrefix:
    """error() output includes [deploy] on stderr in combined mode."""

    def test_error_with_deploy_prefix(self) -> None:
        from cmk.dev_deploy.core.output import error, set_combined_mode

        set_combined_mode(True)
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            error("failure")
            call_text = mock_print.call_args[0][0]
            assert "[deploy]" in call_text
            assert "[error]" in call_text


# ---------------------------------------------------------------------------
# TestSuccessWithPrefix
# ---------------------------------------------------------------------------


class TestSuccessWithPrefix:
    """success() output includes [deploy] in combined mode."""

    def test_success_with_deploy_prefix(self) -> None:
        from cmk.dev_deploy.core.output import set_combined_mode, success

        set_combined_mode(True)
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            success("done")
            call_text = mock_print.call_args[0][0]
            assert "[deploy]" in call_text
            assert "[ok]" in call_text


# ---------------------------------------------------------------------------
# TestDeployerOutputWithPrefix
# ---------------------------------------------------------------------------


class TestDeployerOutputWithPrefix:
    """Deployer output lines include [deploy] prefix in combined mode."""

    def test_deployer_deployed_with_prefix(self) -> None:
        from cmk.dev_deploy.core.output import (
            print_deployer_deployed,
            set_combined_mode,
        )

        set_combined_mode(True)
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            print_deployer_deployed("python", 1.2, "3 deployed")
            call_text = mock_print.call_args[0][0]
            assert "[deploy]" in call_text
            assert "python" in call_text
            assert "deployed" in call_text

    def test_deployer_deployed_no_prefix_default(self) -> None:
        from cmk.dev_deploy.core.output import print_deployer_deployed

        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            print_deployer_deployed("python", 1.2)
            call_text = mock_print.call_args[0][0]
            assert "[deploy]" not in call_text

    def test_deployer_skipped_with_prefix(self) -> None:
        from cmk.dev_deploy.core.output import (
            print_deployer_skipped_line,
            set_combined_mode,
        )

        set_combined_mode(True)
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            print_deployer_skipped_line("config", "no changes")
            call_text = mock_print.call_args[0][0]
            assert "[deploy]" in call_text
            assert "skipped" in call_text


# ---------------------------------------------------------------------------
# TestDefaultModeNoPrefixes
# ---------------------------------------------------------------------------


class TestDefaultModeNoPrefixes:
    """Backend-only default mode produces zero [deploy] prefixes (regression test)."""

    def test_no_deploy_prefix_in_default_mode(self) -> None:
        """Verify that common output calls produce no [deploy] prefix when
        combined mode is not enabled (the default for backend-only usage)."""
        from cmk.dev_deploy.core.output import (
            _config,
            info,
            success,
            warn,
        )

        # Verify module default
        assert _config.combined_mode is False

        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            info("test message")
            warn("test warning")
            success("test ok")

            for call_obj in mock_print.call_args_list:
                assert "[deploy]" not in call_obj[0][0], (
                    f"Found [deploy] prefix in default mode: {call_obj[0][0]}"
                )


# ---------------------------------------------------------------------------
# TestPrintDeployTotal
# ---------------------------------------------------------------------------


class TestPrintDeployTotal:
    """print_deploy_total() always prints total deploy time."""

    def test_always_visible_at_default_verbosity(self) -> None:
        """print_deploy_total produces output at DEFAULT verbosity."""
        from cmk.dev_deploy.core.output import print_deploy_total

        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            print_deploy_total(3.7)
            assert mock_print.call_count >= 1
            text = mock_print.call_args[0][0]
            assert "Deploy complete" in text
            assert "3.7s" in text

    def test_combined_mode_includes_deploy_prefix(self) -> None:
        """print_deploy_total includes [deploy] prefix when combined mode is active."""
        from cmk.dev_deploy.core.output import print_deploy_total, set_combined_mode

        set_combined_mode(True)
        with patch("cmk.dev_deploy.core.output._print_locked") as mock_print:
            print_deploy_total(2.1)
            text = mock_print.call_args[0][0]
            assert "[deploy]" in text
            assert "Deploy complete" in text
            assert "2.1s" in text


# ---------------------------------------------------------------------------
# TestPrintTimingSummaryGating
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TestOutputBuffer
# ---------------------------------------------------------------------------


class TestOutputBuffer:
    """Tests for the thread-local output buffering infrastructure."""

    def test_buffering_captures_instead_of_printing(self) -> None:
        """start_buffering() causes info() to buffer instead of printing to stdout."""
        from cmk.dev_deploy.core.output import flush_buffer, info, start_buffering

        start_buffering()
        with patch("builtins.print") as mock_print:
            info("hello")
            # Nothing should have been printed to stdout
            mock_print.assert_not_called()

        entries = flush_buffer()
        assert len(entries) >= 1
        # At least one entry should contain "hello"
        all_msgs = [msg for msg, _file in entries]
        assert any("hello" in msg for msg in all_msgs)

    def test_flush_returns_entries_and_clears(self) -> None:
        """flush_buffer() returns accumulated entries, then returns empty on second call."""
        from cmk.dev_deploy.core.output import (
            flush_buffer,
            info,
            start_buffering,
            success,
            warn,
        )

        start_buffering()
        info("msg1")
        warn("msg2")
        success("msg3")

        entries = flush_buffer()
        assert len(entries) == 3

        # Second flush should return empty (buffer was cleared)
        entries2 = flush_buffer()
        assert entries2 == []

    def test_no_buffering_prints_immediately(self) -> None:
        """Without start_buffering(), info() delegates to _print_locked which prints."""
        from cmk.dev_deploy.core.output import info

        with patch("cmk.dev_deploy.core.output._print_locked") as mock_pl:
            info("direct")
            mock_pl.assert_called_once()
            assert "direct" in mock_pl.call_args[0][0]

    def test_stderr_entries_preserved(self) -> None:
        """warn() and error() entries preserve file=sys.stderr in the buffer tuple."""
        from cmk.dev_deploy.core.output import (
            error,
            flush_buffer,
            start_buffering,
            warn,
        )

        start_buffering()
        warn("oops")
        error("fail")

        entries = flush_buffer()
        assert len(entries) == 2
        # Both entries should have sys.stderr as the file argument
        for _msg, file in entries:
            assert file is sys.stderr

    def test_write_buffered_output_prints_all_atomically(self) -> None:
        """write_buffered_output() prints all entries under a single lock acquisition.

        Verifies atomicity by replacing _OUTPUT_LOCK with a counting wrapper
        that tracks how many times the lock context is entered.
        """
        import cmk.dev_deploy.core.output as output_mod
        from cmk.dev_deploy.core.output import write_buffered_output

        entries: list[tuple[str, object]] = [(f"line-{i}", None) for i in range(5)]

        acquire_count = 0
        real_lock = threading.Lock()

        class CountingLock:
            """A lock wrapper that counts context-manager entries."""

            def __enter__(self) -> bool:
                nonlocal acquire_count
                acquire_count += 1
                return real_lock.__enter__()

            def __exit__(self, *args: object) -> None:
                return real_lock.__exit__(*args)  # type: ignore[arg-type]

            def acquire(self, *args: object, **kwargs: object) -> bool:
                nonlocal acquire_count
                acquire_count += 1
                return real_lock.acquire(*args, **kwargs)  # type: ignore[arg-type]

            def release(self) -> None:
                return real_lock.release()

        original_lock = output_mod._config.output_lock  # noqa: SLF001
        output_mod._config.output_lock = CountingLock()  # type: ignore[assignment]  # noqa: SLF001
        try:
            with patch("builtins.print") as mock_print:
                write_buffered_output(entries)
        finally:
            output_mod._config.output_lock = original_lock  # noqa: SLF001

        # Lock should have been acquired exactly once (atomic batch)
        assert acquire_count == 1
        # All 5 lines should have been printed
        assert mock_print.call_count == 5
        for i in range(5):
            assert f"line-{i}" in mock_print.call_args_list[i][0][0]

    def test_thread_isolation(self) -> None:
        """Two threads buffering independently see only their own entries."""
        from cmk.dev_deploy.core.output import flush_buffer, info, start_buffering

        results_a: list[tuple[str, object]] = []
        results_b: list[tuple[str, object]] = []

        def thread_a() -> None:
            start_buffering()
            info("A1")
            info("A2")
            results_a.extend(flush_buffer())

        def thread_b() -> None:
            start_buffering()
            info("B1")
            info("B2")
            results_b.extend(flush_buffer())

        ta = threading.Thread(target=thread_a)
        tb = threading.Thread(target=thread_b)
        ta.start()
        tb.start()
        ta.join(timeout=5)
        tb.join(timeout=5)

        # Thread A should only have A entries
        a_msgs = [msg for msg, _file in results_a]
        assert len(a_msgs) == 2
        assert all("A" in msg for msg in a_msgs)
        assert not any("B" in msg for msg in a_msgs)

        # Thread B should only have B entries
        b_msgs = [msg for msg, _file in results_b]
        assert len(b_msgs) == 2
        assert all("B" in msg for msg in b_msgs)
        assert not any("A" in msg for msg in b_msgs)

    def test_buffering_off_by_default(self) -> None:
        """Thread-local buffering flag is False by default on a fresh thread."""
        from cmk.dev_deploy.core.output import _config

        result: list[bool] = []

        def check_default() -> None:
            # Fresh thread -- thread_local should not have buffering set to True
            result.append(getattr(_config.thread_local, "buffering", False))

        t = threading.Thread(target=check_default)
        t.start()
        t.join(timeout=5)

        assert result == [False]
