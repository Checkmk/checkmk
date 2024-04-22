#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pprint import pformat
from typing import Any

from pydantic import ValidationError

from cmk.utils import tty

from cmk.gui.exceptions import MKConfigError  # pylint: disable=cmk-module-layer-violation


class ConfigValidationError(MKConfigError):
    def __init__(
        self,
        which_file: str,
        pydantic_error: ValidationError,
        original_data: Any,
    ) -> None:
        self.which_file = which_file
        self.original_data = original_data
        self.pydantic_error = pydantic_error

    def __str__(self) -> str:
        error_msg = f'''
        {tty.red}Current config: '{self.which_file}'{tty.normal}
        {pformat(self.original_data).replace('\n', '\n\t')}
        \n\t{tty.red}Config errors ({self.pydantic_error.error_count()}){tty.normal}
        '''

        for error in self.pydantic_error.errors():
            error_msg += f'{(pformat(error)).replace("\n", "\n\t")}\n\n\t'

        return error_msg
