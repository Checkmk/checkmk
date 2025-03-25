#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from unittest.mock import MagicMock, patch

import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success

ICON: vs.IconSelectorModel = {"icon": "crash", "emblem": None}
ICON_WRONG_TYPE: vs.IconSelectorModel = {"icon": 123, "emblem": None}  # type: ignore[typeddict-item]
ICON_NOT_EXISTANT: vs.IconSelectorModel = {"icon": "asd", "emblem": None}
ICON_EMBLEM: vs.IconSelectorModel = {"icon": "graph", "emblem": "add"}
ICON_EMBLEM_NOT_EXISTANT: vs.IconSelectorModel = {"icon": "graph", "emblem": "xxx123xxx"}
ICON_EMBLEM_WRONG_TYPE: vs.IconSelectorModel = {"icon": "graph", "emblem": 123}  # type: ignore[typeddict-item]
# TODO: by type icon may not be None, but code explicitly tests for this...
ICON_NONE: vs.IconSelectorModel = {"icon": None, "emblem": None}  # type: ignore[typeddict-item]


class TestValueSpecFloat:
    @patch(
        "cmk.gui.valuespec.definitions.IconSelector.available_icons",
        return_value=["empty", "crash", "graph"],
    )
    @patch(
        "cmk.gui.valuespec.definitions.IconSelector.available_emblems",
        return_value=["add"],
    )
    def test_validate(self, _mock_icons: MagicMock, _mock_emblems: MagicMock) -> None:
        # ## value may be a string, or a dictionary.
        # ## first test string...
        expect_validate_failure(vs.IconSelector(), "asd", match="The selected icon does not exist.")

        # TODO: validate_value allows None, ...
        vs.IconSelector().validate_value(None, "")
        vs.IconSelector().validate_datatype(None, "")

        # ## ...then test dictionary:
        expect_validate_failure(
            vs.IconSelector(), ICON_NOT_EXISTANT, match="The selected icon does not exist."
        )

        expect_validate_failure(
            vs.IconSelector(allow_empty=False),
            ICON_NONE,
            match="You need to select an icon.",
        )

        expect_validate_success(
            vs.IconSelector(),
            ICON,
        )
        expect_validate_success(
            vs.IconSelector(),
            ICON_EMBLEM,
        )
        expect_validate_failure(
            vs.IconSelector(),
            ICON_EMBLEM_NOT_EXISTANT,
            match="The selected emblem does not exist.",
        )

        expect_validate_failure(
            vs.IconSelector(with_emblem=False),
            ICON_EMBLEM,
            # TODO: error message string is wrong!
            match=re.escape("The type is <class 'dict'>, but should be str or dict"),
        )

        # TODO: with_emblem=False seems to enforce usage of str instead of dict
        # although the dict only contains a icon and no emblem. a bit confusing?
        expect_validate_failure(
            vs.IconSelector(with_emblem=False),
            ICON,
            match=re.escape("The type is <class 'dict'>, but should be str or dict"),
        )

        expect_validate_success(
            vs.IconSelector(with_emblem=True),
            ICON_NONE,
        )

        expect_validate_failure(
            # TODO: this only works with with_emblem=True, but emblem is None,..
            # same issue as above with_emblem=False seems to enforce usage of str.
            vs.IconSelector(with_emblem=True),
            ICON_WRONG_TYPE,
            match=re.escape("The icon type is <class 'int'>, but should be str"),
        )

        expect_validate_failure(
            vs.IconSelector(with_emblem=True),
            ICON_EMBLEM_WRONG_TYPE,
            match=re.escape("The emblem type is <class 'int'>, but should be str"),
        )

        # TODO: Rule "Icon image for service in status GUI"
        # displays the following error message when created:
        #   Unable to read current options of this rule. Falling back to
        #   default values. When saving this rule now, your previous settings
        #   will be overwritten. Problem was: The type is <class 'NoneType'>,
        #   but should be str or dict.

    # TODO: empty_img should be renamed to "default_icon" (?)
    # internally there is still a lot of hard coded "empty" stuff.

    # value_to_html seems to ignore emblem!
