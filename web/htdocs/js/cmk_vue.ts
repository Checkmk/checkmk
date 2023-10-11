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

// BUILD TO BE THROWN AWAY
// @ts-ignore
function modify_save_button(mounted_div) {
    // Note: this function will be thrown away once the "Save" action gets a better implementation
    //       I'm not going to fix the typing here.
    // It modifies the submit action. Collects the vue values and puts it into a request parameter as json
    const save_links = document.querySelectorAll<HTMLAnchorElement>(
        'a[onclick^="cmk.page_menu.form_submit"]'
    );
    save_links.forEach(save_link => {
        const orig_event_function = save_link.onclick;
        if (orig_event_function == null) return;

        function modified_save_function(event: Event) {
            // @ts-ignore
            mounted_div.update_form_field();
            // Since vue updates the DOM asynchron the changed value in the forms input field
            // is not updated before the form is sent. Workaround. As usual -> to be thrown away
            // @ts-ignore
            setTimeout(() => orig_event_function(event), 100);
        }

        save_link.onclick = modified_save_function;
    });
}

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
                const mounted_div = app.mount(div);
                modify_save_button(mounted_div);
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
