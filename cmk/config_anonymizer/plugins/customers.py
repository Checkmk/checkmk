#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The customers of the ultimatemt edition.

Sites, folders, hosts, groups and rules of an anonymized dump refer to customers
by their anonymized id. The dump has to define those customers as well, otherwise
it refers to customers that do not exist once it is loaded into another site.
"""

import logging
from collections.abc import Mapping
from typing import override

from cmk.base.config import LoadingResult
from cmk.ccc import store
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui.config import Config
from cmk.utils.labels import Labels
from cmk.utils.paths import default_config_dir

# Where the ultimatemt edition stores its customers. The path is only defined in
# cmk.gui.nonfree.ultimatemt.managed, which this (edition independent) tool
# must not import.
_CUSTOMERS_FILE = default_config_dir / "multisite.d/wato/customers.mk"


def anonymize_customers(
    customers: Mapping[str, object], anon_interface: AnonInterface
) -> dict[str, dict[str, str]]:
    """The customers under their anonymized ids, reduced to an anonymized name.

    Everything else a customer can carry (macros, global settings, report
    layout, ...) is free-form and may hold names or secrets, so it is left out.
    The provider keeps its id: it is fixed, and everything in the dump that
    names no customer belongs to the provider implicitly.
    """
    return {
        (anon_id := anon_interface.get_customer(customer_id)): {"name": anon_id}
        for customer_id in customers
    }


class CustomersStep(AnonymizeStep):
    @override
    def run(
        self,
        anon_interface: AnonInterface,
        active_config: Config,
        loaded_config_result: LoadingResult,
        all_plugins: AgentBasedPlugins,
        builtin_host_labels: Labels,
        logger: logging.Logger,
    ) -> None:
        # The loaded GUI config has the customers of the ultimatemt edition,
        # the provider included. The other editions do not know the setting.
        customers: Mapping[str, object] | None = getattr(active_config, "customers", None)
        if customers is None:
            logger.info("Skipping customers, this edition has none")
            return
        logger.warning("Process customers")

        store.save_to_mk_file(
            anon_interface.relative_to_anon_dir(_CUSTOMERS_FILE),
            key="customers",
            value=anonymize_customers(customers, anon_interface),
            pprint_value=True,
        )


anonymize_step_customers = CustomersStep()
