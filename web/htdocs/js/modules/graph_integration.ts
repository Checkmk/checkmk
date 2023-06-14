// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as ajax from "ajax";
import * as hover from "hover";
import * as utils from "utils";

export function show_hover_graphs(
    event_: MouseEvent,
    site_id: string,
    host_name: string,
    service_description: string
) {
    hover.show(event_, '<div class="message">Loading...</div>');

    show_check_mk_hover_graphs(site_id, host_name, service_description, event_);
    return utils.prevent_default_events(event_);
}

function show_check_mk_hover_graphs(
    site_id: string,
    host_name: string,
    service: string,
    event_: MouseEvent
) {
    const url =
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

function handle_check_mk_hover_graphs_response(
    handler_data: {event_: MouseEvent},
    code: string
) {
    hover.update_content(code, handler_data.event_);
}

function handle_hover_graphs_error(
    handler_data: {event_: MouseEvent},
    status_code: number
) {
    const code = "<div class=error>Update failed (" + status_code + ")</div>";
    hover.update_content(code, handler_data.event_);
}
