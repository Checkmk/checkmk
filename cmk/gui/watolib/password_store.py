#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import subprocess
from collections.abc import Mapping
from typing import Literal, override

from cmk.ccc import store
from cmk.gui import userdb, valuespec
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Choices
from cmk.gui.valuespec import DropdownChoice, Transform, ValueSpecValidateFunc
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir
from cmk.utils import password_store
from cmk.utils.password_store import ad_hoc_password_id, Password


class PasswordStore(WatoSimpleConfigFile[Password]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=wato_root_dir() / "passwords.mk",
            config_variable="stored_passwords",
            spec_class=Password,
        )

    def filter_usable_entries(self, entries: dict[str, Password]) -> dict[str, Password]:
        if user.may("wato.edit_all_passwords"):
            return entries

        assert user.id is not None
        user_groups = set(userdb.contactgroups_of_user(user.id))

        passwords = self.filter_editable_entries(entries)
        passwords.update(
            {k: v for k, v in entries.items() if set(v["shared_with"]).intersection(user_groups)}
        )
        return passwords

    def filter_editable_entries(self, entries: dict[str, Password]) -> dict[str, Password]:
        if user.may("wato.edit_all_passwords"):
            return entries

        assert user.id is not None
        user_groups = userdb.contactgroups_of_user(user.id)
        return {k: v for k, v in entries.items() if v["owned_by"] in user_groups}

    @override
    def _load_file(self, *, lock: bool) -> dict[str, Password]:
        """The actual passwords are stored in a separate file for special treatment

        Have a look at `cmk.utils.password_store` for further information"""
        cfg = join_password_specs(
            store.load_from_mk_file(
                self._config_file_path,
                key=self._config_variable,
                default={},
                lock=lock,
            ),
            password_store.load(password_store.password_store_path()),
        )
        return cfg

    @override
    def save(self, cfg: Mapping[str, Password], pprint_value: bool) -> None:
        """The actual passwords are stored in a separate file for special treatment

        Have a look at `cmk.utils.password_store` for further information"""
        meta_data, passwords = split_password_specs(cfg)
        super().save(meta_data, pprint_value)
        password_store.save(passwords, password_store.password_store_path())
        update_passwords_merged_file()


def update_passwords_merged_file() -> None:
    # update the "live" merged passwords file
    subprocess.check_call(
        ["cmk", "--automation", "update-passwords-merged-file"], stdout=subprocess.DEVNULL
    )


def join_password_specs(
    meta_data: Mapping[str, Password], passwords: Mapping[str, str]
) -> dict[str, Password]:
    """Join passwords with meta data"""
    joined: dict[str, Password] = {}
    for password_id, password_spec in meta_data.items():
        joined[password_id] = password_spec.copy()
        joined[password_id]["password"] = passwords.get(password_id, "")
    return joined


def split_password_specs(
    joined: Mapping[str, Password],
) -> tuple[dict[str, Password], dict[str, str]]:
    """Separate passwords from meta data"""
    meta_data, passwords = {}, {}
    for password_id, joined_password in joined.items():
        meta_data[password_id] = joined_password.copy()
        passwords[password_id] = meta_data[password_id]["password"]
        meta_data[password_id]["password"] = ""
    return meta_data, passwords


@request_memoize()
def passwordstore_choices() -> Choices:
    pw_store = PasswordStore()
    return [
        (ident, pw["title"])
        for ident, pw in pw_store.filter_usable_entries(pw_store.load_for_reading()).items()
    ]


# TODO remove this once a solution for use of passwordstore_choices is found
def passwordstore_choices_without_user() -> Choices:
    pw_store = PasswordStore()
    return [(ident, pw["title"]) for ident, pw in pw_store.load_for_reading().items()]


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(PasswordStore())


