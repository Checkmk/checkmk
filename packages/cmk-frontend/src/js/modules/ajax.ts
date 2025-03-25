/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {PartialK} from "./types";

declare global {
    let global_csrf_token: string;
}

type OptionalArgs<HandlerData = any> = PartialK<
    Args<HandlerData>,
    | "method"
    | "post_data"
    | "handler_data"
    | "add_ajax_id"
    | "plain_error"
    | "sync"
>;

interface Args<HandlerData = any> {
    method: "GET" | "POST";
    post_data: string | null;
    response_handler?: (a: HandlerData, b: string) => void;
    handler_data: HandlerData | null;
    error_handler?: (
        handler_data: HandlerData,
        status: number,
        status_text: string,
        response_text?: string,
    ) => void;
    add_ajax_id: boolean;
    plain_error: boolean;
    sync: boolean;
    authorization?: string;
}

export function call_ajax<HandlerData = any>(
    url: string,
    optional_args?: OptionalArgs<HandlerData>,
) {
    const default_args: Args<HandlerData> = {
        add_ajax_id: true,
        plain_error: false,
        response_handler: undefined,
        error_handler: undefined,
        handler_data: null,
        method: "GET",
        post_data: null,
        sync: false,
        authorization: undefined,
    };
    const args: Args<HandlerData> = {
        ...default_args,
        ...optional_args,
    };

    const AJAX = new window.XMLHttpRequest();
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
            if (typeof e === "string")
                args.error_handler(args.handler_data!, 0, e);
            else if (e instanceof Error)
                args.error_handler(args.handler_data!, 0, e.message);
            else throw new Error("There is an error while using AJAX.open()");
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
        AJAX.setRequestHeader(
            "Content-type",
            "application/x-www-form-urlencoded",
        );
    }

    if (!args.sync) {
        AJAX.onreadystatechange = function () {
            if (AJAX && AJAX.readyState == 4) {
                if (AJAX.status == 200) {
                    if (args.response_handler)
                        args.response_handler(
                            args.handler_data!,
                            AJAX.responseText,
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
                            args.handler_data!,
                            AJAX.status,
                            AJAX.statusText,
                            AJAX.responseText,
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
        !args.post_data.includes("&_csrf_token=") &&
        !args.post_data.startsWith("_csrf_token=")
    ) {
        args.post_data +=
            "&_csrf_token=" + encodeURIComponent(global_csrf_token);
    }

    AJAX.send(args.post_data);
    return AJAX;
}
