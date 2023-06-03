// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import "forms";

import * as ajax from "ajax";
import * as foldable_container from "foldable_container";
import * as popup_menu from "popup_menu";
import * as quicksearch from "quicksearch";
import * as search from "search";
import * as sidebar from "sidebar";
import * as utils from "utils";
import * as valuespecs from "valuespecs";
import * as visibility_detection from "visibility_detection";

export const cmk_export = {
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
