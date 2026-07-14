#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2025 SWR
# @author Frank Baier <frank.baier@swr.de>
#
# Based on:
# SPDX-FileCopyrightText: © 2023 PL Automation Monitoring GmbH <pl@automation-monitoring.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This file is part of the Checkmk Labelpicker project (https://labelpicker.mk)
from abc import ABC, abstractmethod
from typing import Dict, Any
from .dataclasses import CaseConversionConfig, HostLabels


class Strategy(ABC):
    """
    Source Strategy Interface.

    This abstract base class defines the interface for implementing custom
    strategies in sourcing and processing data using specific algorithms.
    Concrete implementations of this class must override the methods
    to provide the desired functionality in the sourcing and processing
    steps.

    """

    @abstractmethod
    def source_algorithm(
            self,
    ) -> Any:
        pass

    @abstractmethod
    def process_algorithm(
            self,
            source_data: Dict[str, Any],
    ) -> HostLabels:
        pass


class LableDataProcessor:
    """
    Primary class to handle label data sourcing and processing strategies.

    This class allows the selection of a sourcing and processing strategy for label data.
    It supports operations for fetching source data and processing it into a structured
    format. Users can provide custom strategies by passing a `Strategy` implementation
    when initializing the class. If no strategy is provided, a default behavior is assumed.

    :ivar strategy: The strategy used for data sourcing and processing.
    :type strategy: Strategy
    """
    strategy: Strategy = None

    def __init__(
            self,
            strategy: Strategy = None,
    ) -> None:
        if strategy is not None:
            self.strategy = strategy
        else:
            # default strategy
            pass

    def get(
            self,
    ) -> Any:
        """
        Retrieves source data based on the provided configuration.

        This method uses the source algorithm defined by the strategy to
        collect data from the source specified in the configuration.

        :return: The data retrieved from the source as processed by the source
                 algorithm within the strategy.
        :rtype: Any
        """
        return self.strategy.source_algorithm()

    def process(
            self,
            source_data:
            HostLabels,
    ) -> HostLabels:
        """
        Processes the provided source data using a specific algorithm defined by the strategy
        and applies the given configuration.

        Example:
        {'localhost': {'csv/tester': 'Mustermann',
                       'csv/Building': 'A',
                       'csv/Owner': 'Internal-IT',
                       'csv/Room': '305'},
         'testhost1': {'csv/Building': 'A',
                       'csv/Owner': 'Test-Automation',
                       'csv/Room': '305'},
         'testhost2': {'csv/Building': 'B',
                       'csv/Owner': 'Test-Automation',
                       'csv/Room': '104'}}

        :param source_data: The source data to be processed.
        :return: The processed data resulting from applying the algorithm and configuration.
        """
        return self.strategy.process_algorithm(source_data)


def case_conversion(
        label_definitions: HostLabels,
        params: CaseConversionConfig,
        label_prefix: str,
) -> HostLabels:
    """
    Converts the labels and their corresponding values of the provided label definitions
    based on the case conversion configuration. The function processes the labels
    and/or values to apply the specified case transformation (if any) and prefixes
    them with the given label prefix.

    :param label_definitions: Dictionary containing mappings of hosts to their respective
        label key-value pairs.
    :param params: Configuration specifying if and how the label keys and values should
        be case converted.
    :param label_prefix: String prefix that will be prepended to each modified label key.
    :return: Modified label definitions with converted labels and values.
    :rtype: HostLabels
    """
    converted = {}
    for host, data in label_definitions.items():
        converted[host] = {}
        for k, v in data.items():
            if params.label != "none":
                if k.startswith(f"{label_prefix}/"):
                    stripped_key = k[len(label_prefix) + 1:]  # remove prefix + "/"
                    stripped_key = getattr(stripped_key, params.label)()
                    k = f"{label_prefix}/{stripped_key}"
            if params.value != "none":
                v = getattr(v, params.value)()

            converted[host].update({ k: v })
    return converted
