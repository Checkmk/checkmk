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
from labelpicker_ng import logger
from typing import Optional
from pprint import pformat
import re, os, ast
from .lpds_hwswtreeapi import lpds_hwswtreeapi


class lpds_hwswtree(lpds_hwswtreeapi):
    """
    Represents an implementation of a strategy to parse and process hardware/software
    inventory data. The class defines various methods to parse inventory data from specific
    sources, translate inventory trees, and generate host labels from the source data.

    This class is typically used to automate the process of collecting and assigning
    structured inventory data to corresponding hosts.

    :ivar label_content: The resulting label content is extracted from the inventory data.
    :type label_content: Optional[str]
    """

    def source_algorithm(
            self,
    ) -> dict:
        """
        Parse Hardware/Software inventory data from a specified directory and return the
        parsed information as a dictionary. The method processes files in the directory,
        evaluates their content as Python literals, and handles syntax and value errors
        gracefully by logging them.

        :return: A dictionary containing parsed inventory data where keys are hostnames
                 and values are their respective-parsed content.
        :rtype: dict
        :raises KeyError: If the inventory directory is not set in the configuration or
                          environment variable.
        """
        parsed = {}

        if self.hwswtree_config.inventory_dir is None:
            inventory_dir = os.environ["OMD_ROOT"] + "/var/check_mk/inventory"
        else:
            if os.path.isabs(self.hwswtree_config.inventory_dir):
                inventory_dir = self.hwswtree_config.inventory_dir
                logger.info(f"Parsing Hardware/Software inventory data from {inventory_dir}")
            else:
                logger.error(f"Inventory directory {self.hwswtree_config.inventory_dir} does not exist or is not absolute.")
                return parsed

        for host in os.listdir(inventory_dir):
            if not re.match(r"(^\.|.*\.gz$)", host):
                logger.debug(f"Parsing host {host}")
                with open(f"{inventory_dir}/{host}", "r") as file:
                    content = file.read()
                    try:
                        parsed[host] = ast.literal_eval(content)
                    except SyntaxError as e:
                        logger.error(f"Syntax error in file {host}:\n{pformat(e, indent=4)}")
                    except ValueError as e:
                        logger.error(f"Value error in file {host}:\n{pformat(e, indent=4)}")
        return parsed
