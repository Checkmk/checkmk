from dataclasses import dataclass
from enum import auto, Enum
from typing import Any

DataForDisk = Any
Value = Any


class DefaultValue:
    pass


DEFAULT_VALUE = DefaultValue()


class DataOrigin(Enum):
    DISK = auto()
    FRONTEND = auto()


@dataclass
class VisitorOptions:
    # Depending on the origin, we will call the migrate function
    data_origin: DataOrigin


class EmptyValue:
    pass


EMPTY_VALUE = EmptyValue()
