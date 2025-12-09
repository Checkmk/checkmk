#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.custom_icons._modes import validate_icon
from cmk.gui.exceptions import MKUserError


def existing_facelift_icon() -> bool:
    # icon_trust.png exists in facelift as static icon
    try:
        validate_icon(("trust.png", "", b""), "smth")
    except MKUserError:
        return True
    print("ERROR: validate_icon did not throw an error for trust.png but it should")
    return False


def existing_image_icon() -> bool:
    # cookie.png exsists as a dynamic icon (it's not themed, and it does not fit the checkmk styleguide)
    try:
        validate_icon(("cookie.png", "", b""), "smth")
    except MKUserError:
        return True
    print("ERROR: validate_icon did not throw an error for cookie.png but it should")
    return False


def icon_does_not_exist() -> bool:
    # some file that does not exist:
    validate_icon(("benedikts-custom-icon-that-is-never-created-by-accident.png", "", b""), "smth")
    return True


def main() -> None:
    # when uploading a custom icon, it's important to check if an icon with
    # the same name already exists, otherwise one would replace that icon in the site.
    #
    # you can only upload png files, so we have to use an existing png file.
    #
    # i'm pretty sure this test function is not completely correct:
    # there are many ways how a icon name can be resolved to a filename,
    # and here we just test one path.
    if not all([existing_facelift_icon(), existing_image_icon(), icon_does_not_exist()]):
        raise Exception("all function should return True")


if __name__ == "__main__":
    main()
