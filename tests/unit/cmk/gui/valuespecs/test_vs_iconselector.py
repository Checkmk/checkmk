#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from unittest.mock import MagicMock, patch

import cmk.gui.valuespec as vs
from cmk.gui.type_defs import DynamicIconName
from cmk.gui.utils.output_funnel import output_funnel

from .utils import (
    expect_validate_failure,
    expect_validate_failure_untypeable,
    expect_validate_success,
    request_var,
)

# A few types below are plain lies...
ICON: vs.IconSelectorModel = {"icon": DynamicIconName("crash"), "emblem": None}
ICON_WRONG_TYPE: vs.IconSelectorModel = {"icon": 123, "emblem": None}  # type: ignore[assignment]
ICON_NOT_EXISTANT: vs.IconSelectorModel = {"icon": DynamicIconName("asd"), "emblem": None}
ICON_EMBLEM: vs.IconSelectorModel = {"icon": DynamicIconName("graph"), "emblem": "add"}
ICON_EMBLEM_NOT_EXISTANT: vs.IconSelectorModel = {
    "icon": DynamicIconName("graph"),
    "emblem": "xxx123xxx",
}
ICON_EMBLEM_WRONG_TYPE: vs.IconSelectorModel = {"icon": "graph", "emblem": 123}  # type: ignore[assignment]
ICON_NONE: vs.IconSelectorModel = {"icon": None, "emblem": None}  # type: ignore[assignment]


class TestValueSpecFloat:
    @patch(
        "cmk.gui.valuespec.definitions.IconSelector.available_icons",
        return_value=["empty", "crash", "graph"],
    )
    @patch(
        "cmk.gui.valuespec.definitions.IconSelector.available_emblems",
        return_value=["add"],
    )
    def test_validate(self, _mock_icons: MagicMock, _mock_emblems: MagicMock) -> None:  # type: ignore[misc]
        # ## value may be a string, or a dictionary.
        # ## first test string...
        expect_validate_failure_untypeable(
            vs.IconSelector(), "asd", match="The selected icon does not exist."
        )

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

    @patch(
        "cmk.gui.theme._theme_type.Theme.detect_icon_path",
        return_value="some_random_icon_path.svg",
    )
    def test_render_input_complain_phase_keeps_stored_icon(  # type: ignore[misc]
        self, _mock_icon_path: MagicMock, request_context: None
    ) -> None:
        """In the complain phase the surrounding valuespecs render their default value
        (None) instead of the stored one, so the icon has to be recovered from the HTML
        vars. Otherwise a single invalid entry blanks out all icons of a list."""
        with request_var(icon_value="crash", icon_emblem_value="add"), output_funnel.plugged():
            vs.IconSelector().render_input("icon", None)
            rendered = output_funnel.drain()

        assert 'value="crash"' in rendered
        assert 'value="add"' in rendered

    @patch(
        "cmk.gui.theme._theme_type.Theme.detect_icon_path",
        return_value="some_random_icon_path.svg",
    )
    def test_render_input_back_url_excludes_form_vars(  # type: ignore[misc]
        self, _mock_icon_path: MagicMock, request_context: None
    ) -> None:
        """The back URL of the popup must not carry the form vars of the surrounding
        valuespec: with long lists the request line grows beyond the web server limit."""
        with (
            request_var(
                mode="edit_configvar",
                varname="user_icons_and_actions",
                ve_1_1_p_icon_value="crash",
            ),
            output_funnel.plugged(),
        ):
            vs.IconSelector().render_input("ve_1_1_p_icon", None)
            rendered = output_funnel.drain()

        # both are url encoded within the back parameter
        assert "mode%3Dedit_configvar" in rendered
        assert "%3Dcrash" not in rendered

    # TODO: empty_img should be renamed to "default_icon" (?)
    # internally there is still a lot of hard coded "empty" stuff.

    # value_to_html seems to ignore emblem!
