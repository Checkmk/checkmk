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
import * as hover from "hover";

export function show_hover_graphs(event, site_id, host_name, service_description)
{
    event = event || window.event;

    hover.show(event, "<div class=\"message\">Loading...</div>");

    show_check_mk_hover_graphs(site_id, host_name, service_description);
    return utils.prevent_default_events(event);
}

function show_check_mk_hover_graphs(site_id, host_name, service)
{
    var url = "host_service_graph_popup.py?site="+encodeURIComponent(site_id)
                                        +"&host_name="+encodeURIComponent(host_name)
                                        +"&service="+encodeURIComponent(service);

    ajax.call_ajax(url, {
        response_handler : handle_check_mk_hover_graphs_response,
        error_handler    : handle_hover_graphs_error,
        method           : "GET"
    });
}

function handle_check_mk_hover_graphs_response(_unused, code)
{
    hover.update_content(code);
}

function handle_hover_graphs_error(_unused, status_code)
{
    var code = "<div class=error>Update failed (" + status_code + ")</div>";
    hover.update_content(code);
}
