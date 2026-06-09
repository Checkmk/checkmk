#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Conversions between the ``Password`` FormSpec value and the password store ``PasswordId``."""

from typing import Literal
from uuid import uuid4

from cmk.utils.password_store import PasswordId

type FormSpecPassword = (
    tuple[Literal["cmk_postprocessed"], Literal["explicit_password"], tuple[str, str]]
    | tuple[Literal["cmk_postprocessed"], Literal["stored_password"], tuple[str, str]]
)


def is_formspec_password(value: object) -> bool:
    """Whether ``value`` is a ``Password`` FormSpec value (rather than a ``PasswordId``)."""
    match value:
        case ("cmk_postprocessed", "explicit_password" | "stored_password", (str(), str())):
            return True
        case _:
            return False


def formspec_to_password_id(value: object) -> PasswordId:
    """Convert a ``Password`` FormSpec value to a ``PasswordId``. Idempotent for ``PasswordId``."""
    match value:
        case ("cmk_postprocessed", "explicit_password", (str(_password_id), str(secret))):
            return "password", secret
        case ("cmk_postprocessed", "stored_password", (str(password_store_id), str())):
            return "store", password_store_id
        case ("password", str(secret)):
            return "password", secret
        case ("store", str(password_store_id)):
            return "store", password_store_id
        case str(password_store_id):
            return password_store_id
        case _:
            raise ValueError(f"Cannot convert {value!r} to a password id.")


def password_id_to_formspec(value: object) -> FormSpecPassword:
    """Convert a ``PasswordId`` to a ``Password`` FormSpec value. Idempotent for FormSpec values."""
    match value:
        case ("cmk_postprocessed", "explicit_password", (str(password_id), str(secret))):
            return "cmk_postprocessed", "explicit_password", (password_id, secret)
        case ("cmk_postprocessed", "stored_password", (str(password_store_id), str(secret))):
            return "cmk_postprocessed", "stored_password", (password_store_id, secret)
        case ("password", str(secret)):
            return "cmk_postprocessed", "explicit_password", (str(uuid4()), secret)
        case ("store", str(password_store_id)):
            return "cmk_postprocessed", "stored_password", (password_store_id, "")
        case str(password_store_id):
            return "cmk_postprocessed", "stored_password", (password_store_id, "")
        case _:
            raise ValueError(f"Cannot convert {value!r} to a password.")
