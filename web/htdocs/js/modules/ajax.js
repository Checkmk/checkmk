// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails.  You should have received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import { merge_args } from "utils";

export function get_url(url, handler, data, errorHandler, addAjaxId)
{
    var args = {
        response_handler: handler
    };

    if (typeof data !== "undefined")
        args.handler_data = data;

    if (typeof errorHandler !== "undefined")
        args.error_handler = errorHandler;

    if (typeof addAjaxId !== "undefined")
        args.add_ajax_id = addAjaxId;

    call_ajax(url, args);
}

export function post_url(url, post_params, responseHandler, handler_data, errorHandler)
{
    var args = {
        method: "POST",
        post_data: post_params
    };

    if (typeof responseHandler !== "undefined") {
        args.response_handler = responseHandler;
    }

    if (typeof handler_data !== "undefined")
        args.handler_data = handler_data;

    if (typeof errorHandler !== "undefined")
        args.error_handler = errorHandler;

    call_ajax(url, args);
}

export function call_ajax(url, optional_args)
{
    var args = merge_args({
        add_ajax_id      : true,
        plain_error      : false,
        response_handler : null,
        error_handler    : null,
        handler_data     : null,
        method           : "GET",
        post_data        : null,
        sync             : false
    }, optional_args);

    var AJAX = window.XMLHttpRequest ? new window.XMLHttpRequest() : new window.ActiveXObject("Microsoft.XMLHTTP");
    if (!AJAX)
        return null;

    // Dynamic part to prevent caching
    if (args.add_ajax_id) {
        url += url.indexOf("?") !== -1 ? "&" : "?";
        url += "_ajaxid="+Math.floor(Date.parse(new Date()) / 1000);
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

    if (args.method == "POST") {
        AJAX.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    }

    if (!args.sync) {
        AJAX.onreadystatechange = function() {
            if (AJAX && AJAX.readyState == 4) {
                if (AJAX.status == 200) {
                    if (args.response_handler)
                        args.response_handler(args.handler_data, AJAX.responseText);
                }
                else if (AJAX.status == 401) {
                    // This is reached when someone is not authenticated anymore
                    // but has some webservices running which are still fetching
                    // infos via AJAX. Reload the whole frameset or only the
                    // single page in that case.
                    if(top)
                        top.location.reload();
                    else
                        document.location.reload();
                }
                else {
                    if (args.error_handler)
                        args.error_handler(args.handler_data, AJAX.status, AJAX.statusText);
                }
            }
        };
    }

    AJAX.send(args.post_data);
    return AJAX;
}
