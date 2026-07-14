#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2026 SWR
# @author Frank Baier <frank.baier@swr.de>
#
# Based on:
# SPDX-FileCopyrightText: © 2023 PL Automation Monitoring GmbH <pl@automation-monitoring.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This file is part of the Checkmk Labelpicker project (https://labelpicker.mk)
from labelpicker_ng import lpb, logger, HostLabels, DatasourceConfig, LabelKey
from .. import checkmk_api as cmk
from typing import Dict, Any, List, Optional, Tuple, Match
from pprint import pformat
import re
from pydantic import BaseModel
from pathlib import Path


class LabelMapping(BaseModel):
    """
    Represents a mapping between a label and its associated tree and filters.

    This model is used to define a relationship between a label name and its
    corresponding tree structure. It can also include optional filters for
    matching regular expressions and specific match groups.

    :ivar labelname: The key or name of the label.
    :type labelname: LabelKey
    :ivar tree: A list defining the hierarchical tree structure relevant to the
        label.
    :type tree: List[str]
    :ivar regex_value_filter: An optional regular expression used to filter
        values associated with the label.
    :type regex_value_filter: Optional[str]
    :ivar match_group_filters: An optional list of filters applied to match
        groups within the regular expression.
    :type match_group_filters: Optional[List[str]]
    """
    labelname: LabelKey
    tree: List[str]
    regex_value_filter: Optional[str] = None
    match_group_filters: List[Tuple[str, str] | str] = []


class HwSwTreeApiConfig(BaseModel):
    """
    Konfiguration für das HWSW‑Tree‑Plugin (API‑Variante) ohne eigene Checkmk‑Zugangsdaten.

    Diese Konfiguration enthält ausschließlich plugin‑spezifische Einstellungen zur
    Auswertung des Inventarbaums. Die Anbindung an Checkmk (API‑URL, Auth usw.)
    erfolgt global und wird dem Plugin als bereits verbundene `CMKInstance` übergeben.

    :ivar table_row_mapping: Zuordnung von Tabellennamen zu (Schlüssel‑, Wert‑)Spalten,
        um Werte aus Tabellenstrukturen zu extrahieren.
    :type table_row_mapping: Dict[str, Tuple[str, str]]
    :ivar mapping: Liste der Label‑Mappings (Labelname, Pfad im Inventarbaum, optionale Filter).
    :type mapping: List[LabelMapping]
    """
    inventory_dir: Optional[Path] = None
    table_row_mapping: Dict[str, Tuple[str, str]] = {
                "packages": ("name", "version"),
                "routes": ("target", "gateway"),
                "interfaces": ("index", "speed"),
            }
    mapping: List[LabelMapping]


