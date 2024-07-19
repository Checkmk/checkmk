/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import "./modules/forms";

import $ from "jquery";

/* eslint-disable import/no-namespace -- Needed for exports */
import * as ajax from "./modules/ajax";
import * as foldable_container from "./modules/foldable_container";
import * as keyboard_shortcuts from "./modules/keyboard_shortcuts";
import * as popup_menu from "./modules/popup_menu";
import * as quicksearch from "./modules/quicksearch";
import * as search from "./modules/search";
import * as sidebar from "./modules/sidebar";
import * as utils from "./modules/utils";
import * as valuespecs from "./modules/valuespecs";
import * as visibility_detection from "./modules/visibility_detection";

$(() => {
    keyboard_shortcuts.register_shortcuts();
});

export const cmk_export = {
    call_ajax: ajax.call_ajax,
    cmk: {
        ajax: ajax,
        sidebar: sidebar,
        utils: utils,
        keyboard_shortcuts: keyboard_shortcuts,
        foldable_container: foldable_container,
        quicksearch: quicksearch,
        visibility_detection: visibility_detection,
        valuespecs: valuespecs,
        popup_menu: popup_menu,
        search: search,
    },
};
