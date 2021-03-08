#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
from functools import partial
from pathlib import Path
from typing import final, Final, Generic, Optional, Tuple

import cmk.utils
import cmk.utils.debug
import cmk.utils.log  # TODO: Remove this!
import cmk.utils.misc
import cmk.utils.paths
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    result,
    ServiceDetails,
    ServiceState,
    SourceType,
)

from cmk.snmplib.type_defs import TRawData

from cmk.core_helpers import Fetcher, Parser, Summarizer
from cmk.core_helpers.cache import FileCache
from cmk.core_helpers.controller import FetcherType
from cmk.core_helpers.host_sections import THostSections
from cmk.core_helpers.type_defs import Mode, SectionNameCollection

from cmk.base.config import HostConfig

__all__ = ["Source"]


class Source(Generic[TRawData, THostSections], metaclass=abc.ABCMeta):
    """Hold the configuration to fetchers and checkers.

    At best, this should only hold static data, that is, every
    attribute is final.

    """
    use_outdated_persisted_sections: bool = False

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        source_type: SourceType,
        fetcher_type: FetcherType,
        description: str,
        default_raw_data: TRawData,
        default_host_sections: THostSections,
        id_: str,
        cache_dir: Optional[Path] = None,
        persisted_section_dir: Optional[Path] = None,
    ) -> None:
        self.hostname: Final[str] = hostname
        self.ipaddress: Final[Optional[str]] = ipaddress
        self.mode: Final[Mode] = mode
        self.source_type: Final[SourceType] = source_type
        self.fetcher_type: Final[FetcherType] = fetcher_type
        self.description: Final[str] = description
        self.default_raw_data: Final = default_raw_data
        self.default_host_sections: Final[THostSections] = default_host_sections
        self.id: Final[str] = id_
        if not cache_dir:
            cache_dir = Path(cmk.utils.paths.data_source_cache_dir) / self.id
        if not persisted_section_dir:
            persisted_section_dir = Path(cmk.utils.paths.var_dir) / "persisted_sections" / self.id

        self.file_cache_path: Final[Path] = cache_dir / self.hostname
        self.file_cache_max_age: int = 0
        self.persisted_sections_file_path: Final[Path] = persisted_section_dir / self.hostname

        self.host_config: Final[HostConfig] = HostConfig.make_host_config(hostname)
        self._logger: Final[logging.Logger] = logging.getLogger("cmk.base.data_source.%s" % id_)

        self.exit_spec = self.host_config.exit_code_spec(id_)

    def __repr__(self) -> str:
        return "%s(%r, %r, mode=%r, description=%r, id=%r)" % (
            type(self).__name__,
            self.hostname,
            self.ipaddress,
            self.mode,
            self.description,
            self.id,
        )

    @property
    def fetcher_configuration(self):
        return self._make_fetcher().to_json()

    @final
    def fetch(self) -> result.Result[TRawData, Exception]:
        try:
            with self._make_fetcher() as fetcher:
                return fetcher.fetch(self.mode)
        except Exception as exc:
            if cmk.utils.debug.enabled():
                raise
            return result.Error(exc)

    @final
    def parse(
        self,
        raw_data: result.Result[TRawData, Exception],
        *,
        selection: SectionNameCollection,
    ) -> result.Result[THostSections, Exception]:
        try:
            return raw_data.map(partial(self._make_parser().parse, selection=selection))
        except Exception as exc:
            self._logger.log(VERBOSE, "ERROR: %s", exc)
            if cmk.utils.debug.enabled():
                raise
            return result.Error(exc)

    @final
    def summarize(
        self,
        host_sections: result.Result[THostSections, Exception],
    ) -> Tuple[ServiceState, ServiceDetails]:
        summarizer = self._make_summarizer()
        return host_sections.fold(
            ok=partial(summarizer.summarize_success, mode=self.mode),
            error=partial(summarizer.summarize_failure, mode=self.mode),
        )

    @abc.abstractmethod
    def _make_file_cache(self) -> FileCache[TRawData]:
        raise NotImplementedError

    @abc.abstractmethod
    def _make_fetcher(self) -> Fetcher:
        """Create a fetcher with this configuration."""
        raise NotImplementedError

    @abc.abstractmethod
    def _make_parser(self) -> Parser[TRawData, THostSections]:
        """Create a parser with this configuration."""
        raise NotImplementedError

    @abc.abstractmethod
    def _make_summarizer(self) -> Summarizer[THostSections]:
        """Create a summarizer with this configuration."""
        raise NotImplementedError
