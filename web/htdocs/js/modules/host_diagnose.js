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

import * as utils from "utils";
import * as ajax from "ajax";

export function start_test(ident, hostname, request_vars, transid) {
    var log   = document.getElementById(ident + "_log");
    var img   = document.getElementById(ident + "_img");
    var retry = document.getElementById(ident + "_retry");

    retry.style.display = "none";

    let params = [
        "host=" + encodeURIComponent(hostname),
        "_transid=" + encodeURIComponent(transid),
        "_test=" + encodeURIComponent(ident)
    ];

    for (let i = 0; i < request_vars.length; i++) {
        params.push(encodeURIComponent(request_vars[i][0]) + "=" + encodeURIComponent(request_vars[i][1]));
    }

    img.src = img.src.replace(/(.*\/icon_).*(\.png$)/i, "$1reload$2");
    utils.add_class(img, "reloading");

    log.innerHTML = "...";
    ajax.get_url("wato_ajax_diag_host.py?" + params.join("&"),
        handle_host_diag_result, { "hostname": hostname, "ident": ident, "request_vars": request_vars }); // eslint-disable-line indent
}

function handle_host_diag_result(data, response_json) {
    var response = JSON.parse(response_json);

    var img   = document.getElementById(data.ident + "_img");
    var log   = document.getElementById(data.ident + "_log");
    var retry = document.getElementById(data.ident + "_retry");
    utils.remove_class(img, "reloading");

    var text = "";
    var new_icon = "";
    if (response.result_code == 1) {
        new_icon = "failed";
        log.className = "log diag_failed";
        text = "API Error:" + response.result;

    } else {
        if (response.result.status_code == 1) {
            new_icon = "failed";
            log.className = "log diag_failed";
        } else {
            new_icon = "success";
            log.className = "log diag_success";
        }
        text = response.result.output;
    }

    img.src = img.src.replace(/(.*\/icon_).*(\.png$)/i, "$1"+new_icon+"$2");
    log.innerText = text;

    retry.src = retry.src.replace(/(.*\/icon_).*(\.png$)/i, "$1reload$2");
    retry.style.display = "inline";
    retry.parentNode.href = "javascript:cmk.host_diagnose.start_test('"+data.ident+"', '"+data.hostname+"', "+JSON.stringify(data.request_vars)+", '"+response.result.next_transid+"');";
}
