#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import typing

from cmk.gui.exceptions import MKUserError

from cmk.rulesets.v1._localize import Message
from cmk.rulesets.v1.form_specs import validators

from .. import definitions

T = typing.TypeVar("T")

ModelT = typing.TypeVar("ModelT")

ValidatorType = typing.Callable[[ModelT], None]


def all_of(validator_list: typing.Sequence[ValidatorType[ModelT]]) -> ValidatorType[ModelT]:
    if len(validator_list) == 1:
        validator = validator_list[0]
    else:
        validator = CompoundValidator[ModelT](validator_list)

    return validator


class TextValidator:
    def __init__(self, min_length: int | None, max_length: int | None) -> None:
        self.min_length = min_length
        self.max_length = max_length

    def __call__(self, value: str) -> None:
        length = len(value)
        if self.min_length is not None and self.min_length > length:
            raise validators.ValidationError(
                Message("Needs to be at least %d characters long.") % str(self.min_length)
            )
        if self.max_length is not None and self.max_length < length:
            raise validators.ValidationError(
                Message("Can maximally be %d characters long.") % str(self.max_length)
            )


class ListValidator:
    def __init__(self, min_entries: int | None, max_entries: int | None) -> None:
        self.min_entries = min_entries
        self.max_entries = max_entries

    def __call__(self, value: typing.Sequence) -> None:
        if self.min_entries is not None and len(value) < self.min_entries:
            raise validators.ValidationError(
                Message("List needs to be at least %d elements long.") % str(self.min_entries)
            )

        if self.max_entries is not None and len(value) > self.max_entries:
            raise validators.ValidationError(
                Message("List can maximally be %d elements long.") % str(self.max_entries)
            )


class ValueSpecValidator:
    def __init__(self, vs_instance: definitions.ValueSpec) -> None:
        self.vs_instance = vs_instance

    def __call__(self, value: typing.Any) -> None:
        try:
            # NOTE
            # validators given to the instance via validate=... are also called by validate_value
            self.vs_instance.validate_datatype(value, "")
            self.vs_instance.validate_value(value, "")
        except MKUserError as exc:
            raise validators.ValidationError(Message(str(exc)))


class CompoundValidator(typing.Generic[T]):
    def __init__(self, validator_list: typing.Sequence[typing.Callable[[T], None]]):
        self.validators = validator_list

    def __repr__(self):
        class_ = self.__orig_class__ if hasattr(self, "__orig_class__") else self.__class__

        def _members(attributes: dict[str, typing.Any]) -> str:
            return ", ".join(
                f"{key}={value}" for key, value in attributes.items() if not key.startswith("__")
            )

        return f"<{class_}({_members(self.__dict__)})>"

    def __call__(self, value: T) -> None:
        exceptions: list[validators.ValidationError] = []
        for validator in self.validators:
            try:
                validator(value)
            except validators.ValidationError as exc:
                exceptions.append(exc)

        if exceptions:
            message = Message("")
            for exception in exceptions:
                message = message + exception._message + Message("\n")

            raise validators.ValidationError(message)


C = typing.TypeVar("C", bound="Comparable")


# Look, mom, we finally have Haskell type classes! :-D Naive version requiring
# only <, hopefully some similar class will make it into typing soon...
class Comparable(typing.Protocol):
    @abc.abstractmethod
    def __lt__(self: C, other: C) -> bool:
        pass


class NumberValidator(typing.Generic[C]):
    def __init__(self, *, lt: C | None, gt: C | None, le: C | None, ge: C | None):
        self.lt = lt
        self.gt = gt
        self.le = le
        self.ge = ge

    def __repr__(self):
        class_ = self.__orig_class__ if hasattr(self, "__orig_class__") else self.__class__

        def _members(attributes: dict[str, typing.Any]) -> str:
            return ", ".join(
                f"{key}={value}" for key, value in attributes.items() if not key.startswith("__")
            )

        return f"<{class_}({_members(self.__dict__)})>"

    def __call__(self, value: C) -> None:
        if self.lt is not None and value > self.lt:
            raise validators.ValidationError(Message("Value should be less than %s") % str(self.lt))
        if self.gt is not None and value > self.gt:
            raise validators.ValidationError(
                Message("Value should be greater than %s") % str(self.gt)
            )
        if self.le is not None and value > self.le:
            raise validators.ValidationError(Message("Value should maximally be %s") % str(self.le))
        if self.ge is not None and value > self.ge:
            raise validators.ValidationError(Message("Value should minimally be %s") % str(self.ge))


class EnforceSuffix:
    def __init__(
        self,
        suffix: str,
        *,
        case: typing.Literal["ignore", "sensitive"],
        error_msg: Message = Message("Does not end with %s"),
    ) -> None:
        self.suffix = suffix
        self.case = case
        self.error_msg = error_msg

    def __call__(self, value: str) -> None:
        if self.case == "ignore":
            to_check = value.lower()
            suffix = self.suffix.lower()
        else:
            to_check = value
            suffix = self.suffix

        if not to_check.endswith(suffix):
            raise validators.ValidationError(self.error_msg % suffix)
