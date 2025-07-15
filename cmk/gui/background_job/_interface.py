#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import importlib
import threading
import time
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager as ContextManager
from logging import Logger
from pathlib import Path
from typing import IO, NamedTuple

from pydantic import BaseModel, field_serializer, field_validator

from cmk.utils import render

from cmk.trace import SpanContext, TraceFlags, TraceState

from ._defines import BackgroundJobDefines


class BackgroundProcessInterface:
    def __init__(
        self,
        work_dir: str,
        job_id: str,
        logger: Logger,
        stop_event: threading.Event,
        gui_context: Callable[[], ContextManager[None]],
        progress_update: IO[str],
    ) -> None:
        self._work_dir = work_dir
        self._job_id = job_id
        self._logger = logger
        self.stop_event = stop_event
        self.gui_context = gui_context
        self._progress_update = progress_update

    def get_work_dir(self) -> str:
        return self._work_dir

    def get_job_id(self) -> str:
        return self._job_id

    def get_logger(self) -> Logger:
        return self._logger

    def send_progress_update(self, info: str, with_timestamp: bool = False) -> None:
        """The progress update is written to stdout and will be caught by the threads counterpart"""
        message = info
        if with_timestamp:
            message = f"{render.time_of_day(time.time())} {message}"
        self._progress_update.write(message + "\n")

    def send_result_message(self, info: str) -> None:
        """The result message is written to a distinct file to separate this info from the rest of
        the context information. This message should contain a short result message and/or some kind
        of resulting data, e.g. a link to a report or an agent output. As it may contain HTML code
        it is not written to stdout."""
        encoded_info = "%s\n" % info
        result_message_path = (
            Path(self.get_work_dir()) / BackgroundJobDefines.result_message_filename
        )
        with result_message_path.open("ab") as f:
            f.write(encoded_info.encode())

    def send_exception(self, info: str) -> None:
        """Exceptions are written to stdout because of log output clarity
        as well as into a distinct file, to separate this info from the rest of the context information
        """
        # Exceptions also get an extra newline, since some error messages tend not output a \n at the end..
        encoded_info = "%s\n" % info
        self._progress_update.write(encoded_info)
        with (Path(self.get_work_dir()) / BackgroundJobDefines.exceptions_filename).open("ab") as f:
            f.write(encoded_info.encode())


class JobTarget[Args](BaseModel, frozen=True):
    # Actually we require a module level function and not a callable
    callable: Callable[[BackgroundProcessInterface, Args], None]
    args: Args

    @field_validator("callable", mode="before")
    @classmethod
    def validate_callable(cls, value: object) -> Callable[[BackgroundProcessInterface, Args], None]:
        if callable(value):
            return value
        if not isinstance(value, tuple | list) or not len(value) == 2:
            raise ValueError("The callable must be a tuple with two elements")
        func = getattr(importlib.import_module(value[0]), value[1])
        if not callable(func):
            raise ValueError("The callable must be a callable")
        return func  # type: ignore[no-any-return]

    @field_serializer("callable")
    def serialize_callable(self, value: Callable) -> tuple[str, str]:
        return self.callable.__module__, self.callable.__name__


class NoArgs(BaseModel, frozen=True): ...


def simple_job_target(
    callable: Callable[[BackgroundProcessInterface, NoArgs], None],
) -> JobTarget[NoArgs]:
    return JobTarget(callable=callable, args=NoArgs())


class SpanContextModel(BaseModel, frozen=True):
    trace_id: int
    span_id: int
    is_remote: bool
    trace_flags: int
    trace_state: Sequence[tuple[str, str]]

    @classmethod
    def from_span_context(cls, span_context: SpanContext) -> SpanContextModel:
        return SpanContextModel(
            trace_id=span_context.trace_id,
            span_id=span_context.span_id,
            is_remote=span_context.is_remote,
            trace_flags=span_context.trace_flags,
            trace_state=list(span_context.trace_state.items()),
        )

    def to_span_context(self) -> SpanContext:
        return SpanContext(
            self.trace_id,
            self.span_id,
            self.is_remote,
            TraceFlags(self.trace_flags),
            TraceState(self.trace_state),
        )


class JobParameters(NamedTuple):
    """Just a small wrapper to help improve the typing through multiprocessing.Process call"""

    stop_event: threading.Event
    work_dir: str
    job_id: str
    target: JobTarget
    lock_wato: bool
    is_stoppable: bool
    override_job_log_level: int | None
    span_id: str
    origin_span_context: SpanContextModel
