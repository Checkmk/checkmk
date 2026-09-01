#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI integration for experimental flags.

This module exposes the file-backed experimental flags (defined in the ``cmk-flags``
package) in the global settings UI. It is the only writer of
``experimental_flag.json``; every other consumer reads the file through
``cmk.flags.load_experimental_flags``.

The config variables are generated from the fields of
:class:`cmk.flags.ExperimentalFlagConfig`, so adding a flag there is enough to make
it appear in the UI -- no per-flag boilerplate here.
"""

import os
from pathlib import Path
from typing import Final, override

from pydantic.fields import FieldInfo

from cmk.ccc import store
from cmk.flags import CONFIG_FILENAME as EXPERIMENTAL_FLAGS_CONFIG_FILENAME
from cmk.flags import ExperimentalFlagConfig
from cmk.gui.i18n import _l
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    ConfigVariable,
    ConfigVariableGroup,
    SerializedSettings,
)
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Help, Label, Title
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.paths import default_config_dir, omd_root

EXPERIMENTAL_FLAGS_CONFIG_ID: Final[ConfigDomainName] = "experimental_flags"
EXPERIMENTAL_FLAGS_CONFIG_DIR: Final = default_config_dir
EXPERIMENTAL_FLAGS_CONFIG_FILE_RELATIVE: Final = (
    EXPERIMENTAL_FLAGS_CONFIG_DIR.relative_to(omd_root) / EXPERIMENTAL_FLAGS_CONFIG_FILENAME
)


class ConfigDomainExperimentalFlags(ABCConfigDomain):
    """Persists the experimental flags as JSON, not as a Python-literal ``.mk`` file.

    ``experimental_flag.json`` is read by ``cmk.flags.load_experimental_flags`` from both
    the GUI and ``cmk/base``, so it has to be valid JSON. The base class would
    write Python literals and read them back via ``exec``; we override ``save``
    and ``load_full_config`` to use JSON instead.
    """

    always_activate = True

    @classmethod
    @override
    def ident(cls) -> ConfigDomainName:
        return EXPERIMENTAL_FLAGS_CONFIG_ID

    @override
    def config_dir(self) -> Path:
        return EXPERIMENTAL_FLAGS_CONFIG_DIR

    @override
    def config_file(self, site_specific: bool) -> Path:
        return self.config_dir() / EXPERIMENTAL_FLAGS_CONFIG_FILENAME

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
        return dict(ExperimentalFlagConfig.model_validate_json(raw).model_dump())

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
        config = ExperimentalFlagConfig.model_validate(dict(settings))
        store.save_text_to_file(filename, config.model_dump_json(indent=2))

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def default_globals(self) -> GlobalSettings:
        return ExperimentalFlagConfig().model_dump()


ConfigVariableGroupExperimentalFlags = ConfigVariableGroup(
    title=_l("Experimental flags"),
    sort_index=200,
)


def _make_flag_config_variable(name: str, field_info: FieldInfo) -> ConfigVariable:
    extra = field_info.json_schema_extra or {}
    assert isinstance(extra, dict)
    description = str(extra.get("description", ""))
    remove_after = str(extra.get("remove_after", ""))
    help_text = Help(
        "%(description)s<br><br>This is a temporary experimental flag. It is scheduled for removal "
        "in version %(remove_after)s and must not be relied on for permanent configuration."
    ) % {"description": description, "remove_after": remove_after}
    return ConfigVariable(
        group=ConfigVariableGroupExperimentalFlags,
        primary_domain=ConfigDomainExperimentalFlags,
        ident=name,
        form_spec=lambda context: fs.BooleanChoice(
            title=Title(name),  # astrein: disable=localization-checker
            label=Label("Enabled"),
            help_text=help_text,
        ),
    )


experimental_flag_config_variables: Final[list[ConfigVariable]] = [
    _make_flag_config_variable(name, field_info)
    for name, field_info in ExperimentalFlagConfig.model_fields.items()
]
