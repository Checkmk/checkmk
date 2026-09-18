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

from collections.abc import Mapping, Sequence
from typing import override

import botocore
from botocore.client import BaseClient

from ..config import AWSConfig, LOGGER, Tags
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionLimits,
    AWSSectionResult,
    get_seconds_since_midnight,
    NOW,
    ResultDistributor,
)


class GlacierLimits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "glacier_limits"

    @property
    @override
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        LOGGER.debug(
            "Maximal allowed age of usage data cache: %(cache_interval)s sec",
            {"cache_interval": cache_interval},
        )
        return cache_interval

    @property
    @override
    def granularity(self) -> int:
        return 86400

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    @override
    def get_live_data(self, *args):
        """
        There's no API method for getting account limits thus we have to
        fetch all vaults.
        """
        response = self._client.list_vaults()  # type: ignore[attr-defined]
        return self._get_response_content(response, "VaultList")

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        self._add_limit(
            "",
            AWSLimit(
                "number_of_vaults",
                "Vaults",
                1000,
                len(raw_content.content),
            ),
        )
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class Glacier(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["glacier_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["glacier_tags"])

    @property
    @override
    def name(self) -> str:
        return "glacier"

    @property
    @override
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        LOGGER.debug(
            "Maximal allowed age of usage data cache: %(cache_interval)s sec",
            {"cache_interval": cache_interval},
        )
        return cache_interval

    @property
    @override
    def granularity(self) -> int:
        return 86400

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("glacier_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[object]:
        """
        1. get all vaults from AWS Glacier.
        2. filter vaults by their name.
        3. get tags for the filtered vaults
        :param colleague_contents:
        :return: filtered list of vaults with their tags
        """
        (colleague_contents,) = args
        found_vaults = []
        for vault in self._filter_vaults_by_names(self._list_vaults(colleague_contents)):
            vault_name = vault["VaultName"]

            try:
                response = self._client.list_tags_for_vault(vaultName=vault_name)  # type: ignore[attr-defined]
            except botocore.exceptions.ClientError as e:
                # If there are no tags attached to a bucket we receive a 'ClientError'
                LOGGER.warning(
                    "%(name)s/%(vault_name)s: Exception, %(error)s",
                    {"name": self.name, "vault_name": vault_name, "error": e},
                )
                response = {}

            tags = self._get_response_content(response, "Tags")
            tag_list: Tags = [{"Key": key, "Value": value} for key, value in tags.items()]
            if self._matches_tag_conditions(tag_list):
                vault["Tagging"] = tags  # Legacy tags, to be removed when check is adapted
                vault["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tag_list)
                found_vaults.append(vault)

        return found_vaults

    def _filter_vaults_by_names(self, vault_list):
        """
        filter vaults by their VaultName
        :param vault_list: list of all vaults
        :return: filtered list of dicts
        """
        if not self._names:
            return vault_list

        return [vault for vault in vault_list if vault["VaultName"] in self._names]

    def _list_vaults(self, colleague_contents: AWSColleagueContents) -> Mapping[str, str | int]:
        """
        get list of vaults from previous call or get it now
        :param colleague_contents:
        :return:
        """
        if colleague_contents.content:
            return colleague_contents.content
        return self._get_response_content(self._client.list_vaults(), "VaultList")  # type: ignore[attr-defined]

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True

        return any(tag in self._tags for tag in tagging)

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]
