#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel, ValidationError

import cmk.utils.store as store
from cmk.utils.config_validation_layer.type_defs import Omitted, remove_omitted
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError
from cmk.utils.paths import omd_root
from cmk.utils.plugin_registry import Registry

from cmk.gui.config import active_config
from cmk.gui.watolib.config_domain_name import wato_fileheader
from cmk.gui.watolib.utils import format_config_value

_G = TypeVar("_G")
_T = TypeVar("_T")
_P = TypeVar("_P", bound=BaseModel)


class WatoConfigFile(ABC, Generic[_G]):
    """Manage simple .mk config file

    The file handling logic is inherited from cmk.utils.store.load_from_mk_file()
    and cmk.utils.store.save_to_mk_file().
    """

    def __init__(self, config_file_path: Path) -> None:
        self._config_file_path = config_file_path

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
        raise NotImplementedError("NotImplemented")


class WatoListConfigFile(WatoConfigFile, Generic[_G]):
    """Manage simple .mk config file containing a list of objects."""

    def __init__(self, config_file_path: Path, config_variable: str) -> None:
        super().__init__(config_file_path)
        self._config_variable = config_variable

    @abstractmethod
    def load_for_reading(self) -> Sequence[_G]: ...

    @abstractmethod
    def load_for_modification(self) -> list[_G]: ...

    @abstractmethod
    def save(self, cfg: Sequence[_G]) -> None: ...


class WatoSingleConfigFile(WatoConfigFile[_T], Generic[_T]):
    """Manage simple .mk config file containing a single dict variable which represents
    the overall configuration. The 1st level dict represents the configuration
    {base_url: ..., credentials: ...}
    """

    def __init__(self, config_file_path: Path, config_variable: str) -> None:
        super().__init__(config_file_path)
        self._config_variable = config_variable

    def _load_file(self, lock: bool) -> _T:
        return store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default={},
            lock=lock,
        )

    def save(self, cfg: _T) -> None:
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

    def filter_usable_entries(self, entries: dict[str, _T]) -> dict[str, _T]:
        return entries

    def filter_editable_entries(self, entries: dict[str, _T]) -> dict[str, _T]:
        return entries


class WatoPydanticConfigFile(WatoConfigFile[_P], Generic[_P]):
    """Manage .mk config file based on a pydantic model."""

    def __init__(
        self,
        config_file_path: Path,
        model_class: type[_P],
        load_default: Callable[[], _P] | None = None,
    ) -> None:
        super().__init__(
            config_file_path=config_file_path,
        )
        self.model_class = model_class
        self.load_default: Callable[[], _P] = model_class if load_default is None else load_default  # type: ignore[assignment]

    def _validate(self, raw: dict[str, Any]) -> _P:
        try:
            return self.model_class.model_validate(raw)
        except ValidationError as exc:
            raise ConfigValidationError(
                which_file=self.name,
                pydantic_error=exc,
                original_data=raw,
            ) from exc

    def _load_file(self, lock: bool = False) -> _P:
        cfg = store.load_mk_file(
            self._config_file_path,
            default=self.load_default().model_dump(),
            lock=lock,
        )
        return self._validate(dict(cfg))

    def save(self, cfg: _P) -> None:
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        output = wato_fileheader()
        for field, value in cfg.model_dump().items():
            if isinstance(value, Omitted):
                continue  # completely skip omitted values
            value = remove_omitted(value)  # remove nested omitted values
            output += "{} = \\\n{}\n\n".format(
                field,
                format_config_value(value),
            )
        store.save_mk_file(self._config_file_path, output, add_header=False)

    def validate_and_save(self, raw: dict[str, Any]) -> None:
        cfg = self._validate(raw)
        self.save(cfg)


class ConfigFileRegistry(Registry[WatoConfigFile]):
    def plugin_name(self, instance: WatoConfigFile) -> str:
        return instance.name


config_file_registry = ConfigFileRegistry()
