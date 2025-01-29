/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";
import {persist_tree_state} from "./foldable_container";
import {add_class, has_class, remove_class, toggle_folding} from "./utils";

export function toggle_grouped_rows(
    tree: string,
    id: string,
    cell: HTMLTableCellElement,
    num_rows: number,
) {
    const group_title_row = cell.parentNode as HTMLElement;

    let display, toggle_img_open;
    let state: "on" | "off";
    if (has_class(group_title_row, "closed")) {
        remove_class(group_title_row, "closed");
        display = "";
        toggle_img_open = true;
        state = "on";
    } else {
        add_class(group_title_row, "closed");
        display = "none";
        toggle_img_open = false;
        state = "off";
    }

    toggle_folding(
        cell.getElementsByTagName("IMG")[0] as HTMLImageElement,
        toggle_img_open,
    );
    persist_tree_state(tree, id, state);

    let row = group_title_row;
    for (let i = 0; i < num_rows; i++) {
        row = row.nextElementSibling as HTMLElement;
        row.style.display = display;
    }
}

export function reschedule_check(
    oLink: HTMLElement,
    site: any,
    host: any,
    service: string,
    wait_svc: string,
) {
    const img = oLink.getElementsByTagName("IMG")[0] as HTMLImageElement;
    remove_class(img, "reload_failed");
    add_class(img, "reloading");

    const post_data =
        "request=" +
        encodeURIComponent(
            JSON.stringify({
                site: site,
                host: host,
                service: service,
                wait_svc: wait_svc,
            }),
        );

    call_ajax("ajax_reschedule.py", {
        method: "POST",
        post_data: post_data,
        response_handler: reschedule_check_response_handler,
        handler_data: {
            img: img,
        },
    });
}

function reschedule_check_response_handler(
    handler_data: {img: HTMLImageElement},
    ajax_response: string,
) {
    const img = handler_data.img;
    remove_class(img, "reloading");

    const response = JSON.parse(ajax_response);
    if (response.result_code != 0) {
        add_class(img, "reload_failed");
        img.title = "Error [" + response.result_code + "]: " + response.result; // eslint-disable-line
        return;
    }

    if (response.result.state === "OK") {
        window.location.reload();
    } else if (response.result.state === "TIMEOUT") {
        add_class(img, "reload_failed");
        img.title =
            "Timeout while performing action: " + response.result.message;
    } else {
        add_class(img, "reload_failed");
        img.title = response.result.message;
    }
}

export function add_to_visual(
    visual_type: string,
    visual_name: string,
    source_type: string,
    context: Record<string, any>,
) {
    const target_visual = document.getElementById(
        "select2-_add_to_" + visual_type + "-container",
    );

    if (!target_visual) {
        console.error("Missing target visual");
        return;
    }

    const target_title = target_visual.title;

    if (!target_title) {
        console.error("Missing target visual title (empty selection)");
        return;
    }

    const target_parts = target_title.split("(").pop();
    const target_id = target_parts!.slice(0, -1);

    const create_info = {
        context: context,
        params: {name: visual_name},
    };
    const create_info_json = JSON.stringify(create_info);

    const url =
        "ajax_add_visual.py" +
        "?visual_type=" +
        visual_type +
        "s" +
        "&visual_name=" +
        // Select2 only transports the title so we have to get the ID
        // from it. target_visual is e.g. "AWS EC2 instances
        // (aws_ec2_overview)"
        target_id +
        "&type=" +
        source_type;

    call_ajax(url, {
        method: "POST",
        post_data: "create_info=" + encodeURIComponent(create_info_json),
        plain_error: true,
        response_handler: function (_handler_data: any, response_body: string) {
            // After adding a dashlet, go to the choosen dashboard
            if (response_body.substr(0, 2) == "OK") {
                window.location.href = response_body.substr(3);
            } else {
                console.error("Failed to add element: " + response_body);
            }
        },
    });
}
