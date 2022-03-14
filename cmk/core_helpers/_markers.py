#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, MutableMapping, NamedTuple, Optional, Sequence, Tuple

from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.regex import regex, REGEX_HOST_NAME_CHARS
from cmk.utils.translations import translate_hostname, TranslationOptions
from cmk.utils.type_defs import HostName, SectionName

__all__ = ["PiggybackMarker", "SectionMarker"]


class PiggybackMarker(NamedTuple):
    hostname: HostName

    @staticmethod
    def is_header(line: bytes) -> bool:
        return (
            line.strip().startswith(b"<<<<")
            and line.strip().endswith(b">>>>")
            and not PiggybackMarker.is_footer(line)
        )

    @staticmethod
    def is_footer(line: bytes) -> bool:
        return line.strip() == b"<<<<>>>>"

    @classmethod
    def from_headerline(
        cls,
        line: bytes,
        translation: TranslationOptions,
        *,
        encoding_fallback: str,
    ) -> "PiggybackMarker":
        # ? ensure_str called on a bytes object with different possible encodings
        raw_host_name = ensure_str_with_fallback(
            line.strip()[4:-4],
            encoding="utf-8",
            fallback=encoding_fallback,
        )
        assert raw_host_name
        hostname = translate_hostname(translation, raw_host_name)

        # Protect Checkmk against unallowed host names. Normally source scripts
        # like agent plugins should care about cleaning their provided host names
        # up, but we need to be sure here to prevent bugs in Checkmk code.
        # TODO: this should be moved into the HostName class, if it is ever created.
        return cls(HostName(regex("[^%s]" % REGEX_HOST_NAME_CHARS).sub("_", hostname)))


class SectionMarker(NamedTuple):
    name: SectionName
    cached: Optional[Tuple[int, int]]
    encoding: str
    nostrip: bool
    persist: Optional[int]
    separator: Optional[str]

    @staticmethod
    def is_header(line: bytes) -> bool:
        line = line.strip()
        return (
            line.startswith(b"<<<")
            and line.endswith(b">>>")
            and not SectionMarker.is_footer(line)
            and not PiggybackMarker.is_header(line)
            and not PiggybackMarker.is_footer(line)
        )

    @staticmethod
    def is_footer(line: bytes) -> bool:
        # There is no section footer in the protocol but some non-compliant
        # plugins still add one and we accept it.
        return (
            len(line) >= 6
            and line == b"<<<>>>"
            or (line.startswith(b"<<<:") and line.endswith(b">>>"))
        )

    @classmethod
    def default(cls, name: SectionName):
        return cls(name, None, "ascii", True, None, None)

    @classmethod
    def from_headerline(cls, headerline: bytes) -> "SectionMarker":
        def parse_options(elems: Iterable[str]) -> Iterable[Tuple[str, str]]:
            for option in elems:
                if "(" not in option:
                    continue
                name, value = option.split("(", 1)
                assert value[-1] == ")", value
                yield name, value[:-1]

        if not SectionMarker.is_header(headerline):
            raise ValueError(headerline)

        headerparts = headerline[3:-3].decode().split(":")
        options = dict(parse_options(headerparts[1:]))
        cached: Optional[Tuple[int, int]]
        try:
            cached_ = tuple(map(int, options["cached"].split(",")))
            cached = cached_[0], cached_[1]
        except KeyError:
            cached = None

        encoding = options.get("encoding", "utf-8")
        nostrip = options.get("nostrip") is not None

        persist: Optional[int]
        try:
            persist = int(options["persist"])
        except KeyError:
            persist = None

        separator: Optional[str]
        try:
            separator = chr(int(options["sep"]))
        except KeyError:
            separator = None

        return SectionMarker(
            name=SectionName(headerparts[0]),
            cached=cached,
            encoding=encoding,
            nostrip=nostrip,
            persist=persist,
            separator=separator,
        )

    def __str__(self) -> str:
        opts: MutableMapping[str, str] = {}
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
        return "<<<%s:%s>>>" % (self.name, ":".join("%s(%s)" % (k, v) for k, v in opts.items()))

    def cache_info(self, cached_at: int) -> Optional[Tuple[int, int]]:
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
