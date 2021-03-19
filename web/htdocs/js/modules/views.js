// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";
import * as foldable_container from "foldable_container";

export function toggle_grouped_rows(tree, id, cell, num_rows) {
    var group_title_row = cell.parentNode;

    var display, toggle_img_open, state;
    if (utils.has_class(group_title_row, "closed")) {
        utils.remove_class(group_title_row, "closed");
        display = "";
        toggle_img_open = true;
        state = "on";
    } else {
        utils.add_class(group_title_row, "closed");
        display = "none";
        toggle_img_open = false;
        state = "off";
    }

    utils.toggle_folding(cell.getElementsByTagName("IMG")[0], toggle_img_open);
    foldable_container.persist_tree_state(tree, id, state);

    var row = group_title_row;
    for (var i = 0; i < num_rows; i++) {
        row = row.nextElementSibling;
        row.style.display = display;
    }
}

export function reschedule_check(oLink, site, host, service, wait_svc) {
    var img = oLink.getElementsByTagName("IMG")[0];
    utils.remove_class(img, "reload_failed");
    utils.add_class(img, "reloading");

    var post_data =
        "request=" +
        encodeURIComponent(
            JSON.stringify({
                site: site,
                host: host,
                service: service,
                wait_svc: wait_svc,
            })
        );

    ajax.call_ajax("ajax_reschedule.py", {
        method: "POST",
        post_data: post_data,
        response_handler: reschedule_check_response_handler,
        handler_data: {
            img: img,
        },
    });
}

function reschedule_check_response_handler(handler_data, ajax_response) {
    var img = handler_data.img;
    utils.remove_class(img, "reloading");

    var response = JSON.parse(ajax_response);
    if (response.result_code != 0) {
        utils.add_class(img, "reload_failed");
        img.title = "Error [" + response.result_code + "]: " + response.result; // eslint-disable-line
        return;
    }

    if (response.result.state === "OK") {
        window.location.reload();
    } else if (response.result.state === "TIMEOUT") {
        utils.add_class(img, "reload_failed");
        img.title = "Timeout while performing action: " + response.result.message;
    } else {
        utils.add_class(img, "reload_failed");
        img.title = response.result.message;
    }
}
