#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI integration for release flags.

This module exposes the file-backed release flags (defined in the ``cmk-flags``
package) in the global settings UI. It is the only writer of
``release_flag.json``; every other consumer reads the file through
``cmk.flags.load_release_flags``.

The config variables are generated from the fields of
:class:`cmk.flags.ReleaseFlagConfig`, so adding a flag there is enough to make
it appear in the UI -- no per-flag boilerplate here.
"""

import os
from pathlib import Path
from typing import Final, override

from pydantic.fields import FieldInfo

from cmk.ccc import store
from cmk.flags import CONFIG_FILENAME as RELEASE_FLAGS_CONFIG_FILENAME
from cmk.flags import ReleaseFlagConfig
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.valuespec import Checkbox
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    ConfigVariable,
    ConfigVariableGroup,
    SerializedSettings,
)
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.paths import default_config_dir, omd_root

RELEASE_FLAGS_CONFIG_ID: Final[ConfigDomainName] = "release_flags"
RELEASE_FLAGS_CONFIG_DIR: Final = default_config_dir
RELEASE_FLAGS_CONFIG_FILE_RELATIVE: Final = (
    RELEASE_FLAGS_CONFIG_DIR.relative_to(omd_root) / RELEASE_FLAGS_CONFIG_FILENAME
)


class ConfigDomainReleaseFlags(ABCConfigDomain):
    """Persists the release flags as JSON, not as a Python-literal ``.mk`` file.

    ``release_flag.json`` is read by ``cmk.flags.load_release_flags`` from both
    the GUI and ``cmk/base``, so it has to be valid JSON. The base class would
    write Python literals and read them back via ``exec``; we override ``save``
    and ``load_full_config`` to use JSON instead.
    """

    always_activate = True

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return RELEASE_FLAGS_CONFIG_ID

    @override
    def config_dir(self) -> Path:
        return RELEASE_FLAGS_CONFIG_DIR

    @override
    def config_file(self, site_specific: bool) -> Path:
        return self.config_dir() / RELEASE_FLAGS_CONFIG_FILENAME

    @override
    def load_full_config(
        self, site_specific: bool = False, custom_site_path: str | None = None
    ) -> GlobalSettings:
        filename = self.config_file(site_specific)
        if custom_site_path:
            filename = Path(custom_site_path) / filename.relative_to(omd_root)
        if not filename.exists():
            return {}
        raw = store.load_text_from_file(filename, default="{}")
        return dict(ReleaseFlagConfig.model_validate_json(raw).model_dump())

    @override
    def save(
        self,
        settings: GlobalSettings,
        site_specific: bool = False,
        custom_site_path: str | None = None,
    ) -> None:
        filename = self.config_file(site_specific)
        if custom_site_path:
            filename = Path(custom_site_path) / os.path.relpath(filename, omd_root)
        filename.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        config = ReleaseFlagConfig.model_validate(dict(settings))
        store.save_text_to_file(filename, config.model_dump_json(indent=2))

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def default_globals(self) -> GlobalSettings:
        return ReleaseFlagConfig().model_dump()


ConfigVariableGroupReleaseFlags = ConfigVariableGroup(
    title=_l("Release flags"),
    sort_index=200,
)


def _make_flag_config_variable(name: str, field_info: FieldInfo) -> ConfigVariable:
    extra = field_info.json_schema_extra or {}
    assert isinstance(extra, dict)
    description = str(extra.get("description", ""))
    remove_after = str(extra.get("remove_after", ""))
    help_text = _(
        "%s<br><br>This is a temporary release flag. It is scheduled for removal "
        "in version %s and must not be relied on for permanent configuration."
    ) % (description, remove_after)
    return ConfigVariable(
        group=ConfigVariableGroupReleaseFlags,
        primary_domain=ConfigDomainReleaseFlags,
        ident=name,
        valuespec=lambda context: Checkbox(
            title=name,
            label=_("Enabled"),
            help=help_text,
            default_value=False,
        ),
    )


release_flag_config_variables: Final[list[ConfigVariable]] = [
    _make_flag_config_variable(name, field_info)
    for name, field_info in ReleaseFlagConfig.model_fields.items()
]
