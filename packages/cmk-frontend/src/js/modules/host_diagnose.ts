/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";
import {add_class, remove_class} from "./utils";

export function start_test(ident: string, hostname: string, transid: string) {
    const log = document.getElementById(ident + "_log") as HTMLImageElement;
    const img = document.getElementById(ident + "_img") as HTMLImageElement;
    const retry = document.getElementById(ident + "_retry") as HTMLImageElement;

    retry!.style.display = "none";

    // Forward all valuespec fields; server-side Password handles typed-vs-_orig.
    const params = new URLSearchParams();
    params.append("host", hostname);
    params.append("_test", ident);
    params.append("_transid", transid);

    const form = document.getElementsByName("diag_host")[0] as
        | HTMLFormElement
        | undefined;
    if (!form) {
        throw new Error(
            "'diag_host' form not found; cannot run connection tests",
        );
    }
    for (const [name, value] of new FormData(form)) {
        if (typeof value !== "string") continue;
        if (!name.startsWith("vs_host_") && !name.startsWith("vs_rules_"))
            continue;
        params.append(name, value);
    }

    img.src = img.src.replace(/(.*\/icon_).*(\.svg$)/i, "$1reload$2");
    add_class(img, "reloading");

    log.innerHTML = "...";

    call_ajax("wato_ajax_diag_host.py", {
        method: "POST",
        response_handler: handle_host_diag_result,
        handler_data: {hostname: hostname, ident: ident},
        post_data: params.toString(),
    });
}

function handle_host_diag_result(
    data: {hostname: string; ident: string},
    response_json: string,
) {
    const response = JSON.parse(response_json);

    const img = document.getElementById(
        data.ident + "_img",
    ) as HTMLImageElement;
    const log = document.getElementById(
        data.ident + "_log",
    ) as HTMLImageElement;
    const retry = document.getElementById(
        data.ident + "_retry",
    ) as HTMLImageElement;
    remove_class(img, "reloading");

    let text = "";
    let new_icon = "";
    if (response.result_code == 1) {
        new_icon = "cancel";
        log.className = "log diag_failed";
        text = "API Error:" + response.result;
    } else {
        if (response.result.status_code == 1) {
            new_icon = "cancel";
            log.className = "log diag_failed";
        } else {
            new_icon = "accept";
            log.className = "log diag_success";
        }
        text = response.result.output;
    }

    img.src = img.src.replace(/(.*\/icon_).*(\.svg$)/i, "$1" + new_icon + "$2");
    log.innerText = text;

    retry.src = retry.src.replace(/(.*\/icon_).*(\.svg$)/i, "$1reload$2");
    retry.style.display = "inline";
    (retry.parentNode as HTMLAnchorElement).href =
        `javascript:cmk.host_diagnose.start_test("${data.ident}", "${data.hostname}", "${response.result.next_transid}");`;
}
