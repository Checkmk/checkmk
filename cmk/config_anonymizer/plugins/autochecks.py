#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterable

import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.ccc.store import ObjectStore
from cmk.checkengine.discovery._autochecks import _AutochecksSerializer, AutochecksStore
from cmk.checkengine.plugins import AutocheckEntry
from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui.config import Config


def _autocheck_hosts() -> Iterable[HostName]:
    for autocheck_file in cmk.utils.paths.autochecks_dir.glob("*.mk"):
        yield HostName(autocheck_file.stem)


def _anonymize_auto_check(anon_interface: AnonInterface, check: AutocheckEntry) -> AutocheckEntry:
    new_item = anon_interface.get_item(item) if (item := check.item) is not None else None
    return AutocheckEntry(
        # we would need to anonymize the check parameters as well, but since we
        # won't use the config for monitoring anyway, this is sufficient
        check.check_plugin_name,
        new_item,
        {},
        dict(
            [anon_interface.get_service_label_groups(k, v) for k, v in check.service_labels.items()]
        ),
    )


class AutochecksSteps(AnonymizeStep):
    def run(
        self, anon_interface: AnonInterface, active_config: Config, logger: logging.Logger
    ) -> None:
        logger.warning("Process autochecks")

        target_dir = anon_interface.relative_to_anon_dir(cmk.utils.paths.autochecks_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        for host in _autocheck_hosts():
            anonymized_checks = [
                _anonymize_auto_check(anon_interface, check)
                for check in AutochecksStore(host).read()
            ]

            new_file = f"{anon_interface.get_host(host)}.mk"
            autochecks_store = ObjectStore(
                target_dir / new_file, serializer=_AutochecksSerializer()
            )
            autochecks_store.write_obj(
                sorted(anonymized_checks, key=lambda e: (str(e.check_plugin_name), str(e.item)))
            )


anonymize_step_autochecks = AutochecksSteps()
