// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import "forms";
import * as ajax from "ajax";
import * as utils from "utils";
import * as foldable_container from "foldable_container";
import * as sidebar from "sidebar";
import * as quicksearch from "quicksearch";
import * as visibility_detection from "visibility_detection";
import * as valuespecs from "valuespecs";
import * as popup_menu from "popup_menu";
import * as search from "search";

export const cmk_export = {
    get_url: ajax.get_url,
    post_url: ajax.post_url,
    call_ajax: ajax.call_ajax,
    cmk: {
        ajax: ajax,
        sidebar: sidebar,
        utils: utils,
        foldable_container: foldable_container,
        quicksearch: quicksearch,
        visibility_detection: visibility_detection,
        valuespecs: valuespecs,
        popup_menu: popup_menu,
        search: search,
    },
};
