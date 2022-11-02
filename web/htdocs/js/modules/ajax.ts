// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

declare global {
    var global_csrf_token: string;
}

interface Args {
    method: "GET" | "POST";
    post_data?;
    response_handler?: (a?, b?) => void;
    handler_data?;
    error_handler?: (a?, b?, c?) => void;
    add_ajax_id?: boolean;
}

export function call_ajax(url, optional_args?) {
    const default_args = {
        add_ajax_id: true,
        plain_error: false,
        response_handler: null,
        error_handler: null,
        handler_data: null,
        method: "GET",
        post_data: null,
        sync: false,
        for_license_usage: false,
        authorization: null,
    };
    var args = {
        ...default_args,
        ...optional_args,
    };

    var AJAX = window.XMLHttpRequest
        ? new window.XMLHttpRequest()
        : new window.ActiveXObject("Microsoft.XMLHTTP");
    if (!AJAX) return null;

    // Dynamic part to prevent caching
    if (args.add_ajax_id) {
        url += url.indexOf("?") !== -1 ? "&" : "?";
        url += "_ajaxid=" + Math.floor(new Date().getDate() / 1000);
    }

    if (args.plain_error) {
        url += url.indexOf("?") !== -1 ? "&" : "?";
        url += "_plain_error=1";
    }

    try {
        AJAX.open(args.method, url, !args.sync);
    } catch (e) {
        if (args.error_handler) {
            args.error_handler(args.handler_data, null, e);
            return null;
        } else {
            throw e;
        }
    }

    if (args.authorization) {
        // args.authorization contains base64 encoded 'username:password'
        AJAX.setRequestHeader("Authorization", "Basic " + args.authorization);
    }

    if (args.method == "POST") {
        if (args.for_license_usage) {
            AJAX.setRequestHeader("Content-type", "application/json");
        } else {
            AJAX.setRequestHeader(
                "Content-type",
                "application/x-www-form-urlencoded"
            );
        }
    }

    if (!args.sync) {
        AJAX.onreadystatechange = function () {
            if (AJAX && AJAX.readyState == 4) {
                if (AJAX.status == 200) {
                    if (args.response_handler)
                        args.response_handler(
                            args.handler_data,
                            AJAX.responseText
                        );
                } else if (AJAX.status == 401) {
                    // This is reached when someone is not authenticated anymore
                    // but has some webservices running which are still fetching
                    // infos via AJAX. Reload the whole page in that case.
                    if (top) {
                        top.location.reload();
                    } else {
                        document.location.reload();
                    }
                } else {
                    if (args.error_handler)
                        args.error_handler(
                            args.handler_data,
                            AJAX.status,
                            AJAX.statusText,
                            AJAX.responseText
                        );
                }
            }
        };
    }
    if (args.method == "POST" && args.post_data == null) {
        args.post_data = "";
    }
    if (
        typeof args.post_data == "string" &&
        !args.post_data.includes("&csrf_token=") &&
        !args.post_data.startsWith("csrf_token=") &&
        !args.for_license_usage
    ) {
        args.post_data +=
            "&csrf_token=" + encodeURIComponent(global_csrf_token);
    }

    AJAX.send(args.post_data);
    return AJAX;
}
