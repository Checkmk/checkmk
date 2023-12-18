/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import "core-js/stable";

import $ from "jquery";
import {createApp} from "vue";

// @ts-ignore
import Form from "./modules/cmk_vue/views/Form.vue";

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
                const app = createApp(Form, {
                    form_spec: {
                        id: vueApp.id,
                        component: vueApp.component,
                    },
                });
                app.use(Form);
                app.mount(div);
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
