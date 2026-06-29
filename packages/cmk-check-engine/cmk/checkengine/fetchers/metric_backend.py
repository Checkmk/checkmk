#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import typing
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Final, Self, TypedDict

from cmk.checkengine.fetcher import DeserializationContext, Fetcher, FetcherError
from cmk.checkengine.helper_interface import AgentRawData


class MetricBackendFetcherParams(TypedDict):
    argv: Sequence[str]
    omd_root: str


class AttributeType(Enum):
    SCOPE = "scope"
    RESOURCE = "resource"
    DATA_POINT = "data_point"


@dataclass(frozen=True)
class AttributeFilter:
    key: str
    value: str


@dataclass(frozen=True)
class AttributeFilterGroup:
    """One conjunctive (AND) set of attribute filters. A host's series are the union (OR) of the
    matches of all its groups, so a host produced by several DCD host name lookup rules collects the
    series of every rule that named it."""

    resource_attribute_filters: Sequence[AttributeFilter]
    scope_attribute_filters: Sequence[AttributeFilter]
    data_point_attribute_filters: Sequence[AttributeFilter]
    # A free-form host name template (e.g. "$RESOURCE_ATTR.service.name$") that, by convention,
    # resolves to this host's own name. Carried through verbatim and resolved into concrete
    # attribute filters by the telemetry fetcher (which has backend access and the template logic).
    # Hosts created by the DCD connector instead carry the resolved values directly in the attribute
    # filters and leave this empty.
    host_name_template: str | None


def _parse_filters(raw: object) -> list[AttributeFilter]:
    assert isinstance(raw, list)
    return [AttributeFilter(key=f["key"], value=f["value"]) for f in raw]


@dataclass(frozen=True)
class MetricBackendFetcherConfig:
    # One or more filter groups, ORed together when fetching the host's series. Each group may carry
    # its own host name template (resolved at fetch time); see AttributeFilterGroup.
    attribute_filter_groups: Sequence[AttributeFilterGroup]
    check_interval: float
    host_name: str

    @classmethod
    def from_serialized(
        cls, metrics_association_raw: str, check_interval: float, host_name: str
    ) -> Self:
        metrics_association = json.loads(metrics_association_raw)

        # Hosts produced by more than one DCD host name lookup rule store the union of the rules'
        # filters as a list of groups. Single-rule and manually configured hosts keep the legacy
        # single ``attribute_filters`` shape, which is read as exactly one group.
        if (groups := metrics_association.get("attribute_filter_groups")) is not None:
            # Multi-rule DCD host: the connector stored the resolved filters of every rule directly,
            # so there is no host name template left to resolve at fetch time.
            attribute_filter_groups = [
                AttributeFilterGroup(
                    resource_attribute_filters=_parse_filters(group["resource_attributes"]),
                    scope_attribute_filters=_parse_filters(group["scope_attributes"]),
                    data_point_attribute_filters=_parse_filters(group["data_point_attributes"]),
                    host_name_template=None,
                )
                for group in groups
            ]
        else:
            attribute_filter_groups = [cls._single_group_from_legacy(metrics_association)]

        return cls(
            attribute_filter_groups=attribute_filter_groups,
            check_interval=check_interval,
            host_name=host_name,
        )

    @staticmethod
    def _single_group_from_legacy(
        metrics_association: dict[str, Any],
    ) -> AttributeFilterGroup:
        attribute_filters = metrics_association["attribute_filters"]
        assert isinstance(attribute_filters, dict)

        host_name_template = metrics_association.get("host_name_template")
        if host_name_template is None and (
            legacy_key := metrics_association.get("host_name_resource_attribute_key")
        ):
            # Backward compatibility: a host configured before the template feature carries a single
            # resource attribute key whose value, by convention, equals the host's own name. Map it
            # to the equivalent template so it keeps working regardless of when the config migration
            # runs. Mirrors cmk.telemetry.host_name_template.macro_for_key.
            host_name_template = f"$RESOURCE_ATTR.{legacy_key}$"

        return AttributeFilterGroup(
            resource_attribute_filters=_parse_filters(attribute_filters["resource_attributes"]),
            scope_attribute_filters=_parse_filters(attribute_filters["scope_attributes"]),
            data_point_attribute_filters=_parse_filters(attribute_filters["data_point_attributes"]),
            host_name_template=host_name_template,
        )


def _has_cause(exc: Exception, cause_type: type[Exception]) -> bool:
    while exc.__cause__ is not None:
        _exc = exc.__cause__
        if isinstance(_exc, cause_type):
            return True
    return False


class MetricBackendFetcher(Fetcher[AgentRawData, MetricBackendFetcherParams]):
    def __init__(
        self,
        *,
        argv: Sequence[str],
        make_output: Callable[[Path, Sequence[str]], str],
        omd_root: Path,
    ) -> None:
        super().__init__()
        self.argv: Final = argv
        self.make_output = make_output
        self.omd_root = omd_root
        self._logger: Final = logging.getLogger("cmk.helper.metric_backend_fetcher")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(" + ", ".join((f"argv={self.argv!r}",)) + ")"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MetricBackendFetcher):
            return False
        return self.argv == other.argv

    def serialized_params(self) -> MetricBackendFetcherParams:
        return {"argv": self.argv, "omd_root": self.omd_root.as_posix()}

    @classmethod
    def from_params(cls, params: MetricBackendFetcherParams, ctx: DeserializationContext) -> Self:
        return cls(
            argv=params["argv"],
            omd_root=Path(params["omd_root"]),
            make_output=ctx.make_output,
        )

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    @typing.override
    def _fetch_from_io(self, mode: object) -> AgentRawData:
        self._logger.debug("Get data from metric backend")
        try:
            return AgentRawData(self.make_output(self.omd_root, self.argv).encode("utf-8"))
        except Exception as e:
            if not _has_cause(e, ConnectionRefusedError):
                raise
            else:
                raise FetcherError(
                    "Backend initializing, please wait for 2-3 check cycles. "
                    "If this error persists, make sure the metric backend (Clickhouse) is running. "
                    "If the error still persists, please contact the Checkmk support. "
                    f"(Details: {e})\n"
                ) from e
