#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.session import SuperUserContext
from cmk.gui.watolib.hosts_and_folders import FolderTree, Host


def _remove_labels(host: Host, invalid_labels: set[str], *, pprint_value: bool) -> None:
    updated_labels = {
        k: v for k, v in host.attributes.get("labels", {}).items() if k not in invalid_labels
    }
    with SuperUserContext():
        host.update_attributes({"labels": updated_labels}, pprint_value=pprint_value)


def _find_invalid_labels() -> dict[Host, set[str]]:
    result: dict[Host, set[str]] = {}

    for folder_path, folder in FolderTree().all_folders().items():
        hosts = folder.hosts()
        for host_name, host in hosts.items():
            labels = host.labels()
            invalid_labels = set()
            for label, value in labels.items():
                if ":" in label or ":" in value:
                    invalid_labels.add(label)

            if invalid_labels:
                result[host] = invalid_labels
    return result
