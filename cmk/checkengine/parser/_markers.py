#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Sequence
from typing import NamedTuple

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.sectionname import SectionName
from cmk.utils.translations import translate_raw_host_name, TranslationOptions

__all__ = ["PiggybackMarker", "SectionMarker"]


class PiggybackMarker(NamedTuple):
    hostname: HostName | None

    @classmethod
    def from_header(
        cls,
        header: bytes,
        translation: TranslationOptions,
        *,
        encoding_fallback: str,
    ) -> "PiggybackMarker":
        # ? ensure_str called on a bytes object with different possible encodings
        raw_host_name = translate_raw_host_name(
            translation,
            ensure_str_with_fallback(
                header,
                encoding="utf-8",
                fallback=encoding_fallback,
            ),
        )

        if not raw_host_name:
            # NOTE: We are never called with an empty header (otherwise we would be a footer), and
            # decoding won't make a non-empty header empty, so raw_host_name is never empty, either.
            # Nevertheless, host name translation *can* result in an empty name.
            return cls(None)

        try:
            return cls(HostAddress.project_valid(raw_host_name))
        except ValueError:
            return cls(None)

    def should_be_ignored(self) -> bool:
        if self.hostname is not None:
            try:
                HostAddress(self.hostname)
                return False
            except ValueError:
                pass
        return True


# option values of the form "FOO(BAR, BAZ)"
_OPTION = re.compile(r"([^(]*?)\((.*)\)")


class SectionMarker(NamedTuple):
    name: SectionName
    cached: tuple[int, int] | None
    encoding: str
    nostrip: bool
    persist: int | None
    separator: str | None

    @classmethod
    def default(cls, name: SectionName) -> "SectionMarker":
        return cls(name, None, "ascii", True, None, None)

    @classmethod
    def from_header(cls, header: bytes) -> "SectionMarker":
        section_name, *elems = header.decode().split(":")
        # NOTE: We silenty ignore some syntactically invalid options below, but throw for others. Hmmm...
        options = {
            name_and_value[1]: name_and_value[2]
            for option in elems
            if (name_and_value := re.fullmatch(_OPTION, option))
        }

        try:
            cached_ = tuple(map(int, options["cached"].split(",")))
            cached: tuple[int, int] | None = cached_[0], cached_[1]
        except KeyError:
            cached = None

        encoding = options.get("encoding", "utf-8")
        nostrip = options.get("nostrip") is not None

        try:
            persist: int | None = int(options["persist"])
        except KeyError:
            persist = None

        try:
            separator: str | None = chr(int(options["sep"]))
        except KeyError:
            separator = None

        return SectionMarker(
            name=SectionName(section_name),
            cached=cached,
            encoding=encoding,
            nostrip=nostrip,
            persist=persist,
            separator=separator,
        )

    def __str__(self) -> str:
        opts: dict[str, str] = {}
        if self.cached:
            opts["cached"] = ",".join(str(c) for c in self.cached)
        if self.encoding != "utf-8":
            opts["encoding"] = self.encoding
        if self.nostrip:
            opts["nostrip"] = ""
        if self.persist is not None:
            opts["persist"] = str(self.persist)
        if self.separator is not None:
            opts["sep"] = str(ord(self.separator))
        if not opts:
            return f"<<<{self.name}>>>"
        return "<<<{}:{}>>>".format(self.name, ":".join(f"{k}({v})" for k, v in opts.items()))

    def cache_info(self, cached_at: int) -> tuple[int, int] | None:
        # If both `persist` and `cached` are present, `cached` has priority
        # over `persist`.  I do not know whether this is correct.
        if self.cached:
            return self.cached
        if self.persist is not None:
            return cached_at, self.persist - cached_at
        return None

    def parse_line(self, line: bytes) -> Sequence[str]:
        # ? ensure_str called on a bytes object with different possible encodings
        line_str = ensure_str_with_fallback(
            line,
            encoding=self.encoding,
            fallback="latin-1",
        )
        if not self.nostrip:
            line_str = line_str.strip()
        return line_str.split(self.separator)
