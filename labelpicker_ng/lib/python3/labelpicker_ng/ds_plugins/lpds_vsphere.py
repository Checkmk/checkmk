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
from labelpicker_ng import lpb, logger, HostLabels, DatasourceConfig
from typing import Dict, Any
from pprint import pformat
from .lpds_vsphere_api import vSphereAPI, VsphereConfig


class lpds_vsphere(lpb.Strategy):
    """
    Strategy for extracting and processing vSphere resource data.

    This class provides mechanisms for authenticating with a vSphere API,
    retrieving virtual machines (VMs) and their associated tags, and
    processing the extracted data into a structured format suitable for
    further usage. It relies on a provided configuration for authentication
    and label formatting.

    :ivar label_content: Placeholder for label content. It is an optional
        attribute and can be set to None if not used.
    :type label_content: str | None
    :ivar config: The primary configuration object based on `DatasourceConfig`.
        This is used for general settings required by the strategy.
    :type config: DatasourceConfig
    :ivar vsphere_config: Specific vSphere-related configuration, derived
        from `config.config`. This object is used for communication with the
        vSphere API.
    :type vsphere_config: VsphereConfig
    """
    config: DatasourceConfig
    vsphere_config: VsphereConfig
    label_content: str | None = None

    def __init__(
            self,
            config: DatasourceConfig,
            **kwargs,
    ):
        super().__init__()
        try:
            self.config = config
            self.vsphere_config = VsphereConfig(**config.config)
        except Exception as e:
            logger.error(f"Mo or incomplete lpds_vsphere config found:\n{pformat(e, indent=4)}")

    def source_algorithm(
            self,
    ) -> dict:
        """
        Executes the vSphere resource extraction algorithm.

        The function authenticates with a vSphere API and retrieves virtual machines (VMs)
        alongside their associated tags. It constructs and returns a dictionary mapping VM names
        to their tags and corresponding values, using provided configuration settings for authentication.

        :return: A dictionary mapping virtual machine names to their associated tag categories
            and values.
        :rtype: dict
        """
        vsphere_api = vSphereAPI(self.vsphere_config.api_config)

        vm_cache = {}
        tag_cache = {}

        for vm in vsphere_api.get_all_vms():
            vm_cache[vm["name"]] = {}
            vm_tags = vsphere_api.get_vm_tags(vm["vm"])
            for vm_tag in vm_tags:
                if not vm_tag in tag_cache:
                    tag = vsphere_api.get_vsphere_tag(vm_tag)
                    tag_value = tag["value"]["name"]
                    category = vsphere_api.get_tag_category(tag["value"]["category_id"])
                    tag_cache[vm_tag] = (category["value"]["name"], tag_value)
                tag_id, tag_val = tag_cache[vm_tag]
                vm_cache[vm["name"]].update({tag_id: tag_val})

        return vm_cache

    def process_algorithm(
            self,
            source_data: Dict[str, Any],
    ) -> HostLabels:
        """
        Processes the input data to generate a dictionary of host labels. The input
        dictionary is iterated where each host and its associated tags are processed.
        Hosts without the correct suffix are updated to include the required suffix
        from the vsphere configuration. Tags are also formatted to include a specified
        label prefix from the service configuration.

        The final processed dictionary of labels is returned. Each host key maps to
        another dictionary which contains formatted tags and their corresponding values.

        :param source_data: Input dictionary where each key is a host name (str) and
            the value is another dictionary containing tag-value pairs to process.
        :return: Dictionary of processed host labels where each host key maps to
            another dictionary of formatted tag-value pairs.
        """
        collected_labels = {}
        for host, tags in source_data.items():
            if not host.endswith(self.vsphere_config.host_suffix):
                host=f"{host}{self.vsphere_config.host_suffix}"
            collected_labels[host] = {}
            for tag, value in tags.items():
                tag = f"{self.config.label_prefix}/{tag}"
                collected_labels[host].update({tag.strip(): value.strip()})
        return collected_labels
