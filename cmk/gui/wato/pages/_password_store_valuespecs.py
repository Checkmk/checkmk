#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    DropdownChoice,
    Migrate,
    MigrateNotUpdated,
    Password,
    ValueSpecHelp,
)
from cmk.gui.watolib.password_store import passwordstore_choices


def IndividualOrStoredPassword(
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
) -> CascadingDropdown:
    """ValueSpec for a password that can be entered directly or selected from a password store

    One should look into using :func:`password_store.extract` to translate the reference to the
    actual password.
    """
    return CascadingDropdown(
        title=title,
        help=help,
        choices=[
            (
                "password",
                _("Explicit"),
                Password(
                    allow_empty=allow_empty,
                    size=size,
                ),
            ),
            (
                "store",
                _("From password store"),
                DropdownChoice(
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
    )


PasswordFromStore = IndividualOrStoredPassword  # CMK-12228


def MigrateNotUpdatedToIndividualOrStoredPassword(
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
) -> MigrateNotUpdated:
    return MigrateNotUpdated(
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
    help: ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
) -> Migrate:
    return Migrate(
        valuespec=IndividualOrStoredPassword(
            title=title,
            help=help,
            allow_empty=allow_empty,
            size=size,
        ),
        migrate=lambda v: ("password", v) if not isinstance(v, tuple) else v,
    )