def IndividualOrStoredPassword(
    title: str | None = None,
    help: valuespec.ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
    validate: ValueSpecValidateFunc | None = None,
) -> valuespec.CascadingDropdown:
    """ValueSpec for a password that can be entered directly or selected from a password store

    One should look into using :func:`password_store.extract` to translate the reference to the
    actual password.
    """
    return valuespec.CascadingDropdown(
        title=title,
        help=help,
        choices=[
            (
                "password",
                _("Explicit"),
                valuespec.Password(
                    allow_empty=allow_empty,
                    size=size,
                ),
            ),
            (
                "store",
                _("From password store"),
                valuespec.DropdownChoice(
                    choices=passwordstore_choices,
                    sorted=True,
                    invalid_choice="complain",
                    invalid_choice_title=_("Password does not exist or using not permitted"),
                    invalid_choice_error=_(
                        "The configured password has either be removed or you "
                        "are not permitted to use this password. Please choose "
                        "another one."
                    ),
                ),
            ),
        ],
        orientation="horizontal",
        validate=validate,
    )


def MigrateNotUpdatedToIndividualOrStoredPassword(
    title: str | None = None,
    help: valuespec.ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
) -> valuespec.MigrateNotUpdated:
    return valuespec.MigrateNotUpdated(
        valuespec=IndividualOrStoredPassword(
            title=title,
            help=help,
            allow_empty=allow_empty,
            size=size,
        ),
        migrate=lambda v: ("password", v) if not isinstance(v, tuple) else v,
    )


def MigrateToIndividualOrStoredPassword(
    title: str | None = None,
    help: valuespec.ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
    validate: ValueSpecValidateFunc | None = None,
) -> valuespec.Migrate:
    return valuespec.Migrate(
        valuespec=IndividualOrStoredPassword(
            title=title,
            help=help,
            allow_empty=allow_empty,
            size=size,
            validate=validate,
        ),
        migrate=lambda v: ("password", v) if not isinstance(v, tuple) else v,
    )


def postprocessable_ios_password(
    *,
    title: str | None,
    help_text: str | None = None,
    validate: ValueSpecValidateFunc | None = None,
) -> Transform:
    return Transform(
        IndividualOrStoredPassword(
            title=title,
            help=help_text,
            allow_empty=False,
        ),
        forth=_transform_password_forth,
        back=_transform_password_back,
        validate=validate,
    )


def _transform_password_forth(value: object) -> tuple[str, str]:
    match value:
        case "cmk_postprocessed", "explicit_password", (str(), str(password)):
            return "password", password
        case "cmk_postprocessed", "stored_password", (str(password_store_id), str()):
            return "store", password_store_id
        case _other:
            raise ValueError(value)


def _transform_password_back(
    value: tuple[str, str],
) -> tuple[
    Literal["cmk_postprocessed"], Literal["explicit_password", "stored_password"], tuple[str, str]
]:
    match value:
        case "password", str(password):
            return "cmk_postprocessed", "explicit_password", (ad_hoc_password_id(), password)
        case "store", str(password_store_id):
            return "cmk_postprocessed", "stored_password", (password_store_id, "")
        case _other:
            raise ValueError(value)


def _transform_passwordstore_password_forth(value: object) -> str:
    match value:
        case "cmk_postprocessed", "stored_password", (str(password_store_id), str()):
            return password_store_id
        case _other:
            raise ValueError(value)


def _transform_passwordstore_password_back(
    value: str,
) -> tuple[Literal["cmk_postprocessed"], Literal["stored_password"], tuple[str, str]]:
    match value:
        case str(password_store_id):
            return "cmk_postprocessed", "stored_password", (password_store_id, "")
        case _other:
            raise ValueError(value)


def postprocessable_passwordstore_password(
    title: str | None,
    help_text: str | None,
    validate: ValueSpecValidateFunc | None,
) -> Transform:
    return Transform(
        DropdownChoice(
            title=title,
            help=help_text,
            choices=passwordstore_choices,
            empty_text="No passwords configured yet",
        ),
        forth=_transform_passwordstore_password_forth,
        back=_transform_passwordstore_password_back,
        validate=validate,
    )
