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
import * as main_menu_shortcut_handler from "./modules/main_menu_shortcut_handler";
import * as popup_menu from "./modules/popup_menu";
import * as quicksearch from "./modules/quicksearch";
import * as search from "./modules/search";
import * as sidebar from "./modules/sidebar";
import * as utils from "./modules/utils";
import * as valuespecs from "./modules/valuespecs";
import * as visibility_detection from "./modules/visibility_detection";
import {getKeyShortcutServiceInstance} from "./modules/keyShortcuts";

$(() => {
    const keyShortcuts = getKeyShortcutServiceInstance(
        document.getElementsByTagName("iframe"),
    );

    main_menu_shortcut_handler.register_shortcuts(keyShortcuts);
});

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
