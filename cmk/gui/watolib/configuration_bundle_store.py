#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import NewType, NotRequired, TypedDict, TypeGuard

from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_QUICK_SETUP

from cmk.gui.hooks import request_memoize
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import multisite_dir

BundleId = NewType("BundleId", str)


def is_locked_by_quick_setup(
    ident: GlobalIdent | None, *, check_reference_exists: bool = True
) -> TypeGuard[GlobalIdent]:
    """Check if the given ident of a config object is locked by the quick setup program.

    Args:
        ident:
            The locked_by ident of the config object.

        check_reference_exists:
            additionally checks if the reference exists. Normally the reference should point to
            an existing configuration bundle. In some rare cases, the reference might point to a
            non-existing bundle. This is possible due to partial deletion of the underlying objects
            which can happen and is deemed ok, the user should be allowed to modify the object in
            this case. We still want to show the user that the object is part of a bundle while
            unlocking it. Defaults to True since the reference should normally exist.
    """
    if ident is None:
        return False

    if ident["program_id"] != PROGRAM_ID_QUICK_SETUP:
        return False

    if check_reference_exists and ident["instance_id"] not in load_configuration_bundles():
        return False

    return True


class ConfigBundle(TypedDict):
    """
    A configuration bundle is a collection of configs which are managed together by this bundle.
    Each underlying config must have the locked_by attribute set to the id of the bundle. We
    explicitly avoid double references (for now: but might have to be considered in the context
    of performance restrictions) here to keep the data model simple. The group and program
    combination should determine which configuration objects are potentially part of the bundle.
    """

    # General properties
    title: str
    comment: str

    # Bundle specific properties
    owned_by: NotRequired[str | None]  # user id, not set = admin
    group: str  # e.g. rulespec_name    # special_agent:aws
    program_id: str  # PROGRAM_ID_QUICK_SETUP
    customer: NotRequired[str]  # CME specific


class ConfigBundleStore(WatoSingleConfigFile[dict[BundleId, ConfigBundle]]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=multisite_dir() / "configuration_bundles.mk",
            config_variable="configuration_bundles",
            spec_class=dict[BundleId, ConfigBundle],
        )


def load_group_bundles(bundle_group: str) -> Mapping[BundleId, ConfigBundle]:
    all_bundles = ConfigBundleStore().load_for_reading()
    return {
        bundle_id: bundle
        for bundle_id, bundle in all_bundles.items()
        if bundle["group"] == bundle_group
    }


@request_memoize()
def load_configuration_bundles() -> Mapping[BundleId, ConfigBundle]:
    return ConfigBundleStore().load_for_reading()


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(ConfigBundleStore())
