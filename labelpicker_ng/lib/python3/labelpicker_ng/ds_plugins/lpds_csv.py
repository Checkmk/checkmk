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
from typing import List, Literal
from pydantic import BaseModel
from  labelpicker_ng import lpb, HostLabels, DatasourceConfig, logger, Host
import os
import csv
import re
from pathlib import Path
from pprint import pformat


class CsvConfig(BaseModel):
    """
    Konfiguration für den CSV-Importer.

    :ivar separator: Feld-Trennzeichen in den CSV-Dateien. Erlaubt sind ',' oder ';'.
                     Standard: ';'
    :type separator: Literal[',', ';']
    :ivar allow_prefixes: Wenn True, dürfen Labels in der CSV einen eigenen Prefix
                          (z. B. "cmk/name:value") mitbringen. Wenn False, wird
                          immer der Prefix aus der `DatasourceConfig` verwendet.
    :type allow_prefixes: bool
    :ivar csv_files: Liste der zu verarbeitenden CSV-Dateien als Pfade.
    :type csv_files: List[Path]
    """
    separator: Literal[',', ';'] = ";"
    allow_prefixes: bool = False
    csv_files: List[Path] = list


class lpds_csv(lpb.Strategy):
    """
    Represents a CSV-based data processing strategy.

    This class is designed to parse and process CSV files according to the given
    configuration. It is capable of reading multiple CSV files, skipping headers,
    and extracting meaningful data from each row. Additionally, the processed
    information can be further used to generate host labels based on specified rules.

    :ivar config: Configuration object containing details about the data source
        and processing settings.
    :type config: DatasourceConfig
    :ivar csv_config: Configuration specific to the CSV format, including file paths
        and delimiters, derived from the provided data source configuration.
    :type csv_config: CsvConfig
    """
    config: DatasourceConfig
    csv_config: CsvConfig

    def __init__(
            self,
            config: DatasourceConfig,
            **kwargs,
    ):
        super().__init__()
        try:
            self.config = config
            self.csv_config = CsvConfig(**config.config)
        except Exception as e:
            logger.error(f"Mo or incomplete lpds_csv config found:\n{pformat(e, indent=4)}")

    @staticmethod
    def parse_label(
            label: str
    ) -> tuple[str | None, str | None, str | None]:
        """
        Zerlegt ein Label in die Bestandteile Prefix, Name und Wert.

        Erwartetes Format: "[prefix/]name[:value]". Beispiel: "csv/owner:IT".

        :param label: Roh-Label aus der CSV.
        :return: Tupel aus (prefix, name, value). Nicht vorhandene Teile sind `None`.
        :rtype: tuple[str | None, str | None, str | None]
        """
        label_re = re.compile(
            r"^(?:(?P<prefix>[^/:]+)/)?(?P<name>[^:]+)(?::(?P<value>.+))?$"
        )
        m = label_re.match(label)
        if not m:
            return None, None, None  # oder Exception werfen

        return (
            (p := m.group("prefix")) and p.strip() or None,
            (n := m.group("name")) and n.strip() or None,
            (v := m.group("value")) and v.strip() or None,
        )

    def source_algorithm(
            self,
    ) -> List[List[str]]:
        """
        Parses CSV files as defined in the configuration and returns their content.

        This method processes multiple CSV files specified in the given configuration.
        For each CSV file, it reads its content line by line, skipping the header row,
        and returns the data in a parsed format. It handles cases where the CSV files
        may not exist or the configuration may be incomplete.

        :return: A list of parsed rows from the CSV files, where each row is a list of
            strings. Returns an empty list if the configuration is malformed or an error
            occurs during parsing.
        :rtype: List[List[str]]
        """
        parsed = []
        for csv_file in self.csv_config.csv_files:
            if os.path.isfile(csv_file):
                logger.debug(f"Reading CSV file {csv_file}")
                with open(csv_file, "r") as f:
                    reader = csv.reader(f, delimiter=self.csv_config.separator)
                    for row in reader:
                        # add row to a parsed list but skip the first row (header)
                        if not reader.line_num == 1:
                            parsed.append(row)
            else:
                logger.error(f"CSV file {csv_file} not found.")
        return parsed

    def process_algorithm(
            self,
            source: List[List[str]],
    ) -> HostLabels:
        """
        Processes a given algorithm by parsing the source data and applying the specified
        configuration settings. This function generates a mapping of hosts to their labels.

        :param source: A list of lists where each sublist represents a row containing a host
                       identifier and corresponding labels. Each label is represented in the
                       format "label_prefix:label_name/label_value".
        :return: A dictionary mapping hosts to their associated labels. Each label includes
                 optional prefix information determined by the input configuration.
        :rtype: HostLabels
        """
        collected_labels = {}
        for row in source:
            host: Host = row[0]
            collected_labels[host] = {}
            for label in row[1].split(","):
                try:
                    label_prefix, label_name, label_value = self.parse_label(label)
                    if label_name and label_value:
                        if self.csv_config.allow_prefixes:
                            label_prefix = label_prefix or self.config.label_prefix
                        else:
                            label_prefix = self.config.label_prefix
                        new_label = f"{label_prefix}/{label_name}"
                        collected_labels[host].update({new_label: label_value})
                except Exception as e:
                    logger.error(f"ERROR: Could not parse label {label} from row {row}.\nException:\n{pformat(e, indent=4)}")
        return collected_labels
