#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, cast, Generic, Mapping, TypeAlias, TypeVar

from pydantic import TypeAdapter, ValidationError

from cmk.utils import store
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError
from cmk.utils.paths import omd_root
from cmk.utils.plugin_registry import Registry

from cmk.gui.config import active_config
from cmk.gui.watolib.config_domain_name import wato_fileheader
from cmk.gui.watolib.utils import format_config_value

_G = TypeVar("_G")
_T = TypeVar("_T")
_D = TypeVar("_D", bound=Mapping)


class WatoConfigFile(ABC, Generic[_G]):
    """Manage simple .mk config file

    The file handling logic is inherited from cmk.utils.store.load_from_mk_file()
    and cmk.utils.store.save_to_mk_file().
    """

    def __init__(
        self,
        config_file_path: Path,
        spec_class: TypeAlias,
    ) -> None:
        self._config_file_path = config_file_path
        self.validator = TypeAdapter(spec_class)

    def _validate(self, raw: object) -> _G:
        try:
            return self.validator.validate_python(raw, strict=True)
        except ValidationError as exc:
            raise ConfigValidationError(
                which_file=self.name,
                pydantic_error=exc,
                original_data=raw,
            ) from exc

    def load_for_reading(self) -> _G:
        return self._load_file(lock=False)

    def load_for_modification(self) -> _G:
        return self._load_file(lock=True)

    @abstractmethod
    def _load_file(self, lock: bool) -> _G: ...

    @abstractmethod
    def save(self, cfg: _G) -> None: ...

    @property
    def name(self) -> str:
        return self._config_file_path.relative_to(omd_root).as_posix()

    def read_file_and_validate(self) -> None:
        cfg = self._load_file(lock=False)
        self._validate(cfg)


class WatoListConfigFile(WatoConfigFile[list[_G]], Generic[_G]):
    """Manage simple .mk config file containing a list of objects."""

    def __init__(
        self,
        config_file_path: Path,
        config_variable: str,
        spec_class: TypeAlias,
    ) -> None:
        super().__init__(config_file_path, list[spec_class])
        self._config_variable = config_variable

    def _load_file(self, lock: bool) -> list[_G]:
        return store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default=[],
            lock=lock,
        )

    def save(self, cfg: list[_G]) -> None:
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(
            str(self._config_file_path),
            self._config_variable,
            cfg,
            pprint_value=active_config.wato_pprint_config,
        )


class WatoSingleConfigFile(WatoConfigFile[_D], Generic[_D]):
    """Manage simple .mk config file containing a single dict variable which represents
    the overall configuration. The 1st level dict represents the configuration
    {base_url: ..., credentials: ...}
    """

    def __init__(self, config_file_path: Path, config_variable: str, spec_class: TypeAlias) -> None:
        super().__init__(config_file_path, spec_class)
        self._config_variable = config_variable

    def _load_file(self, lock: bool) -> _D:
        return store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default={},
            lock=lock,
        )

    def save(self, cfg: _D) -> None:
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(
            str(self._config_file_path),
            self._config_variable,
            cfg,
            pprint_value=active_config.wato_pprint_config,
        )


class WatoSimpleConfigFile(WatoSingleConfigFile[dict[str, _T]], Generic[_T]):
    """Manage simple .mk config file containing a single dict variable
    with nested entries. The 1st level dict encompasses those entries where each entry
    has its own configuration.

    An example is {"password_1": {...}, "password_2": {...}}
    """

    def __init__(self, config_file_path: Path, config_variable: str, spec_class: TypeAlias) -> None:
        super().__init__(config_file_path, config_variable, dict[str, spec_class])

    def filter_usable_entries(self, entries: dict[str, _T]) -> dict[str, _T]:
        return entries

    def filter_editable_entries(self, entries: dict[str, _T]) -> dict[str, _T]:
        return entries


class WatoMultiConfigFile(WatoConfigFile[_D], Generic[_D]):
    """Manage .mk config file with multiple keys.

    Use a typed dict to specify different types per field."""

    def __init__(
        self,
        config_file_path: Path,
        spec_class: TypeAlias,
        load_default: Callable[[], _D],
    ) -> None:
        super().__init__(
            config_file_path=config_file_path,
            spec_class=spec_class,
        )
        self.load_default = load_default

    def _load_file(self, lock: bool) -> _D:
        cfg = store.load_mk_file(
            self._config_file_path,
            default=self.load_default(),
            lock=lock,
        )
        return cast(_D, cfg)

    def save(self, cfg: _D) -> None:
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        output = wato_fileheader()
        for field, value in cfg.items():
            output += "{} = \\\n{}\n\n".format(
                field,
                format_config_value(value),
            )
        store.save_mk_file(self._config_file_path, output, add_header=False)

    def validate_and_save(self, raw: Mapping[str, object]) -> None:
        with_defaults = dict(self.load_default())
        with_defaults.update(raw)
        cfg = self._validate(with_defaults)
        self.save(cfg)


class ConfigFileRegistry(Registry[WatoConfigFile]):
    def plugin_name(self, instance: WatoConfigFile) -> str:
        return instance.name


config_file_registry = ConfigFileRegistry()
