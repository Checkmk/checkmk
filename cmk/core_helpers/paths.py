"""Fetcher config path manipulation."""
from pathlib import Path
from typing import Final, Literal, NewType, Union

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.type_defs import HostName

__all__ = [
    "LATEST_SERIAL",
    "ConfigSerial",
    "OptionalConfigSerial",
    "current_helper_config_serial",
    "next_helper_config_serial",
    "make_helper_config_path",
    "make_fetchers_config_path",
    "make_local_config_path",
    "make_global_config_path",
]

LATEST_SERIAL: Final[Literal["latest"]] = "latest"
# TODO(ml): The strings in ConfigSerial look like this: "0", "1", "2"...
#           We should use `int` or even better make a full-blown
#           abstraction out of that.
#           See also: a few of its "methods" are below.
ConfigSerial = NewType("ConfigSerial", str)
OptionalConfigSerial = Union[ConfigSerial, Literal["latest"]]


def current_helper_config_serial() -> ConfigSerial:
    serial: int = store.load_object_from_file(
        cmk.utils.paths.core_helper_config_dir / "serial.mk",
        default=0,
        lock=True,
    )
    return ConfigSerial(str(serial))


def next_helper_config_serial(serial: ConfigSerial) -> ConfigSerial:
    """Acquire and return the next helper config serial

    This ID is used to identify a core helper configuration generation. It is used to store the
    helper config on the file system below var/check_mk/core/helper_config/[serial]. It needs to
    be unique compared to all currently known serials (the ones that exist in the directory
    mentioned above).
    """
    int_serial: Final = int(serial) + 1
    store.save_object_to_file(
        cmk.utils.paths.core_helper_config_dir / "serial.mk",
        int_serial,
    )
    return ConfigSerial(str(int_serial))


def make_helper_config_path(serial: OptionalConfigSerial) -> Path:
    return cmk.utils.paths.core_helper_config_dir / serial


def make_fetchers_config_path(serial: ConfigSerial) -> Path:
    return make_helper_config_path(serial) / "fetchers"


def make_local_config_path(serial: ConfigSerial, host_name: HostName) -> Path:
    return make_fetchers_config_path(serial) / "hosts" / f"{host_name}.json"


def make_global_config_path(serial: ConfigSerial) -> Path:
    return make_fetchers_config_path(serial) / "global_config.json"
