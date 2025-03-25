/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {render_stats_table} from "@/modules/tracking_display";
import {render_qr_code} from "@/modules/qrcode_rendering";
import {insert_before} from "@/modules/layout";
import {lock_and_redirect} from "@/modules/sites";

type CallableFunctionArguments = {[key: string]: string};
type CallableFunction = (
    node: HTMLElement,
    options: CallableFunctionArguments,
) => Promise<void>;
// See cmk.gui.htmllib.generator:KnownTSFunction
// The type on the Python side and the available keys in this dictionary MUST MATCH.
const callable_functions: {[name: string]: CallableFunction} = {
    render_stats_table: render_stats_table,
    render_qr_code: render_qr_code,
    insert_before: insert_before,
    lock_and_redirect: lock_and_redirect,
};

export function init_callable_ts_functions(element: Element | Document) {
    // See cmk.gui.htmllib.generator:HTMLWriter.call_ts_function
    element
        .querySelectorAll<HTMLElement>("*[data-cmk_call_ts_function]")
        .forEach((container, _) => {
            const data = container.dataset;
            const function_name: string = data.cmk_call_ts_function!;
            let args: CallableFunctionArguments; // arguments is a restricted name in JavaScript
            if (data.cmk_call_ts_arguments) {
                args = JSON.parse(data.cmk_call_ts_arguments);
            } else {
                args = {};
            }
            const ts_function = callable_functions[function_name];
            // The function has the responsibility to take the container and do it's thing with it.
            ts_function(container, args);
        });
}
