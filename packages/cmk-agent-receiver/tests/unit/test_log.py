#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextvars
import logging

import pytest
from _pytest.logging import LogCaptureFixture

from cmk.agent_receiver import log as logger


@pytest.fixture
def logger_with_context() -> logging.Logger:
    """Logger configured with context filter and formatter."""
    test_logger = logging.getLogger("test_context")
    test_logger.handlers.clear()
    test_logger.filters.clear()
    test_logger.addFilter(logger.ContextInjectingFilter())
    return test_logger


def test_logging_without_context_produces_no_context_data(
    logger_with_context: logging.Logger, caplog: LogCaptureFixture
) -> None:
    """Test logging without context produces clean log records."""
    with caplog.at_level(logging.INFO, logger="test_context"):
        logger_with_context.info("No context")
    assert len(caplog.records) == 1
    assert not caplog.records[0].context_dict  # type: ignore[attr-defined]


def test_logging_with_single_context_variable_injects_context_attributes(
    logger_with_context: logging.Logger, caplog: LogCaptureFixture
) -> None:
    """Test various data types in context are preserved correctly."""
    with caplog.at_level(logging.INFO, logger="test_context"):
        with logger.bound_contextvars(
            string_val="test", int_val=42, bool_val=True, none_val=None, list_val=[1, 2, 3]
        ):
            logger_with_context.info("Multiple types")

    record = caplog.records[0]
    assert record.ctx_string_val == "test"  # type: ignore[attr-defined]
    assert record.ctx_int_val == 42  # type: ignore[attr-defined]
    assert record.ctx_bool_val is True  # type: ignore[attr-defined]
    assert record.ctx_none_val is None  # type: ignore[attr-defined]
    assert record.ctx_list_val == [1, 2, 3]  # type: ignore[attr-defined]


def test_nested_context_overrides_and_restores_values_correctly(
    logger_with_context: logging.Logger, caplog: LogCaptureFixture
) -> None:
    """Test nested context behavior with overriding and restoration."""
    with caplog.at_level(logging.INFO, logger="test_context"):
        with logger.bound_contextvars(user_id=123, action="outer"):
            logger_with_context.info("Outer")

            with logger.bound_contextvars(user_id=456, request_id="nested"):
                logger_with_context.info("Inner")

            logger_with_context.info("Back to outer")

    assert len(caplog.records) == 3

    # Outer context
    assert caplog.records[0].ctx_user_id == 123  # type: ignore[attr-defined]
    assert caplog.records[0].ctx_action == "outer"  # type: ignore[attr-defined]

    # Inner context (user_id overridden, action inherited)
    assert caplog.records[1].ctx_user_id == 456  # type: ignore[attr-defined]
    assert caplog.records[1].ctx_action == "outer"  # type: ignore[attr-defined]
    assert caplog.records[1].ctx_request_id == "nested"  # type: ignore[attr-defined]

    # Back to outer (user_id restored, request_id gone)
    assert caplog.records[2].ctx_user_id == 123  # type: ignore[attr-defined]
    assert caplog.records[2].ctx_action == "outer"  # type: ignore[attr-defined]
    assert not hasattr(caplog.records[2], "ctx_request_id")


def test_context_cleanup_after_exception_in_bound_contextvars(
    logger_with_context: logging.Logger, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="test_context"):
        with pytest.raises(ValueError):
            with logger.bound_contextvars(user_id=123):
                raise ValueError("Test exception")

        logger_with_context.info("After exception")

    assert len(caplog.records) == 1
    assert not caplog.records[0].context_dict  # type: ignore[attr-defined]


def test_context_prefix_filtering_excludes_non_prefixed_variables(
    logger_with_context: logging.Logger, caplog: LogCaptureFixture
) -> None:
    non_log_var: contextvars.ContextVar[str] = contextvars.ContextVar("non_log_key")
    non_log_var.set("should_not_appear")

    with caplog.at_level(logging.INFO, logger="test_context"):
        with logger.bound_contextvars(proper_context="should_appear"):
            logger_with_context.info("Test message")

    record = caplog.records[0]
    assert not hasattr(record, "ctx_non_log_key")


def test_contextual_formatter_formats_context_as_json_suffix() -> None:
    formatter = logger.ContextualFormatter()

    record = logging.LogRecord("test", logging.INFO, "", 0, "Test message", (), None)
    record.context_dict = {"user_id": 123}
    result = formatter.format(record)

    assert result == 'Test message [context: {"user_id":123}]'


def test_contextual_formatter_passes_through_messages_without_context() -> None:
    formatter = logger.ContextualFormatter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "Test message", (), None)
    result = formatter.format(record)
    assert result == "Test message"
