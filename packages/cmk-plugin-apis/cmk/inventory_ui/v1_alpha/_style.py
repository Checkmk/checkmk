#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import auto, Enum


class Alignment(Enum):
    LEFT = auto()
    CENTERED = auto()
    RIGHT = auto()


class BackgroundColor(Enum):
    LIGHT_RED = auto()
    RED = auto()
    DARK_RED = auto()

    LIGHT_ORANGE = auto()
    ORANGE = auto()
    DARK_ORANGE = auto()

    LIGHT_YELLOW = auto()
    YELLOW = auto()
    DARK_YELLOW = auto()

    LIGHT_GREEN = auto()
    GREEN = auto()
    DARK_GREEN = auto()

    LIGHT_BLUE = auto()
    BLUE = auto()
    DARK_BLUE = auto()

    LIGHT_CYAN = auto()
    CYAN = auto()
    DARK_CYAN = auto()

    LIGHT_PURPLE = auto()
    PURPLE = auto()
    DARK_PURPLE = auto()

    LIGHT_PINK = auto()
    PINK = auto()
    DARK_PINK = auto()

    LIGHT_BROWN = auto()
    BROWN = auto()
    DARK_BROWN = auto()

    LIGHT_GRAY = auto()
    GRAY = auto()
    DARK_GRAY = auto()

    BLACK = auto()
    WHITE = auto()


class LabelColor(Enum):
    LIGHT_RED = auto()
    RED = auto()
    DARK_RED = auto()

    LIGHT_ORANGE = auto()
    ORANGE = auto()
    DARK_ORANGE = auto()

    LIGHT_YELLOW = auto()
    YELLOW = auto()
    DARK_YELLOW = auto()

    LIGHT_GREEN = auto()
    GREEN = auto()
    DARK_GREEN = auto()

    LIGHT_BLUE = auto()
    BLUE = auto()
    DARK_BLUE = auto()

    LIGHT_CYAN = auto()
    CYAN = auto()
    DARK_CYAN = auto()

    LIGHT_PURPLE = auto()
    PURPLE = auto()
    DARK_PURPLE = auto()

    LIGHT_PINK = auto()
    PINK = auto()
    DARK_PINK = auto()

    LIGHT_BROWN = auto()
    BROWN = auto()
    DARK_BROWN = auto()

    LIGHT_GRAY = auto()
    GRAY = auto()
    DARK_GRAY = auto()

    BLACK = auto()
    WHITE = auto()