class lpds_hwswtreeapi(
    lpb.Strategy
):
    """
    Strategie zur Auswertung des Hardware/Software‑Inventars über die Checkmk‑REST‑API.

    Die Klasse verarbeitet das HWSW‑Inventar, übersetzt Pfade im Inventarbaum und erzeugt
    Host‑Labels gemäß der konfigurierten Mappings. Die Verbindung zu Checkmk wird nicht
    in dieser Klasse konfiguriert; stattdessen erhält sie eine bereits initialisierte
    `CMKInstance` über das `kwargs`‑Argument `wato`.

    :ivar label_content: The resulting label content extracted from the inventory data.
    :type label_content: Optional[str]
    """
    config: DatasourceConfig
    wato: cmk.CMKInstance
    hwswtree_config: HwSwTreeApiConfig
    label_content: str | None = None

    def __init__(
            self,
            config: DatasourceConfig,
            **kwargs,
    ):
        super().__init__()
        try:
            self.config = config
            self.wato: cmk.CMKInstance = kwargs.get("wato")
            self.hwswtree_config = HwSwTreeApiConfig(**config.config)
        except Exception as e:
            logger.error(f"Mo or incomplete HwSwTreeeApi config found:\n{pformat(e, indent=4)}")

    def source_algorithm(
            self,
    ) -> dict:
        """
        Ruft das Inventar über die bereitgestellte `CMKInstance` ab.

        Es wird keine eigene Checkmk‑Konfiguration aufgebaut. Stattdessen nutzt die
        Methode das in `__init__` übergebene Objekt `self.wato` (Typ `CMKInstance`),
        um das komplette HWSW‑Inventar zu laden und unverändert als Dict
        zurückzugeben.

        :return: Inventardaten als Dictionary.
        :rtype: dict
        """
        inventory_data = self.wato.get_inventory()
        return inventory_data

    @staticmethod
    def _translate_inv_tree(
            invtree: List[str]
    ) -> List[str]:
        """
        Translates a list of inventory tree elements from their display names to their corresponding
        internal keys or normalized format. It uses a predefined mapping dictionary to replace the
        display names with their identifiers. Unmapped items are converted to lowercase.

        :param invtree: A list of strings representing the inventory tree elements.
        :type invtree: List[str]
        :return: A list of translated and normalized inventory tree elements.
        :rtype: List[str]
        """
        invtree_translated = []
        inv_mapping = {
            "Operating System": "os",
            "Interfaces": "total_interfaces",
            "Ports": "total_ethernet_ports",
            "Default": "0.0.0.0/0",
            "Model Name": "model",
        }
        # TODO: Use builtin_inventory_plugins.inventory_displayhints for mapping
        #for item, data in builtin_inventory_plugins.inventory_displayhints.items():
        #    if "title" in data and type(data["title"]) == str:
        #        pass
        for item in invtree:
            item = inv_mapping.get(item, item)
            item = item.lower()
            invtree_translated.append(item)
        return invtree_translated

    def _inspect_inv_dict(
            self,
            data: Dict[str, Any],
            inv_tree: List[str],
            index: int = 0
    ) -> None:
        """
        Inspect the nested dictionary structure to retrieve values based on the given
        inventory tree keys. The function traverses through keys and evaluates their
        data contents, particularly focusing on the keys 'Attributes', 'Nodes', and
        'Table'. Depending on the structure and recursive depth, the function attempts
        to extract relevant information or navigate deeper into the nested dictionary.

        :param data: A dictionary representing the data structure to be inspected
        :param inv_tree: A list of strings defining the hierarchy or tree of keys
        :param index: The current index within the `inv_tree` to actively inspect
        :type data: Dict[str, Any]
        :type inv_tree: List[str]
        :type index: int
        :return: None
        :rtype: None
        """
        deep_inv_tree = len(inv_tree) - 1
        self.label_content = None
        cmk_inv_objects = ["Attributes", "Nodes", "Table"]
        for obj in cmk_inv_objects:
            # If Attributes, Nodes or Table is not in data continue it seems to be a structure of an old cmk version
            # Currently no parser inplemented for this, so skip it
            if not obj in data:
                continue
            if not data[obj] == {}:
                if obj == "Attributes" and index == deep_inv_tree:
                    if "Pairs" in data[obj]:
                        self.label_content = str(data[obj]["Pairs"][inv_tree[index]])
                elif obj == "Table":
                    if "Rows" in data[obj]:
                        for key, rmap in self.hwswtree_config.table_row_mapping.items():
                            if key == inv_tree[index - 1]:
                                for row in data[obj]["Rows"]:
                                    # Convert both the pattern and the target text to strings
                                    pattern = str(inv_tree[index])
                                    target_text = str(row[rmap[0]])

                                    # Now use re.search() to match the pattern anywhere in the target_text
                                    if re.search(pattern, target_text):
                                        self.label_content = row[rmap[1]]
                                        break
                else:
                    # try to dig deeper
                    try:
                        self._inspect_inv_dict(
                            data[obj][inv_tree[index]],
                            inv_tree,
                            index + 1,
                        )
                    except KeyError:
                        pass

    def process_algorithm(
            self,
            source_data: Dict[str, Any],
    ) -> HostLabels:
        """
        Process source data and return a dictionary where the keys represent hostnames
        and the values are corresponding labels based on the specified configuration.
        This method evaluates the provided source data according to the mapping
        definitions within the configuration and applies regex-based filters
        to refine extracted labels. It ensures structured and filtered label data
        collection for the provided hosts.

        :param source_data: Dictionary representing the source dataset, where each key is
            a host and the value contains host-specific data.
        :return: A dictionary with hostnames as keys and corresponding labels as values
            after processing the `source_data` according to the `config`.
        :rtype: HostLabels
        """
        def replace_group_reference(m: Match[str]) -> str:
            group_no = int(m.group(1))
            value = match.group(group_no)
            return "" if value is None else value

        collected_labels = {}
        filter_blacklist = []
        for host, data in source_data.items():
            logger.debug("Processing host: {}".format(host))
            for definition in self.hwswtree_config.mapping:
                inv_tree = self._translate_inv_tree(definition.tree)
                self._inspect_inv_dict(data, inv_tree)

                if self.label_content:
                    # update collected_labels with host and label
                    if host not in collected_labels:
                        collected_labels[host] = {}
                    # set label key depending on label_prefix
                    if self.config.label_prefix:
                        k = "{}/{}".format(self.config.label_prefix, definition.labelname)
                    else:
                        k = definition.labelname
                    regex_value_filter = definition.regex_value_filter
                    # Todo: Should be implemented in labelpicker_base.py
                    # if regex_value_filter is defined, check if label_content matches regex and define variable v. If not skip the complete label
                    if regex_value_filter:
                        if not re.search(str(regex_value_filter), self.label_content):
                            continue

                    v = self.label_content
                    # try to apply a matchgroup filter if defined
                    for mg_filter in definition.match_group_filters:
                        if isinstance(mg_filter, tuple):
                            # if filter is a list, use the first element as regex and the second element as modified regex
                            regex = mg_filter[0]
                            re_modified = mg_filter[1]
                        else:
                            # if the filter is a string, switch to simple match -> first group
                            regex: str = mg_filter
                            re_modified = r"\1"

                        if re_modified is None:
                            raise ValueError("re_modified / match_group_filters (if set) must not be None")

                        if mg_filter not in filter_blacklist:
                            try:
                                match = re.search(regex, v)
                                if match:
                                    # substitute match groups in re_modified string
                                    v = re.sub(
                                        pattern=r"\\(\d+)",
                                        repl=replace_group_reference,
                                        string=re_modified,
                                    )
                                    break
                            except Exception as e:
                                filter_blacklist.append(mg_filter)
                                logger.error(f"ERROR: Could not apply match_group_filters to {k}. "
                                             f"Exception:\n{pformat(e, indent=4)}")
                    if v != '':
                        collected_labels[host].update({k: v})

                    logger.debug(f"{host} -> {definition.labelname} -> {v}")

        return collected_labels
