#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import contextvars
import json
import logging
import pathlib
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import override

# Prefix for our context variables to avoid conflicts
_LOG_KEY_PREFIX = "cmk_log_"
_LOG_KEY_PREFIX_LEN = len(_LOG_KEY_PREFIX)

# Registry of context variables - each key gets its own ContextVar for better isolation
_CONTEXT_VARS: dict[str, contextvars.ContextVar[object]] = {}

logger = logging.getLogger("agent-receiver")


def configure_logger(path: pathlib.Path) -> None:
    handler = logging.FileHandler(path, encoding="UTF-8")
    formatter = ContextualFormatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")
    context_filter = ContextInjectingFilter()

    handler.setFormatter(formatter)
    handler.addFilter(context_filter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ContextInjectingFilter(logging.Filter):
    """Filter that injects context variables into log records."""

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        """Inject context variables into the log record."""
        ctx = contextvars.copy_context()
        context: dict[str, object] = {}

        for context_var in ctx:
            if context_var.name.startswith(_LOG_KEY_PREFIX):
                key = context_var.name[_LOG_KEY_PREFIX_LEN:]
                context[key] = ctx[context_var]
                # Also set as individual attributes for easy access
                setattr(record, f"ctx_{key}", ctx[context_var])

        record.context_dict = context

        return True


class ContextualFormatter(logging.Formatter):
    """Formatter that uses context data from LogRecord attributes (set by filter)."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        formatted_message = super().format(record)

        if hasattr(record, "context_dict") and record.context_dict:
            context_json = json.dumps(record.context_dict, separators=(",", ":"))
            formatted_message += f" [context: {context_json}]"

        return formatted_message


def bind_context(**kwargs: object) -> Mapping[str, contextvars.Token[object]]:
    """
    Bind key-value pairs to separate context variables.

    Returns a mapping of tokens that can be used with reset_context()
    for proper cleanup/restoration.
    """
    tokens: dict[str, contextvars.Token[object]] = {}
    for key, value in kwargs.items():
        contextvar_key = f"{_LOG_KEY_PREFIX}{key}"
        # Get or create the context variable for this key
        try:
            var = _CONTEXT_VARS[contextvar_key]
        except KeyError:
            var = contextvars.ContextVar(contextvar_key)
            _CONTEXT_VARS[contextvar_key] = var
        tokens[key] = var.set(value)

    return tokens


def reset_context(**tokens: contextvars.Token[object]) -> None:
    for key, token in tokens.items():
        contextvar_key = f"{_LOG_KEY_PREFIX}{key}"
        _CONTEXT_VARS[contextvar_key].reset(token)


@contextmanager
def bound_contextvars(**kwargs: object) -> Generator[None, None, None]:
    """
    Context manager that temporarily binds key-value pairs to context variables.

    Automatically restores previous values when exiting the context.
    Does not affect other context variables.

    Usage:
        with bound_context(user_id=123, request_id="abc-def"):
            logger.info("Processing request")  # Will include context
    """
    tokens = bind_context(**kwargs)

    try:
        yield
    finally:
        # Reset to previous values using tokens
        reset_context(**tokens)
