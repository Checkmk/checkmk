#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus
from typing import NewType

from fastapi import HTTPException

RelayID = NewType("RelayID", str)
TaskID = NewType("TaskID", str)
Serial = NewType("Serial", str)


class RelayNotFoundError(HTTPException):
    def __init__(self, relay_id: RelayID):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND, detail=f"Relay with ID '{relay_id}' not found"
        )


class TaskNotFoundError(HTTPException):
    def __init__(self, task_id: TaskID):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND, detail=f"Task with ID '{task_id}' not found"
        )


class TooManyTasksError(HTTPException):
    def __init__(self, max_number_of_tasks: int):
        super().__init__(
            status_code=HTTPStatus.FORBIDDEN,
            detail=f"The maximum number of tasks {max_number_of_tasks} has been reached",
        )
