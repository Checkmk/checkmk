/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";

// @ts-ignore
declare let XDomainRequest;
//# +--------------------------------------------------------------------+
//# | Posting crash report to official Checkmk crash reporting API      |
//# '--------------------------------------------------------------------'

export function submit_crash_report(url: string, post_data: string) {
    document.getElementById("pending_msg")!.style.display = "block";

    if (has_cross_domain_ajax_support()) {
        call_ajax(url, {
            method: "POST",
            post_data: post_data,
            response_handler: handle_report_response,
            error_handler: handle_report_error,
            add_ajax_id: false,
            handler_data: {
                base_url: url,
            },
        });
    } else if (typeof XDomainRequest !== "undefined") {
        // IE < 9 does not support cross domain ajax requests in the standard way.
        // workaround this issue by doing some iframe / form magic
        submit_with_ie(url, post_data);
    } else {
        handle_report_error(
            null,
            null,
            "Your browser does not support direct reporting.",
        );
    }
}

function has_cross_domain_ajax_support() {
    return "withCredentials" in new XMLHttpRequest();
}

// @ts-ignore
function submit_with_ie(url, post_data) {
    const handler_data = {
        base_url: url,
    };
    //not sure if this is the best solution
    //see for another solution: https://stackoverflow.com/questions/66120513/property-does-not-exist-on-type-window-typeof-globalthis
    const xdr = new (window as any).XDomainRequest();
    xdr.onload = function () {
        handle_report_response(handler_data, xdr.responseText);
    };
    xdr.onerror = function () {
        handle_report_error(handler_data, null, xdr.responseText);
    };
    // eslint-disable-next-line @typescript-eslint/no-empty-function
    xdr.onprogress = function () {};
    xdr.open("post", url);
    xdr.send(post_data);
}

function handle_report_response(
    _handler_data: {base_url: string},
    response_body: string,
) {
    hide_report_processing_msg();

    if (response_body.substr(0, 2) == "OK") {
        const id = response_body.split(" ")[1];
        const success_container = document.getElementById("success_msg")!;
        success_container.style.display = "block";
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        success_container.innerHTML = success_container.innerHTML.replace(
            /###ID###/,
            id,
        );
    } else {
        const fail_container = document.getElementById("fail_msg")!;
        fail_container.style.display = "block";
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        fail_container.children[0].innerHTML += " (" + response_body + ").";
    }
}

function handle_report_error(
    handler_data: {base_url: string} | null,
    status_code: number | null,
    error_msg: string,
) {
    hide_report_processing_msg();

    const fail_container = document.getElementById("fail_msg")!;
    fail_container.style.display = "block";
    const message_element = fail_container.children[0];
    if (status_code) {
        message_element.append(` (HTTP: ${status_code}).`);
    } else if (error_msg) {
        message_element.append(` (${error_msg}).`);
    } else {
        const tt = document.createElement("tt");
        tt.textContent = handler_data!["base_url"];
        message_element.append(
            "(",
            tt,
            "is not reachable. Does your browser block XMLHttpRequest requests?).",
        );
    }
}

function hide_report_processing_msg() {
    const msg = document.getElementById("pending_msg")!;
    msg.parentNode?.removeChild(msg);
}

// Download function only for crash reports

export function download(data_url: string) {
    const link = document.createElement("a");
    link.download =
        "Check_MK_GUI_Crash-" + new Date().toISOString() + ".tar.gz";
    link.href = data_url;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
