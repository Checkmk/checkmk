// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";
import * as hover from "hover";

export function show_hover_graphs(
    event_,
    site_id,
    host_name,
    service_description
) {
    event_ = event_ || window.event;

    hover.show(event_, '<div class="message">Loading...</div>');

    show_check_mk_hover_graphs(site_id, host_name, service_description, event_);
    return utils.prevent_default_events(event_);
}

function show_check_mk_hover_graphs(site_id, host_name, service, event_) {
    var url =
        "host_service_graph_popup.py?site=" +
        encodeURIComponent(site_id) +
        "&host_name=" +
        encodeURIComponent(host_name) +
        "&service=" +
        encodeURIComponent(service);

    ajax.call_ajax(url, {
        response_handler: handle_check_mk_hover_graphs_response,
        handler_data: {event_: event_},
        error_handler: handle_hover_graphs_error,
        method: "GET",
    });
}

function handle_check_mk_hover_graphs_response(handler_data, code) {
    hover.update_content(code, handler_data.event_);
}

function handle_hover_graphs_error(handler_data, status_code) {
    var code = "<div class=error>Update failed (" + status_code + ")</div>";
    hover.update_content(code, handler_data.event_);
}
