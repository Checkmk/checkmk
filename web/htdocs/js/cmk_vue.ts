/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import "core-js/stable";

import $ from "jquery";

function setup_vue() {
    document
        .querySelectorAll<HTMLFormElement>("div[data-cmk_vue_app]")
        .forEach((div, _) => {
            const dataset = div.dataset;
            if (dataset == undefined) return;

            const vue_app_data = dataset.cmk_vue_app;
            if (vue_app_data == undefined) return;
            const vueApp = JSON.parse(vue_app_data);

            if (vueApp.app_name == "demo") {
                // TODO: initializiation code
            } else {
                throw `can not load vue app "${vueApp.app_name}"`;
            }
        });
}

$(() => {
    // -> change to X.onload?
    setup_vue();
});

export const cmk_export = {};
