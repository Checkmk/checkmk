#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI integration for experimental flags.

This module exposes the file-backed experimental flags (defined in the ``cmk-flags``
package) in the global settings UI. Changed flags are visible to consumer after
all changes are activated.

The config variables are generated from the fields of
:class:`cmk.flags.ExperimentalFlagConfig`, so adding a flag there is enough to
make it appear in the UI -- no per-flag boilerplate here.

The flags are only shown on development sites, see :func:`is_development_site`.
"""

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Final, override

from pydantic.fields import FieldInfo

from cmk.ccc import store
from cmk.flags import CONFIG_FILENAME as EXPERIMENTAL_FLAGS_CONFIG_FILENAME
from cmk.flags import ExperimentalFlagConfig, load_experimental_flags
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    ConfigVariable,
    ConfigVariableGroup,
    EXPERIMENTAL_FLAGS,
    SerializedSettings,
)
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Help, Label, Title
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.paths import default_config_dir, omd_root
from cmk.web.utils.html import HTML
from cmk.web.utils.icons import IconNames

EXPERIMENTAL_FLAGS_CONFIG_ID: Final = EXPERIMENTAL_FLAGS
EXPERIMENTAL_FLAGS_CONFIG_DIR: Final = default_config_dir
EXPERIMENTAL_FLAGS_STAGED_FILENAME: Final = "_pending_release_flag.json"


def is_development_site(environ: Mapping[str, str] = os.environ) -> bool:
    return environ.get("CMK_DEV", "").lower() == "true"


def _load_flags(filename: Path) -> ExperimentalFlagConfig:
    # Same fallback as load_experimental_flags, which can only read the active file.
    try:
        return ExperimentalFlagConfig.model_validate_json(filename.read_text())
    except Exception:
        return ExperimentalFlagConfig()


class ConfigDomainExperimentalFlags(ABCConfigDomain):
    """Persists the experimental flags as JSON, not as a Python-literal ``.mk`` file.

    ``release_flag.json`` is read by ``cmk.flags.load_experimental_flags`` from
    both the GUI and ``cmk/base``, so it has to be valid JSON. The base class
    would write Python literals and read them back via ``exec``; we override
    ``save`` and ``load_full_config`` to use JSON instead.
    """

    # Distributed setups are not supported yet: nothing is synced to remote sites,
    # so they keep the default flags.
    needs_sync = False
    always_activate = True
    _flags_changed = False

    @classmethod
    @override
    def ident(cls) -> ConfigDomainName:
        return EXPERIMENTAL_FLAGS_CONFIG_ID

    @classmethod
    @override
    def hint(cls) -> HTML:
        return HTML.without_escaping(
            _(
                "This is an experimental flag for testing only. It may change or be removed "
                "without notice and must not be relied on for permanent configuration. "
                "Changing it restarts the whole site during activate changes."
            )
        )

    @override
    def config_dir(self) -> Path:
        return EXPERIMENTAL_FLAGS_CONFIG_DIR

    @override
    def config_file(self, site_specific: bool) -> Path:
        return self.config_dir() / EXPERIMENTAL_FLAGS_STAGED_FILENAME

    def active_config_file(self) -> Path:
        return self.config_dir() / EXPERIMENTAL_FLAGS_CONFIG_FILENAME

    @override
    def load_full_config(
        self, site_specific: bool = False, custom_site_path: str | None = None
    ) -> GlobalSettings:
        # Without a staged file nothing has been changed since the last activation,
        # e.g. right after an update, so the active file is the current state.
        candidates = [self.config_file(site_specific), self.active_config_file()]
        if custom_site_path:
            candidates = [Path(custom_site_path) / f.relative_to(omd_root) for f in candidates]
        filename = next((f for f in candidates if f.exists()), None)
        if filename is None:
            return {}
        return dict(_load_flags(filename).model_dump(exclude_unset=True))

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
        store.save_text_to_file(filename, config.model_dump_json(indent=2, exclude_unset=True))

    @override
    def save_site_globals(
        self, settings: GlobalSettings, custom_site_path: str | None = None
    ) -> None:
        pass

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # Move the final flags in place in the create artifacts stage, so consumers
        # can use them in the activate stage.
        staged = self.config_file(site_specific=False)
        self._flags_changed = False
        if staged.exists():
            before = load_experimental_flags(self.config_dir())
            staged.replace(self.active_config_file())
            self._flags_changed = load_experimental_flags(self.config_dir()) != before
        return []

    def drop_undeclared_flags(self) -> None:
        for config_file in (self.config_file(site_specific=False), self.active_config_file()):
            if config_file.exists():
                config = _load_flags(config_file)
                store.save_text_to_file(
                    config_file, config.model_dump_json(indent=2, exclude_unset=True)
                )

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        if not self._flags_changed:
            return []
        self._flags_changed = False
        return self._restart_site()

    def _restart_site(self) -> ConfigurationWarnings:
        completed_process = subprocess.run(
            ["omd", "restart"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            encoding="utf-8",
            check=False,
        )
        return [completed_process.stdout] if completed_process.returncode else []

    @override
    def default_globals(self) -> GlobalSettings:
        return ExperimentalFlagConfig().model_dump()


ConfigVariableGroupExperimentalFlags = ConfigVariableGroup(
    title=_l("Experimental flags (for testing only)"),
    sort_index=200,
    icon=IconNames.experiment,
    description=_l("Configures temporary auto-generated flags tied to features"),
)


def _make_flag_config_variable(
    name: str, field_info: FieldInfo, *, in_global_settings: bool
) -> ConfigVariable:
    extra = field_info.json_schema_extra or {}
    assert isinstance(extra, dict)
    description = str(extra.get("description", ""))
    remove_after = str(extra.get("remove_after", ""))
    help_text = Help(
        "%(description)s<br><br>This is a temporary experimental flag. It is scheduled for "
        "removal in version %(remove_after)s and must not be relied on for permanent "
        "configuration."
    ) % {"description": description, "remove_after": remove_after}
    return ConfigVariable(
        group=ConfigVariableGroupExperimentalFlags,
        primary_domain=ConfigDomainExperimentalFlags,
        ident=name,
        form_spec=lambda context: fs.BooleanChoice(  # noqa: ARG005
            title=Title(name),  # astrein: disable=localization-checker
            label=Label("Enabled"),
            help_text=help_text,
        ),
        in_global_settings=in_global_settings,
    )


def experimental_flag_config_variables(*, in_global_settings: bool) -> list[ConfigVariable]:
    return [
        _make_flag_config_variable(name, field_info, in_global_settings=in_global_settings)
        for name, field_info in ExperimentalFlagConfig.model_fields.items()
    ]
