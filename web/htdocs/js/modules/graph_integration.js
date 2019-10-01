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
import * as popup_menu from "popup_menu";

export function render_graphs(container, site, host, service, pnpview, base_url, pnp_url, with_link, add_txt, from_ts, to_ts, pnp_theme)
{
    from_ts = (typeof from_ts === "undefined") ? null : from_ts;
    to_ts   = (typeof to_ts === "undefined") ? null : to_ts;

    var data = {
        "container": container, "base_url": base_url,
        "pnp_url":   pnp_url,   "site":     site,
        "host":      host,      "service":  service,
        "with_link": with_link, "view":     pnpview,
        "add_txt":   add_txt,   "theme":    pnp_theme
    };

    if (from_ts !== null && to_ts !== null) {
        data["start"] = from_ts;
        data["end"] = to_ts;
    }

    var url = pnp_url + "index.php/json?&host=" + encodeURIComponent(host)
              + "&srv=" + encodeURIComponent(service) + "&source=0&view=" + pnpview;
    ajax.get_url(url, pnp_response_handler, data, pnp_error_response_handler, false);
}

function pnp_response_handler(data, code) {
    var valid_response = true;
    var response = [];
    try {
        response = eval(code);
        for(var i = 0; i < response.length; i++) {
            var view = data["view"] == "" ? "0" : data["view"];
            create_pnp_graph(data, "&" + response[i]["image_url"].replace("#", "%23").replace("&view="+view, ""));
        }
    } catch(e) {
        valid_response = false;
    }

    if(!valid_response) {
        if (code.match(/_login/)) {
            // Login failed! This usually happens when one uses a distributed
            // multisite setup but the transparent authentication is somehow
            // broken. Display an error message trying to assist.
            var container = document.getElementById(data["container"]);
            container.innerHTML = "<div class=\"error\">Unable to fetch graphs of the host. Maybe you have a "
                                + "distributed setup and not set up the authentication correctly yet.</div>";
        } else {
            fallback_graphs(data);
        }
    }
}

function pnp_error_response_handler(data, status_code) {
    // PNP versions that do not have the JSON webservice respond with
    // 404. Current version with the webservice answer 500 if the service
    // in question does not have any PNP graphs. So we paint the fallback
    // graphs only if the respone code is 404 (not found).
    if (parseInt(status_code) == 404)
        fallback_graphs(data);
}

// Fallback bei doofer/keiner Antwort
function fallback_graphs(data) {
    for(var s = 0; s < 8; s++) {
        create_pnp_graph(data, "&host=" + data["host"] + "&srv=" + data["service"] + "&source=" + s);
    }
}

function create_pnp_graph(data, params) {
    var urlvars = params + "&theme="+data["theme"]+"&baseurl="+data["base_url"];

    if (typeof(data["start"]) !== "undefined" && typeof(data["end"]) !== "undefined")
        urlvars += "&start="+data["start"]+"&end="+data["end"];

    var container = document.getElementById(data["container"]);

    var img = document.createElement("img");
    img.src = data["pnp_url"] + "index.php/image?view=" + data["view"] + urlvars;

    if (data.with_link) {
        var graph_container = document.createElement("div");
        graph_container.setAttribute("class", "pnp_graph");

        var view   = data["view"] == "" ? 0 : data["view"];
        // needs to be extracted from "params", hack!
        var source = parseInt(utils.get_url_param("source", params)) + 1;

        // Add the control for adding the graph to a visual
        var visualadd = document.createElement("a");
        visualadd.title = data["add_txt"];
        visualadd.className = "popup_trigger";
        visualadd.onclick = function(host, service, view, source) {
            return function(event) {
                popup_menu.toggle_popup(event, this, "add_visual", "add_visual",
                    [
                        "pnpgraph",
                        { "host": host, "service": service },
                        { "timerange": view, "source": source }
                    ],
                    "add_type=pnpgraph",
                    null,
                    false
                );
            };
        }(data["host"], data["service"], view, source);

        graph_container.appendChild(visualadd);

        var link = document.createElement("a");
        link.href = data["pnp_url"] + "index.php/graph?" + urlvars;
        link.appendChild(img);
        graph_container.appendChild(link);

        container.appendChild(graph_container);
    }
    else {
        container.appendChild(img);
    }

    img = null;
    link = null;
    container = null;
    urlvars = null;
}

export function show_hover_graphs(event, site_id, host_name, service_description, pnp_popup_url, force_pnp_graphing)
{
    event = event || window.event;

    hover.show(event, "<div class=\"message\">Loading...</div>");

    if (force_pnp_graphing)
        show_pnp_hover_graphs(pnp_popup_url);
    else
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

function show_pnp_hover_graphs(url)
{
    ajax.call_ajax(url, {
        response_handler : handle_pnp_hover_graphs_response,
        error_handler    : handle_hover_graphs_error,
        method           : "GET"
    });
}

function handle_check_mk_hover_graphs_response(_unused, code)
{
    if (code.indexOf("pnp4nagios") !== -1) {
        // fallback to pnp graph handling (received an URL with the previous ajax call)
        show_pnp_hover_graphs(code);
        return;
    }

    hover.update_content(code);
}


function handle_pnp_hover_graphs_response(_unused, code)
{
    // In case of PNP hover graph handling:
    // It is possible that, if using multisite based authentication, pnp sends a 302 redirect
    // to the login page which is transparently followed by XmlHttpRequest. There is no chance
    // to catch the redirect. So we try to check the response content. If it does not contain
    // the expected code, simply display an error message.
    if (code.indexOf("/image?") === -1) {
        // Error! unexpected response
        code = "<div class=\"error\"> "
             + "ERROR: Received an unexpected response "
             + "while trying to display the PNP Graphs. Maybe there is a problem with the "
             + "authentication.</div>";
    }

    hover.update_content(code);
}


function handle_hover_graphs_error(_unused, status_code)
{
    var code = "<div class=error>Update failed (" + status_code + ")</div>";
    hover.update_content(code);
}
