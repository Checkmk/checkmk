#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import argparse
import hashlib
import logging
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Literal, TypedDict

from cmk.server_side_programs.v1_unstable import Storage

AGENT = "aws"

LOGGER = logging.getLogger(f"agent_{AGENT}")


class RawTag(TypedDict):
    Name: str
    Values: Sequence[str]


OverallTags = tuple[Sequence[str] | None, Sequence[str] | None]

RawTags = list[RawTag]


Tags = list[Mapping[Literal["Key", "Value"], str]]


class NamingConvention(Enum):
    ip_region_instance = "ip_region_instance"
    private_dns_name = "private_dns_name"


class TagsImportPatternOption(Enum):
    ignore_all = "IGNORE_ALL"
    import_all = "IMPORT_ALL"


TagsOption = str | Literal[TagsImportPatternOption.ignore_all, TagsImportPatternOption.import_all]


class AWSConfig:
    def __init__(
        self,
        hostname: str,
        sys_argv: argparse.Namespace,
        overall_tags: OverallTags,
        piggyback_naming_convention: NamingConvention,
        tags_option: TagsOption = TagsImportPatternOption.import_all,
    ) -> None:
        self.hostname = hostname
        self._overall_tags = self._prepare_tags(overall_tags)
        self.service_config: dict = {}
        self._config_hash_storage = Storage(AGENT, hostname)
        self._config_hash_key = "config_hash"
        self._current_config_hash = self._compute_config_hash(sys_argv)
        self.piggyback_naming_convention = piggyback_naming_convention
        self.tags_option = tags_option

    def add_service_tags(self, tags_key: str, tags: OverallTags) -> None:
        """Convert commandline input
        from
            (['foo', 'foo', 'aaa', 'aaa', ...], ['bar', 'baz', 'bbb', 'ccc', ...])
        to
            Filters=[{'Name': 'tag:foo', 'Values': ['bar', 'baz']},
                     {'Name': 'tag:aaa', 'Values': ['bbb', 'ccc']}, ...]
        as we need in API methods if and only if keys AND values are set.
        """
        self.service_config.setdefault(tags_key, None)
        keys, values = tags
        if keys and values:
            self.service_config[tags_key] = self._prepare_tags(tags)
        elif self._overall_tags:
            self.service_config[tags_key] = self._overall_tags

    @staticmethod
    def _prepare_tags(
        tags: OverallTags,
    ) -> RawTags | None:
        keys, values = tags
        if keys is None or values is None:
            return None

        grouped: dict[str, list[str]] = {}
        for k, v in zip(keys, values):
            grouped.setdefault(k, []).append(v)
        return [{"Name": f"tag:{k}", "Values": v} for k, v in grouped.items()]

    def add_single_service_config(self, key: str, value: object | None) -> None:
        self.service_config.setdefault(key, value)

    @staticmethod
    def _compute_config_hash(sys_argv: argparse.Namespace) -> str:
        filtered_sys_argv = dict(
            filter(lambda el: el[0] not in ["debug", "verbose", "no_cache"], vars(sys_argv).items())
        )

        # Be careful to use a hashing mechanism that generates the same hash across
        # different python processes! Otherwise the config file will always be
        # out-of-date
        return hashlib.sha256("".join(sorted(filtered_sys_argv)).encode()).hexdigest()

    def is_up_to_date(self) -> bool:
        old_config_hash = self._load_config_hash()
        if old_config_hash is None:
            LOGGER.info(
                "AWSConfig: %(hostname)s: New config: '%(config_hash)s'",
                {"hostname": self.hostname, "config_hash": self._current_config_hash},
            )
            self._write_config_hash()
            return False

        if old_config_hash != self._current_config_hash:
            LOGGER.info(
                "AWSConfig: %(hostname)s: Config has changed: '%(old_config_hash)s' -> '%(config_hash)s'",
                {
                    "hostname": self.hostname,
                    "old_config_hash": old_config_hash,
                    "config_hash": self._current_config_hash,
                },
            )
            self._write_config_hash()
            return False

        LOGGER.info(
            "AWSConfig: %(hostname)s: Config is up-to-date: '%(config_hash)s'",
            {"hostname": self.hostname, "config_hash": self._current_config_hash},
        )
        return True

    def _load_config_hash(self) -> str | None:
        return self._config_hash_storage.read(self._config_hash_key, default=None)

    def _write_config_hash(self) -> None:
        self._config_hash_storage.write(self._config_hash_key, self._current_config_hash)
