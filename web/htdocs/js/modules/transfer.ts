// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as ajax from "ajax";

declare var XDomainRequest;
//# +--------------------------------------------------------------------+
//# | Posting crash report to official Checkmk crash reporting API      |
//# '--------------------------------------------------------------------'

export function submit_crash_report(url, post_data) {


    document.getElementById("pending_msg")!.style.display = "block";

    if (has_cross_domain_ajax_support()) {
        ajax.call_ajax(url, {
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
        handle_report_error(null, null, "Your browser does not support direct reporting.");
    }
}

export function submit_license_usage_report(url, authorization, post_data) {
    document.getElementById("pending_msg")!.style.display = "block";

    if (has_cross_domain_ajax_support()) {
        ajax.call_ajax(url, {
            method: "POST",
            post_data: post_data,
            response_handler: function (_unused_data, response_msg) {
                hide_report_processing_msg();

                var success_container = document.getElementById("success_msg")!;
                success_container.style.display = "block";
                (success_container.children[0] as HTMLElement).innerText += " " + response_msg;
            },
            error_handler: function (_unused_data, _unused_status, _unused_error, response_msg) {
                hide_report_processing_msg();

                var fail_container = document.getElementById("fail_msg")!;
                fail_container.style.display = "block";
                (fail_container.children[0] as HTMLElement).innerText += " (" + response_msg + ")";
            },
            add_ajax_id: false,
            handler_data: {
                base_url: url,
            },
            for_license_usage: true,
            authorization: authorization,
        });
    } else {
        handle_report_error(null, null, "Your browser does not support direct reporting.");
    }
}

function has_cross_domain_ajax_support() {
    return "withCredentials" in new XMLHttpRequest();
}

function submit_with_ie(url, post_data) {
    var handler_data = {
        base_url: url,
    };
    //not sure if this is the best solution
    //see for another solution: https://stackoverflow.com/questions/66120513/property-does-not-exist-on-type-window-typeof-globalthis
    var xdr = new (window as any).XDomainRequest();
    xdr.onload = function () {
        handle_report_response(handler_data, xdr.responseText);
    };
    xdr.onerror = function () {
        handle_report_error(handler_data, null, xdr.responseText);
    };
    xdr.onprogress = function () {
    };
    xdr.open("post", url);
    xdr.send(post_data);
}

function handle_report_response(handler_data, response_body) {
    hide_report_processing_msg();

    if (response_body.substr(0, 2) == "OK") {
        var id = response_body.split(" ")[1];
        var success_container = document.getElementById("success_msg")!;
        success_container.style.display = "block";
        success_container.innerHTML = success_container.innerHTML.replace(/###ID###/, id);
    } else {
        var fail_container = document.getElementById("fail_msg")!;
        fail_container.style.display = "block";
        fail_container.children[0].innerHTML += " (" + response_body + ").";
    }
}

function handle_report_error(handler_data, status_code, error_msg) {
    hide_report_processing_msg();

    var fail_container = document.getElementById("fail_msg")!;
    fail_container.style.display = "block";
    if (status_code) {
        fail_container.children[0].innerHTML += " (HTTP: " + status_code + ").";
    } else if (error_msg) {
        fail_container.children[0].innerHTML += " (" + error_msg + ").";
    } else {
        fail_container.children[0].innerHTML +=
            " (<tt>" +
            handler_data["base_url"] +
            "</tt> is not reachable. Does your browser block XMLHttpRequest requests?).";
    }
}

function hide_report_processing_msg() {
    var msg = document.getElementById("pending_msg")!;
    msg.parentNode?.removeChild(msg);
}

// Download function only for crash reports

export function download(data_url) {
    var link = document.createElement("a");
    link.download = "Check_MK_GUI_Crash-" + new Date().toISOString() + ".tar.gz";
    link.href = data_url;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
