#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, Iterator


class LazyString:
    """String wrapper to postpone localizations of strings

    Our own home grown version of flask_babel.SpeakLater. We previously used flask_babel.SpeakLater, but
    dropped it, because it is a trivial dependency.
    """

    def __init__(self, func: Callable[[str], str], text: str) -> None:
        self._func = func
        self._text = text

    def __getattr__(self, attr: str):
        if attr == "__setstate__":
            raise AttributeError(attr)
        string = str(self)
        if hasattr(string, attr):
            return getattr(string, attr)
        raise AttributeError(attr)

    def __repr__(self) -> str:
        return "l'{0}'".format(str(self))

    def __str__(self) -> str:
        return str(self._func(self._text))

    def __len__(self) -> int:
        return len(str(self))

    def __getitem__(self, key: int) -> str:
        return str(self)[key]

    def __iter__(self) -> Iterator[str]:
        return iter(str(self))

    def __contains__(self, item: str) -> bool:
        return item in str(self)

    def __add__(self, other: str) -> str:
        return str(self) + other

    def __radd__(self, other: str) -> str:
        return other + str(self)

    def __mul__(self, other: int) -> str:
        return str(self) * other

    def __rmul__(self, other: int) -> str:
        return other * str(self)

    def __lt__(self, other: str) -> bool:
        return str(self) < other

    def __le__(self, other: str) -> bool:
        return str(self) <= other

    def __eq__(self, other: object) -> bool:
        return str(self) == other

    def __ne__(self, other: object) -> bool:
        return str(self) != other

    def __gt__(self, other: str) -> bool:
        return str(self) > other

    def __ge__(self, other: str) -> bool:
        return str(self) >= other

    def __html__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash(str(self))

    def __mod__(self, other: object) -> str:
        return str(self) % other

    def __rmod__(self, other: str) -> str:
        return other + str(self)

    def to_json(self) -> str:
        return str(self)
