#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from cmk.ccc.version import Edition
from cmk.utils.licensing import active_metric_series_retriever_registry as registry


@pytest.fixture
def retriever_function() -> MagicMock:
    return MagicMock()


@pytest.fixture
def edition_mock() -> Iterator[MagicMock]:
    with patch(
        "cmk.utils.licensing.active_metric_series_retriever_registry.edition",
    ) as edition_mock:
        yield edition_mock


@pytest.fixture
def logger_mock() -> Iterator[MagicMock]:
    with patch(
        "cmk.utils.licensing.active_metric_series_retriever_registry._get_logger",
    ) as get_logger_mock:
        yield get_logger_mock.return_value.error


@pytest.mark.parametrize("retriever_return", [123, None])
def test_get_num_active_metric_series_returns_value_when_registered(
    retriever_function: MagicMock,
    retriever_return: int | None,
) -> None:
    # given
    retriever_function.return_value = retriever_return
    registry.active_metric_series_retriever_registry.register(retriever_function)

    # when
    result = registry.get_num_active_metric_series()

    # then
    assert result == retriever_return
    retriever_function.assert_called_once_with()


def test_get_num_active_metric_series_returns_none_and_logs_on_exception(
    retriever_function: MagicMock,
    logger_mock: MagicMock,
) -> None:
    # given
    exception = ValueError("boom")
    retriever_function.side_effect = exception
    registry.active_metric_series_retriever_registry.register(retriever_function)

    # when
    result = registry.get_num_active_metric_series()

    # then
    assert result is None
    retriever_function.assert_called_once_with()
    logger_mock.assert_called_once_with(
        "Error when retrieving the active metric series count (%s): %s", "ValueError", exception
    )


@pytest.mark.parametrize(
    "edition",
    [Edition.ULTIMATE, Edition.ULTIMATEMT, Edition.CLOUD],
)
def test_get_num_active_metric_series_logs_when_missing_registry_when_expected(
    edition_mock: MagicMock,
    logger_mock: MagicMock,
    edition: Edition,
) -> None:
    # given
    edition_mock.return_value = edition
    registry.active_metric_series_retriever_registry.metric_series_retriever_function = None

    # when
    result = registry.get_num_active_metric_series()

    # then
    assert result is None
    logger_mock.assert_called_once_with(
        "There is no registered active metric series function, while it should"
    )


@pytest.mark.parametrize(
    "edition",
    [Edition.COMMUNITY, Edition.PRO],
)
def test_get_num_active_metric_series_no_log_when_missing_registry_when_not_expected(
    edition_mock: MagicMock,
    logger_mock: MagicMock,
    edition: Edition,
) -> None:
    # given
    edition_mock.return_value = edition
    registry.active_metric_series_retriever_registry.metric_series_retriever_function = None

    # when
    result = registry.get_num_active_metric_series()

    # then
    assert result is None
    logger_mock.assert_not_called()
