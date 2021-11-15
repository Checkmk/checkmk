// Copyright (C) 2019 tribe29 GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";
import * as hover from "hover";
import * as reload_pause from "reload_pause";

// Styling. Please note that for each visible pixel our canvas
// has two pixels. This improves the resolution when zooming
// in with your browser.
const v_label_margin = 10; // pixels between vertical label and v axis
const t_label_margin = 10; // pixels between time label and t axis
const axis_over_width = 5; // pixel that the axis is longer for optical reasons
const color_gradient = 0.2; // ranges from 0 to 1
const curve_line_width = 2.0;
const rule_line_width = 2.0;
const g_page_update_delay = 60; // prevent page update for X seconds
const g_delayed_graphs = [];

// Global graph constructs to store the graphs etc.
const g_graphs = {};
var g_current_graph_id = 0;

//#   .-Creation-----------------------------------------------------------.
//#   |              ____                _   _                             |
//#   |             / ___|_ __ ___  __ _| |_(_) ___  _ __                  |
//#   |            | |   | '__/ _ \/ _` | __| |/ _ \| '_ \                 |
//#   |            | |___| | |  __/ (_| | |_| | (_) | | | |                |
//#   |             \____|_|  \___|\__,_|\__|_|\___/|_| |_|                |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | Graphs are created by a javascript function. The unique graph id   |
//#   | is create solely by the javascript code. This function is being    |
//#   | called by web/plugins/graphs.py:render_graphs_htmls()              |
//#   '--------------------------------------------------------------------'

function get_id_of_graph(ajax_context) {
    // Return the graph_id for and eventual existing graph
    for (var graph_id in g_graphs) {
        // JSON.stringify seems to be the easiest way to compare the both dicts
        if (
            JSON.stringify(ajax_context.definition.specification) ==
                JSON.stringify(g_graphs[graph_id].ajax_context.definition.specification) &&
            JSON.stringify(ajax_context.render_options) ==
                JSON.stringify(g_graphs[graph_id].ajax_context.render_options)
        ) {
            return graph_id;
        }
    }

    // Otherwise create a new graph
    return "graph_" + g_current_graph_id++;
}

export function create_graph(html_code, graph_artwork, graph_render_options, ajax_context) {
    // Detect whether or not a new graph_id has to be calculated. During the view
    // data reload create_graph() is called again for all already existing graphs.
    // In this situation the graph_id needs to be detected and reused instead of
    // calculating a new one. Otherwise e.g. g_graphs will grow continously.
    var graph_id = get_id_of_graph(ajax_context);

    // create container div that contains the graph.
    var container_div = document.createElement("div");
    container_div.setAttribute("id", graph_id);
    container_div.innerHTML = html_code;
    if (graph_render_options.show_timeranges)
        container_div.className = "graph_container timeranges";
    else container_div.className = "graph_container";

    var embedded_script = get_current_script();

    // Insert the new container right after the script tag
    embedded_script.parentNode.insertBefore(container_div, embedded_script.nextSibling);

    // Now register and paint the graph
    ajax_context["graph_id"] = graph_id;
    g_graphs[graph_id] = graph_artwork;
    g_graphs[graph_id]["ajax_context"] = ajax_context;
    g_graphs[graph_id]["render_options"] = graph_render_options;
    g_graphs[graph_id]["id"] = graph_id;
    render_graph(g_graphs[graph_id]);
}

// determine DOM node of the <javascript> that called us. It's
// parent will get the graph node attached.
function get_current_script() {
    var embedded_script = utils.current_script;
    if (embedded_script) return embedded_script;

    // The function fixes IE compatibility issues
    return (
        document.currentScript ||
        (function () {
            // eslint-disable-line
            var scripts = document.getElementsByTagName("script");
            return scripts[scripts.length - 1];
        })()
    );
}

// Is called from the HTML code rendered with python. It contacts
// the python code again via an AJAX call to get the rendered graph.
//
// This is done for the following reasons:
//
// a) Start rendering and updating a graph in the moment it gets visible to the
//    user for the first time.
// b) Process the rendering asynchronous via javascript to make the page loading
//    faster by parallelizing the graph loading processes.
export function load_graph_content(graph_recipe, graph_data_range, graph_render_options) {
    var script_object = get_current_script();

    // In case the graph load container (-> is at future graph location) is not
    // visible to the user delay processing of this function
    var graph_load_container = script_object.previousSibling;
    if (!utils.is_in_viewport(graph_load_container)) {
        g_delayed_graphs.push({
            graph_load_container: graph_load_container,
            graph_recipe: graph_recipe,
            graph_data_range: graph_data_range,
            graph_render_options: graph_render_options,
            script_object: script_object,
        });
        return;
    } else {
        do_load_graph_content(graph_recipe, graph_data_range, graph_render_options, script_object);
    }
}

export function register_delayed_graph_listener() {
    var num_delayed = g_delayed_graphs.length;
    if (num_delayed == 0) return; // no delayed graphs: Nothing to do

    // Start of delayed graph renderer listening
    utils.content_scrollbar().getScrollElement().addEventListener("scroll", delayed_graph_renderer);
    utils.add_event_handler("resize", delayed_graph_renderer);
}

function do_load_graph_content(
    graph_recipe,
    graph_data_range,
    graph_render_options,
    script_object
) {
    var graph_load_container = script_object.previousSibling;
    update_graph_load_container(
        graph_load_container,
        "Loading graph...",
        '<img class="loading" src="themes/facelift/images/load_graph.png">'
    );

    var post_data =
        "request=" +
        encodeURIComponent(
            JSON.stringify({
                graph_recipe: graph_recipe,
                graph_data_range: graph_data_range,
                graph_render_options: graph_render_options,
            })
        );

    ajax.call_ajax("ajax_render_graph_content.py", {
        method: "POST",
        post_data: post_data,
        response_handler: handle_load_graph_content,
        error_handler: handle_load_graph_content_error,
        handler_data: script_object,
    });
}

function handle_load_graph_content(script_object, ajax_response) {
    var response = JSON.parse(ajax_response);

    if (response.result_code != 0) {
        handle_load_graph_content_error(script_object, response.result_code, response.result);
        return;
    }

    // Create a temporary div node to load the response into the DOM.
    // Then get the just loaded graph objects from the temporary div and
    // add replace the placeholder with it.
    var tmp_div = document.createElement("div");
    tmp_div.innerHTML = response.result;

    script_object.parentNode.replaceChild(tmp_div, script_object.previousSibling);
    script_object.parentNode.removeChild(script_object);
    utils.execute_javascript_by_object(tmp_div);
}

function handle_load_graph_content_error(script_object, status_code, error_msg) {
    var msg = "Loading graph failed: (Status: " + status_code + ")<br><br>" + error_msg;

    var graph_load_container = script_object.previousSibling;
    update_graph_load_container(graph_load_container, "ERROR", "<pre>" + msg + "</pre>");
}

function update_graph_load_container(container, title, content_html) {
    container.getElementsByClassName("title")[0].innerText = title;
    container.getElementsByClassName("content")[0].innerHTML = content_html;
}

// Is executed on scroll / resize events in case at least one graph is
// using the delayed graph rendering mechanism
function delayed_graph_renderer() {
    var num_delayed = g_delayed_graphs.length;
    if (num_delayed == 0) return; // no delayed graphs: Nothing to do

    var i = num_delayed;
    while (i--) {
        var entry = g_delayed_graphs[i];
        if (utils.is_in_viewport(entry.graph_load_container)) {
            do_load_graph_content(
                entry.graph_recipe,
                entry.graph_data_range,
                entry.graph_render_options,
                entry.script_object
            );
            g_delayed_graphs.splice(i, 1);
        }
    }
    return true;
}

function update_delayed_graphs_timerange(start_time, end_time) {
    for (var i = 0, len = g_delayed_graphs.length; i < len; i++) {
        var entry = g_delayed_graphs[i];
        entry.graph_data_range.time_range = [start_time, end_time];
    }
}

//#.
//#   .-Painting-------------------------------------------------------------.
//#   |                ____       _       _   _                              |
//#   |               |  _ \ __ _(_)_ __ | |_(_)_ __   __ _                  |
//#   |               | |_) / _` | | '_ \| __| | '_ \ / _` |                 |
//#   |               |  __/ (_| | | | | | |_| | | | | (_| |                 |
//#   |               |_|   \__,_|_|_| |_|\__|_|_| |_|\__, |                 |
//#   |                                               |___/                  |
//#   +----------------------------------------------------------------------+
//#   |  Paint the graph into the canvas object.                             |
//#   '----------------------------------------------------------------------'

// Keep draw contex as global variable for conveniance
var ctx = null;

// Notes:
// - In JS canvas 0,0 is at top left
// - We paint as few padding as possible. Additional padding is being
//   added via CSS
// NOTE: If you change something here, then please check if you also need to
// adapt the Python code that creates that graph_artwork
function render_graph(graph) {
    // First find the canvas object and add a reference to the graph dict
    // If the initial rendering failed then any later update does not
    // make any sense.
    var container = document.getElementById(graph["id"]);
    if (!container) return;

    var canvas = container.childNodes[0].getElementsByTagName("canvas")[0];
    if (!canvas) return;

    update_graph_styling(graph, container);

    graph["canvas_obj"] = canvas;

    ctx = canvas.getContext("2d"); // Create one ctx for all operations

    var font_size = from_display_coord(graph.render_options.font_size);
    ctx.font = font_size + "pt sans-serif";

    var width = canvas.width;
    var height = canvas.height;

    var bottom_border = graph_bottom_border(graph);
    var top_border = 0;
    if (bottom_border > 0) top_border = (bottom_border - t_label_margin) / 2;

    var v_axis_width = graph_vertical_axis_width(graph);

    var v_line_color = [graph.render_options.foreground_color, "#8097b19c", "#8097b19c"];

    // Prepare position and translation of origin
    var t_range_from = graph["time_axis"]["range"][0];
    var t_range_to = graph["time_axis"]["range"][1];
    var t_range = t_range_to - t_range_from;
    var t_pixels = width - v_axis_width;
    var t_pixels_per_second = t_pixels / t_range;
    graph["time_axis"]["pixels_per_second"] = t_pixels_per_second; // store for dragging

    var v_range_from = graph["vertical_axis"]["range"][0];
    var v_range_to = graph["vertical_axis"]["range"][1];
    var v_range = v_range_to - v_range_from;
    var v_pixels = height - bottom_border - top_border;
    var v_pixels_per_unit = v_pixels / v_range;
    graph["vertical_axis"]["pixels_per_unit"] = v_pixels_per_unit; // store for dragging

    var t_orig = v_axis_width;
    graph["time_origin"] = t_orig; // for dragging

    var v_orig = height - bottom_border;
    graph["vertical_origin"] = v_orig; // for dragging

    var v_axis_orig = v_range_from;

    // Now transform the whole coordinate system to our real t and v coords
    // so if we paint something at (0, 0) it will correctly represent a
    // value of 0 and a time point of time_start.
    var trans_t = function (t) {
        return (t - t_range_from) * t_pixels_per_second + t_orig;
    };
    var trans_v = function (v) {
        return v_orig - (v - v_axis_orig) * v_pixels_per_unit;
    };
    var trans = function (t, v) {
        return [trans_t(t), trans_v(v)];
    };

    var position, label;
    // render grid
    if (!graph.render_options.preview) {
        let line_width;

        // Paint the vertical axis
        let labels = graph["vertical_axis"]["labels"];
        ctx.save();
        ctx.textAlign = "end";
        ctx.textBaseline = "middle";
        ctx.fillStyle = graph.render_options.foreground_color;
        for (i = 0; i < labels.length; i++) {
            position = labels[i][0];
            label = labels[i][1];
            line_width = labels[i][2];
            if (line_width > 0) {
                paint_line(
                    trans(t_range_from, position),
                    trans(t_range_to, position),
                    v_line_color[line_width]
                );
            }

            if (graph.render_options.show_vertical_axis && label != null)
                ctx.fillText(label, t_orig - v_label_margin, trans(t_range_from, position)[1]);
        }
        ctx.restore();

        // Paint time axis
        labels = graph["time_axis"]["labels"];
        ctx.save();
        ctx.fillStyle = graph.render_options.foreground_color;
        for (i = 0; i < labels.length; i++) {
            position = labels[i][0];
            label = labels[i][1];
            line_width = labels[i][2];
            if (line_width > 0) {
                paint_line(
                    trans(position, v_range_from),
                    trans(position, v_range_to),
                    v_line_color[line_width]
                );
            }
        }
        ctx.restore();
    }

    // Paint curves
    var curves = graph["curves"];
    var step = graph["step"] / 2.0;
    var i, j, color, opacity;
    for (i = 0; i < curves.length; i++) {
        var t = graph["start_time"];
        var curve = curves[i];
        if (curve["dont_paint"]) continue;

        var points = curve["points"];
        // the hex color code can have additional opacity information
        // if these are none existing default to 0.3 UX project
        if (curve["color"].length == 9) {
            color = curve["color"].substr(0, 7);
            opacity = curve["color"].slice(-2);
        } else {
            color = curve["color"];
            opacity = "4c"; // that is 0.3
        }

        if (curve["type"] == "area") {
            var prev_lower = null;
            var prev_upper = null;
            ctx.save();
            ctx.fillStyle = hex_to_rgba(color + opacity);
            ctx.imageSmoothingEnabled = true; // seems no difference on FF

            for (j = 0; j < points.length; j++) {
                var point = points[j];
                var lower = point[0];
                var upper = point[1];
                if (lower != null && upper != null && prev_lower != null && prev_upper != null) {
                    ctx.beginPath();
                    ctx.moveTo(trans_t(t - step), trans_v(prev_lower));
                    ctx.lineTo(trans_t(t - step), trans_v(prev_upper));
                    ctx.lineTo(trans_t(t), trans_v(upper));
                    ctx.lineTo(trans_t(t), trans_v(lower));
                    ctx.closePath();
                    ctx.fill();

                    ctx.beginPath();
                    ctx.strokeStyle = color;
                    ctx.lineWidth = curve_line_width;
                    let mirrored = upper <= 0;
                    ctx.moveTo(trans_t(t - step), trans_v(mirrored ? prev_lower : prev_upper));
                    ctx.lineTo(trans_t(t), trans_v(mirrored ? lower : upper));
                    ctx.stroke();
                }
                prev_lower = lower;
                prev_upper = upper;
                t += step;
            }
            ctx.restore();
        } else {
            // "line"
            ctx.save();
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = curve_line_width;
            var last_value = null;
            for (j = 0; j < points.length; j++) {
                var value = points[j];
                if (value != null) {
                    var p = trans(t, value);
                    if (last_value != null) ctx.lineTo(p[0], p[1]);
                    else ctx.moveTo(p[0], p[1]);
                }
                last_value = value;
                t += step;
            }
            ctx.stroke();
            ctx.closePath();
            ctx.restore();
        }
    }

    if (!graph.render_options.preview && graph.render_options.show_time_axis) {
        // Paint time axis labels
        ctx.save();
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = graph.render_options.foreground_color;
        let labels = graph["time_axis"]["labels"];
        labels.forEach(([position, label, _]) => {
            if (label != null) ctx.fillText(label, trans(position, 0)[0], v_orig + t_label_margin);
        });
        ctx.restore();
    }

    // Paint horizontal rules like warn and crit
    ctx.save();
    ctx.lineWidth = rule_line_width;
    var rules = graph["horizontal_rules"];
    for (i = 0; i < rules.length; i++) {
        position = rules[i][0];
        label = rules[i][1];
        color = rules[i][2];
        if (position >= v_range_from && position <= v_range_to) {
            paint_line(trans(t_range_from, position), trans(t_range_to, position), color);
        }
    }
    ctx.restore();

    // paint the optional pin
    if (graph.render_options.show_pin && graph.pin_time != null) {
        var pin_x = trans_t(graph.pin_time);
        if (pin_x >= t_orig) {
            paint_line(
                [pin_x, v_orig + axis_over_width],
                [pin_x, 0],
                graph.render_options.foreground_color
            );
            paint_dot([pin_x, 0], graph.render_options.foreground_color);
        }
    }
    // paint forecast graph future start
    if (graph.definition.is_forecast) {
        let pin_x = trans_t(graph.requested_end_time);
        if (pin_x >= t_orig) {
            paint_line([pin_x, v_orig + axis_over_width], [pin_x, 0], "#00ff00");
        }
    }

    // Enable interactive mouse control of graph
    graph_activate_mouse_control(graph);
}

function hex_to_rgba(color) {
    // convert '#00112233' to 'rgba(0, 17, 34, 0.2)'
    // NOTE: When we drop IE11 support we don't need this conversion anymore.
    const parse = x => parseInt(color.substr(x, 2), 16);
    return `rgba(${parse(1)}, ${parse(3)}, ${parse(5)}, ${parse(7) / 255})`;
}

function graph_vertical_axis_width(graph) {
    if (graph.render_options.preview) return 0;

    if (!graph.render_options.show_vertical_axis && !graph.render_options.show_controls) return 0;

    if (
        graph.render_options.vertical_axis_width instanceof Array &&
        graph.render_options.vertical_axis_width[0] == "explicit"
    ) {
        return from_display_coord(pt_to_px(graph.render_options.vertical_axis_width[1]));
    }

    return 6 * from_display_coord(pt_to_px(graph.render_options.font_size));
}

function update_graph_styling(graph, container) {
    var graph_div = container.getElementsByClassName("graph")[0];
    if (!graph_div) return;
    graph_div.style.color = graph.render_options.foreground_color;

    var inverted_fg_color = render_color(
        invert_color(parse_color(graph.render_options.foreground_color))
    );

    var style = document.createElement("style");
    var rules = [
        {
            selector: "div.graph div.v_axis_label",
            attrs: {
                color: render_color_rgba(parse_color(graph.render_options.foreground_color), 0.8),
            },
        },
        {
            selector: "div.graph div.time",
            attrs: {
                color: render_color_rgba(parse_color(graph.render_options.foreground_color), 0.8),
            },
        },
        {
            selector:
                "div.graph table.legend th.scalar.inactive, div.graph table.legend td.scalar.inactive",
            attrs: {
                color: render_color_rgba(parse_color(graph.render_options.foreground_color), 0.6),
            },
        },
        {
            selector: "div.graph table.legend th",
            attrs: {
                "border-bottom": "1px solid " + graph.render_options.foreground_color,
            },
        },
        {
            selector: "div.graph table.legend th.scalar",
            attrs: {
                color: graph.render_options.foreground_color,
                "border-bottom": "1px solid " + graph.render_options.foreground_color,
            },
        },
        {
            selector: "div.graph a",
            attrs: {
                color: graph.render_options.foreground_color,
            },
        },
        {
            selector: "div.graph.preview .title",
            attrs: {
                "text-shadow":
                    "-1px 0 " +
                    inverted_fg_color +
                    ", 0 1px " +
                    inverted_fg_color +
                    ", 1px 0 " +
                    inverted_fg_color +
                    ", 0 -1px " +
                    inverted_fg_color,
            },
        },
        {
            selector: "div.graph div.title.inline, div.graph div.time.inline",
            attrs: {
                "text-shadow":
                    "-1px 0 " +
                    inverted_fg_color +
                    ", 0 1px " +
                    inverted_fg_color +
                    ", 1px 0 " +
                    inverted_fg_color +
                    ", 0 -1px " +
                    inverted_fg_color,
            },
        },
        {
            selector: "div.graph div.indicator",
            attrs: {
                "border-right": "1px dotted " + graph.render_options.foreground_color,
            },
        },
    ];

    var css_text = "";
    for (var i = 0, len = rules.length; i < len; i++) {
        var spec = rules[i];
        css_text += spec["selector"] + " {\n";
        for (var attr_name in spec["attrs"]) {
            css_text += attr_name + ": " + spec["attrs"][attr_name] + ";\n";
        }
        css_text += "}\n";
    }

    style.innerHTML = css_text;
    graph_div.appendChild(style);
}

function pt_to_px(size) {
    return (size / 72.0) * 96;
}

function to_display_coord(canvas_coord) {
    return canvas_coord / 2;
}

function from_display_coord(display_coord) {
    return display_coord * 2;
}

function graph_bottom_border(graph) {
    if (graph.render_options.preview) return 0;

    if (graph.render_options.show_time_axis)
        return from_display_coord(pt_to_px(graph.render_options.font_size)) + t_label_margin;
    else return 0;
}

function paint_line(p0, p1, color) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.moveTo(p0[0], p0[1]);
    ctx.lineTo(p1[0], p1[1]);
    ctx.stroke();
    ctx.closePath();
    ctx.restore();
}

function paint_rect(p, width, height, color) {
    ctx.save();
    ctx.fillStyle = color;
    ctx.fillRect(p[0], p[1], width, height);
    ctx.restore();
}

function paint_dot(p, color) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(p[0], p[1], 5, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.closePath();
    ctx.restore();
}

function parse_color(hexcolor) {
    var bits = parseInt(hexcolor.substr(1), 16);
    var r = ((bits >> 16) & 255) / 255.0;
    var g = ((bits >> 8) & 255) / 255.0;
    var b = (bits & 255) / 255.0;
    return [r, g, b];
}

function render_color(rgb) {
    var r = rgb[0];
    var g = rgb[1];
    var b = rgb[2];
    var bits = parseInt(b * 255) + 256 * parseInt(g * 255) + 65536 * parseInt(r * 255);
    var hex = bits.toString(16);
    while (hex.length < 6) hex = "0" + hex;
    return "#" + hex;
}

function render_color_rgba(rgb, a) {
    var r = rgb[0] * 255;
    var g = rgb[1] * 255;
    var b = rgb[2] * 255;
    return "rgba(" + r + ", " + g + ", " + b + ", " + a + ")";
}

function lighten_color(rgb, v) {
    var lighten = function (x, v) {
        return x + (1.0 - x) * v;
    };
    return [lighten(rgb[0], v), lighten(rgb[1], v), lighten(rgb[2], v)];
}

function darken_color(rgb, v) {
    var darken = function (x, v) {
        return x * (1.0 - v);
    };
    return [darken(rgb[0], v), darken(rgb[1], v), darken(rgb[2], v)];
}

function invert_color(rgb) {
    var invert = function (x) {
        return 1.0 - x;
    };
    return [invert(rgb[0]), invert(rgb[1]), invert(rgb[2])];
}

//#.
//#   .-Mouse Control--------------------------------------------------------.
//#   |   __  __                         ____            _             _     |
//#   |  |  \/  | ___  _   _ ___  ___   / ___|___  _ __ | |_ _ __ ___ | |    |
//#   |  | |\/| |/ _ \| | | / __|/ _ \ | |   / _ \| '_ \| __| '__/ _ \| |    |
//#   |  | |  | | (_) | |_| \__ \  __/ | |__| (_) | | | | |_| | | (_) | |    |
//#   |  |_|  |_|\___/ \__,_|___/\___|  \____\___/|_| |_|\__|_|  \___/|_|    |
//#   |                                                                      |
//#   +----------------------------------------------------------------------+
//#   |  Code for handling dragging and zooming via the scroll whell.        |
//#   '----------------------------------------------------------------------'

var g_dragging_graph = null;
var g_resizing_graph = null;

// Is set to True when one graph is started being updated via AJAX.
// It is set to False when the update has finished.
var g_graph_update_in_process = false;

// Is set to True when one graph is started being updated via AJAX. It is
// set to False after 100 ms to prevent too often graph rendering updates.
var g_graph_in_cooldown_period = false;

// Holds the timeout object which triggers an AJAX update of all other graphs
// on the page 500ms after the last mouse wheel zoom step.
var g_graph_wheel_timeout = null;

// Returns the graph container node. Can be called with any DOM node as
// parameter which is part of a graph
function get_graph_container(obj) {
    while (obj && !utils.has_class(obj, "graph_container")) obj = obj.parentNode;
    return obj;
}

function get_main_graph_container(obj) {
    while (obj && !utils.has_class(obj, "graph_with_timeranges")) obj = obj.parentNode;
    return obj.childNodes[1];
}

function get_graph_graph_node(obj) {
    while (obj && !utils.has_class(obj, "graph")) obj = obj.parentNode;
    return obj;
}

// Walk up DOM parents to find the graph container, then walk down to
// find the canvas element which has the graph_id in it's id attribute.
// Strip off the graph_id and return it.
function get_graph_id_of_dom_node(target) {
    var graph_container = get_graph_container(target);
    if (!graph_container) return null;

    return graph_container.id;
}

function graph_global_mouse_wheel(event) {
    event = event || window.event; // IE FIX

    var obj = utils.get_target(event);
    // prevent page scrolling when making wheelies over graphs
    while (obj && !obj.className) obj = obj.parentNode;
    if (obj && obj.tagName == "DIV" && obj.className == "graph_container")
        return utils.prevent_default_events(event);
}

function graph_activate_mouse_control(graph) {
    var canvas = graph["canvas_obj"];
    utils.add_event_handler(
        "mousemove",
        function (event) {
            return graph_mouse_move(event, graph);
        },
        canvas
    );

    utils.add_event_handler(
        "mousedown",
        function (event) {
            return graph_mouse_down(event, graph);
        },
        canvas
    );

    var on_wheel = function (event) {
        return graph_mouse_wheel(event, graph);
    };

    utils.add_event_handler(utils.wheel_event_name(), on_wheel, canvas);
    utils.add_event_handler(utils.wheel_event_name(), graph_global_mouse_wheel);

    utils.add_event_handler("mouseup", global_graph_mouse_up);

    if (
        graph.ajax_context.render_options.show_controls &&
        graph.ajax_context.render_options.resizable
    ) {
        // Find resize img element
        var container = get_graph_container(canvas);
        var resize_img = container.getElementsByClassName("resize")[0];
        utils.add_event_handler(
            "mousedown",
            function (event) {
                return graph_start_resize(event, graph);
            },
            resize_img
        );

        utils.add_event_handler("mousemove", graph_mouse_resize);
    }

    if (graph.ajax_context.render_options.interaction) {
        utils.add_event_handler("mousemove", update_mouse_hovering);
    }
}

function graph_start_resize(event, graph) {
    event = event || window.event; // IE FIX
    g_resizing_graph = {
        pos: [event.clientX, event.clientY],
        graph: graph,
    };
    return utils.prevent_default_events(event);
}

function graph_mouse_resize(event) {
    if (!g_resizing_graph) return true;

    if (g_graph_update_in_process || g_graph_in_cooldown_period)
        return utils.prevent_default_events(event);

    var new_x = event.clientX;
    var new_y = event.clientY;
    var delta_x = new_x - g_resizing_graph.pos[0];
    var delta_y = new_y - g_resizing_graph.pos[1];
    g_resizing_graph.pos = [new_x, new_y];

    var graph = g_resizing_graph.graph;
    var post_data =
        "context=" +
        encodeURIComponent(JSON.stringify(graph.ajax_context)) +
        "&resize_x=" +
        delta_x +
        "&resize_y=" +
        delta_y;

    start_graph_update(graph["canvas_obj"], post_data);
    return utils.prevent_default_events(event);
}

// Get the mouse position of an event in coords of the
// shown time/value system. Return null if the coords
// lie outside.
function graph_get_mouse_position(event, graph) {
    var time = graph_get_click_time(event, graph);
    if (time < graph["time_axis"]["range"][0] || time > graph["time_axis"]["range"][1]) return null; // out of range

    var value = graph_get_click_value(event, graph);
    if (value < graph["vertical_axis"]["range"][0] || value > graph["vertical_axis"]["range"][1])
        return null; // out of range

    return [time, value];
}

function graph_mouse_down(event, graph) {
    event = event || window.event; // IE FIX
    var pos = graph_get_mouse_position(event, graph);
    if (!pos) return;

    // Store information needed for update globally
    g_dragging_graph = {
        pos: pos,
        graph: graph,
    };
    g_graph_update_in_process = false;

    return utils.prevent_default_events(event);
}

function has_mouse_moved(pos1, pos2) {
    if (Math.abs(pos1[0] - pos2[0]) < 1) return false;
    else return true;
}

function global_graph_mouse_up(event) {
    event = event || window.event; // IE FIX

    var graph_id, graph;
    if (g_dragging_graph) {
        graph = g_dragging_graph.graph;
        var pos = graph_get_mouse_position(event, graph);
        if (pos) {
            graph_id = graph["id"];

            // When graph has not been dragged, the user did a simple click
            // Fire the graphs click action or, by default, positions the pin
            if (!has_mouse_moved(g_dragging_graph.pos, pos)) {
                handle_graph_clicked(graph);
                set_pin_position(event, graph, pos[0]);
            }

            if (graph.render_options.interaction) sync_all_graph_timeranges(graph_id);
        }
    } else if (!g_resizing_graph) {
        var target = utils.get_target(event);
        if (
            target.tagName == "TH" &&
            utils.has_class(target, "scalar") &&
            utils.has_class(target, "inactive")
        ) {
            // Click on inactive scalar title: Change graph consolidation function to this one
            graph_id = get_graph_id_of_dom_node(target);
            if (graph_id) {
                graph = g_graphs[graph_id];

                var consolidation_function = "";
                if (utils.has_class(target, "min")) consolidation_function = "min";
                else if (utils.has_class(target, "max")) consolidation_function = "max";
                else consolidation_function = "average";

                handle_graph_clicked(graph);
                set_consolidation_function(event, graph, consolidation_function);
            }
        } else if (target.tagName != "IMG" && target.tagName != "A") {
            graph_id = get_graph_id_of_dom_node(target);
            if (graph_id) {
                graph = g_graphs[graph_id];

                // clicked out of graphical area but on graph: remove the pin
                handle_graph_clicked(graph);
                remove_pin(event, graph);
            }
        }
    }

    g_dragging_graph = null;
    g_resizing_graph = null;
    g_graph_update_in_process = false;
    return true;
}

function handle_graph_clicked(graph) {
    if (graph.render_options.onclick) {
        eval(graph.render_options.onclick);
    }
}

function set_consolidation_function(event, graph, consolidation_function) {
    if (graph.render_options.interaction) {
        update_graph(event, graph, 0.0, null, null, null, null, consolidation_function);
        sync_all_graph_timeranges(graph.id);
    }
}

function remove_pin(event, graph) {
    // Only try to remove the pin when there is currently one
    if (
        graph.render_options.interaction &&
        graph.render_options.show_pin &&
        graph.pin_time !== null
    ) {
        set_pin_position(event, graph, -1);
        sync_all_graph_timeranges(graph.id);
    }
}

function set_pin_position(event, graph, timestamp) {
    if (graph.render_options.interaction && graph.render_options.show_pin)
        return update_graph(event, graph, 0.0, null, null, null, parseInt(timestamp), null);
}

// move is used for dragging and also for resizing
function graph_mouse_move(event, graph) {
    event = event || window.event; // IE FIX

    if (!graph.render_options.interaction) return; // don't do anything when this graph is not allowed to set the pin

    if (g_graph_update_in_process || g_graph_in_cooldown_period) return false;

    if (g_dragging_graph == null || g_dragging_graph.graph.id != graph.id) return false; // Not dragging or dragging other graph

    // Compute new time range
    var time_shift = g_dragging_graph.pos[0] - graph_get_click_time(event, graph);

    // Compute vertical zoom
    var value = graph_get_click_value(event, graph);
    var vertical_zoom = value / g_dragging_graph.pos[1];
    if (vertical_zoom <= 0) vertical_zoom = null; // No mirroring, no zero range

    update_graph(event, graph, time_shift, null, null, vertical_zoom, null, null);

    return utils.prevent_default_events(event);
}

function update_mouse_hovering(event) {
    var canvas = mouse_hovering_canvas_graph_area(event);
    remove_all_mouse_indicators();
    if (!canvas) {
        remove_all_graph_hover_popups();
        return;
    }

    var graph_node = get_graph_graph_node(canvas);
    var graph_id = get_graph_id_of_dom_node(graph_node);
    var graph = g_graphs[graph_id];

    hover.add(graph_node);

    if (!graph.render_options.interaction) return; // don't do anything when this graph is not allowed to set the pin

    var canvas_rect = canvas.getBoundingClientRect();
    update_mouse_indicator(canvas, graph, graph_node, event.clientX - canvas_rect.left);
    update_graph_hover_popup(event, graph);
}

function mouse_hovering_canvas_graph_area(event) {
    var obj = utils.get_target(event);
    if (!obj) return null;

    var graph_id = get_graph_id_of_dom_node(obj);
    if (!graph_id) return null;

    var graph = g_graphs[graph_id];
    var canvas = graph["canvas_obj"];
    var canvas_rect = canvas.getBoundingClientRect();

    if (
        event.clientX < canvas_rect.left ||
        event.clientX > canvas_rect.right ||
        event.clientY < canvas_rect.top ||
        event.clientY > canvas_rect.bottom
    )
        return null; // is not over canvas at all

    // Out of area on the left?
    var v_axis_width = to_display_coord(graph_vertical_axis_width(graph));
    var left_of_area = canvas_rect.left + v_axis_width + 4; // 4 is padding of graph container
    if (event.clientX < left_of_area) return null;

    // Out of area on bottom?
    var bottom_border = to_display_coord(graph_bottom_border(graph));
    var bottom_of_area = canvas_rect.bottom - bottom_border;
    if (event.clientY > bottom_of_area) return null;

    return canvas;
}

function update_mouse_indicator(canvas, graph, graph_node, x) {
    var indicator = document.createElement("div");
    utils.add_class(indicator, "indicator");
    graph_node.appendChild(indicator);

    indicator.style.left = x + "px";
    indicator.style.top = canvas.offsetTop + "px";
    indicator.style.height =
        canvas.clientHeight - to_display_coord(graph_bottom_border(graph)) + "px";
}

function remove_all_mouse_indicators() {
    var indicators = document.getElementsByClassName("indicator");
    for (var i = 0, len = indicators.length; i < len; i++) {
        indicators[i].parentNode.removeChild(indicators[i]);
    }
}

function graph_mouse_wheel(event, graph) {
    event = event || window.event; // IE FIX

    if (!graph.render_options.interaction) return; // don't do anything when this graph is not allowed to set the pin

    if (g_graph_update_in_process) return utils.prevent_default_events(event);

    var time_zoom_center = graph_get_click_time(event, graph);
    var delta = utils.wheel_event_delta(event);

    var zoom = null;
    if (delta > 0) {
        zoom = 1.1;
    } else {
        // Do not zoom further in if we already display only 10 points or less
        var curves = graph["curves"];
        if (curves.length == 0) return true;
        var curve = curves[0];
        var points = curve["points"];
        if (points.length <= 10) return true;

        zoom = 1 / 1.1;
    }

    if (!update_graph(event, graph, 0.0, zoom, time_zoom_center, null, null, null)) return false;

    /* Also zoom all other graphs on the page */
    var graph_id = graph.id;
    if (g_graph_wheel_timeout) clearTimeout(g_graph_wheel_timeout);
    g_graph_wheel_timeout = setTimeout(function () {
        sync_all_graph_timeranges(graph_id);
    }, 500);

    return utils.prevent_default_events(event);
}

function graph_get_click_time(event, graph) {
    var canvas = utils.get_target(event);

    // Get X position of mouse click, converted to canvas pixels
    var x = (get_event_offset_x(event) * canvas.width) / canvas.clientWidth;

    // Convert this to a time value and check if its within the visible range
    var t_offset = (x - graph["time_origin"]) / graph["time_axis"]["pixels_per_second"];
    return graph["time_axis"]["range"][0] + t_offset;
}

function graph_get_click_value(event, graph) {
    var canvas = utils.get_target(event);

    // Get Y position of mouse click, converted to canvas pixels
    var y = (get_event_offset_y(event) * canvas.height) / canvas.clientHeight;

    // Convert this to a vertical value and check if its within the visible range
    var v_offset = -(y - graph["vertical_origin"]) / graph["vertical_axis"]["pixels_per_unit"];
    return graph["vertical_axis"]["range"][0] + v_offset;
}

function get_event_offset_x(event) {
    return event.offsetX == undefined ? event.layerX : event.offsetX;
}

function get_event_offset_y(event) {
    return event.offsetY == undefined ? event.layerY : event.offsetY;
}

//#.
//#   .-Graph hover--------------------------------------------------------.
//#   |        ____                 _       _                              |
//#   |       / ___|_ __ __ _ _ __ | |__   | |__   _____   _____ _ __      |
//#   |      | |  _| '__/ _` | '_ \| '_ \  | '_ \ / _ \ \ / / _ \ '__|     |
//#   |      | |_| | | | (_| | |_) | | | | | | | | (_) \ V /  __/ |        |
//#   |       \____|_|  \__,_| .__/|_| |_| |_| |_|\___/ \_/ \___|_|        |
//#   |                      |_|                                           |
//#   '--------------------------------------------------------------------'

function update_graph_hover_popup(event, graph) {
    if (g_graph_update_in_process || g_graph_in_cooldown_period)
        return utils.prevent_default_events(event);

    var hover_timestamp = graph_get_click_time(event, graph);

    if (!hover_timestamp) return utils.prevent_default_events(event);

    if (
        hover_timestamp < graph["time_axis"]["range"][0] ||
        hover_timestamp > graph["time_axis"]["range"][1]
    )
        return utils.prevent_default_events(event);

    var post_data =
        "context=" +
        encodeURIComponent(JSON.stringify(graph.ajax_context)) +
        "&hover_time=" +
        encodeURIComponent(parseInt(hover_timestamp));

    g_graph_update_in_process = true;
    set_graph_update_cooldown();

    ajax.call_ajax("ajax_graph_hover.py", {
        method: "POST",
        response_handler: handle_graph_hover_popup_update,
        handler_data: {
            graph: graph,
            event: event,
        },
        post_data: post_data,
    });
}

function handle_graph_hover_popup_update(handler_data, ajax_response, http_code) {
    if (http_code !== undefined) {
        //console.log("Error calling AJAX web service for graph hover update: " + ajax_response);
        g_graph_update_in_process = false;
        return;
    }

    try {
        var popup_data = JSON.parse(ajax_response);
    } catch (e) {
        console.log(e);
        alert("Failed to parse graph hover update response: " + ajax_response);
        g_graph_update_in_process = false;
        return;
    }

    render_graph_hover_popup(handler_data.graph, handler_data.event, popup_data);

    //render_graph_and_subgraphs(graph);
    g_graph_update_in_process = false;
}

// Structure of popup_data:
// {
//    "curve_values": [
//        {
//            "color": "#00d1ff",
//            "rendered_value": [0.5985, "0.599"],
//            "title": "CPU load average of last minute"
//        },
//        {
//            "color": "#2c5766",
//            "rendered_value": [0.538, "0.538"],
//            "title": "CPU load average of last 15 minutes"
//        }
//     ],
//     "rendered_hover_time": "2018-09-26 16:34:54"
// }
function render_graph_hover_popup(graph, event, popup_data) {
    var wrapper = document.createElement("div");

    var popup_container = document.createElement("div");
    utils.add_class(popup_container, "graph_hover_popup");
    wrapper.appendChild(popup_container);

    var time = document.createElement("div");
    utils.add_class(time, "time");
    time.innerText = popup_data.rendered_hover_time;
    popup_container.appendChild(time);

    var entries = document.createElement("table");
    utils.add_class(entries, "entries");
    popup_container.appendChild(entries);

    popup_data.curve_values.forEach(curve => {
        let row = entries.insertRow();
        let title = row.insertCell(0);
        let color = document.createElement("div");
        utils.add_class(color, "color");
        color.style.backgroundColor = hex_to_rgba(curve.color + "4c");
        color.style.borderColor = curve.color;
        title.appendChild(color);
        title.appendChild(document.createTextNode(curve.title + ": "));

        let value = row.insertCell(1);
        utils.add_class(value, "value");
        value.innerText = curve.rendered_value[1];
    });

    hover.update_content(wrapper.innerHTML, event);
}

// Hide the tooltips that show the metric values at the position of the pointer
function remove_all_graph_hover_popups() {
    for (const menu of document.getElementsByClassName("hover_menu")) {
        const graph_container = menu.getElementsByClassName("graph_hover_popup");
        if (graph_container.length > 0) {
            hover.hide();
        }
    }
}

//#.
//#   .-Graph-Update-------------------------------------------------------.
//#   |   ____                 _           _   _           _       _       |
//#   |  / ___|_ __ __ _ _ __ | |__       | | | |_ __   __| | __ _| |_ ___ |
//#   | | |  _| '__/ _` | '_ \| '_ \ _____| | | | '_ \ / _` |/ _` | __/ _ \|
//#   | | |_| | | | (_| | |_) | | | |_____| |_| | |_) | (_| | (_| | ||  __/|
//#   |  \____|_|  \__,_| .__/|_| |_|      \___/| .__/ \__,_|\__,_|\__\___||
//#   |                 |_|                     |_|                        |
//#   +--------------------------------------------------------------------+
//#   | Handles re-rendering of graphs after user actions                  |
//#   '--------------------------------------------------------------------'

// TODO: Refactor the arguments to use something like ajax.call_ajax(). Makes things much clearer.
function update_graph(
    event,
    graph,
    time_shift,
    time_zoom,
    time_zoom_center,
    vertical_zoom,
    pin_timestamp,
    consolidation_function
) {
    var canvas = graph["canvas_obj"];

    var start_time;
    var end_time;

    // Time zoom
    if (time_zoom != null) {
        // The requested start/end time can differ from the real because
        // RRDTool align the times as it needs. The graph always is align
        // to the RRDTool data, but the zooming into small time intervals
        // does not work correctly if we do not base this on the requested start_time.
        start_time =
            time_zoom_center - (time_zoom_center - graph["requested_start_time"]) * time_zoom;
        end_time = time_zoom_center + (graph["requested_end_time"] - time_zoom_center) * time_zoom;

        // Sanity check
        if (end_time < start_time) {
            end_time = start_time + 60;
            start_time -= 60;
        }

        // Do not allow less than 120 secs.
        var range = end_time - start_time;
        if (range < 120) {
            var diff = 120 - range;
            start_time -= ((time_zoom_center - start_time) / 120) * diff;
            end_time += ((end_time - time_zoom_center) / 120) * diff;
        }
    }

    // Time shift
    else {
        start_time = graph["start_time"] + time_shift;
        end_time = graph["end_time"] + time_shift;
    }

    // Check for range
    if (
        start_time < 0 ||
        end_time < 0 ||
        start_time > 2147483646 ||
        end_time > 2147483646 ||
        start_time > end_time
    ) {
        return true;
    }

    // Vertical zoom
    var range_from = null;
    var range_to = null;
    if (vertical_zoom != null) {
        var old_range_from = graph["vertical_axis"]["range"][0];
        var old_range_to = graph["vertical_axis"]["range"][1];
        range_from = old_range_from / vertical_zoom;
        range_to = old_range_to / vertical_zoom;
    } else if (graph["requested_vrange"] != null) {
        range_from = graph["requested_vrange"][0];
        range_to = graph["requested_vrange"][1];
    }

    // Recompute step
    var step = (end_time - start_time) / canvas.width / 2;

    // wenn er einmal grob wurde, nie wieder fein wird, auch wenn man in
    // einen Bereich draggt, der wieder fein vorhanden wäre? Evtl. müssen
    // wir den Wunsch-Step neu berechnen. Oder sicher speichern, also
    // den ursprügnlichen Wunsch-Step anders als den vom RRD zurückgegebene.

    var post_data =
        "context=" +
        encodeURIComponent(JSON.stringify(graph.ajax_context)) +
        "&start_time=" +
        encodeURIComponent(start_time) +
        "&end_time=" +
        encodeURIComponent(end_time) +
        "&step=" +
        encodeURIComponent(step);

    if (range_from != null) {
        post_data +=
            "&range_from=" +
            encodeURIComponent(range_from) +
            "&range_to=" +
            encodeURIComponent(range_to);
    }

    if (pin_timestamp != null) {
        post_data += "&pin=" + encodeURIComponent(pin_timestamp);
    }

    if (consolidation_function != null) {
        post_data += "&consolidation_function=" + encodeURIComponent(consolidation_function);
    }

    if (g_graph_update_in_process) return utils.prevent_default_events(event);

    start_graph_update(canvas, post_data);
    return true;
}

function start_graph_update(canvas, post_data) {
    g_graph_update_in_process = true;

    set_graph_update_cooldown();
    reload_pause.pause(g_page_update_delay);

    ajax.call_ajax("ajax_graph.py", {
        method: "POST",
        response_handler: handle_graph_update,
        handler_data: get_graph_container(canvas),
        post_data: post_data,
    });
}

function set_graph_update_cooldown() {
    g_graph_in_cooldown_period = true;
    setTimeout(function () {
        g_graph_in_cooldown_period = false;
    }, 100);
}

function handle_graph_update(graph_container, ajax_response, http_code) {
    if (http_code !== undefined) {
        //console.log("Error calling AJAX web service for graph update: " + ajax_response);
        g_graph_update_in_process = false;
        return;
    }

    try {
        var response = JSON.parse(ajax_response);
    } catch (e) {
        console.log(e);
        alert("Failed to parse graph update response: " + ajax_response);
        return;
    }
    // Structure of response:
    // {
    //     "html" : html_code,
    //     "graph" : graph_artwork,
    //     "context" : {
    //         "graph_id"       : context["graph_id"],
    //         "definition"     : graph_recipe,
    //         "data_range"     : graph_data_range,
    //         "render_options" : graph_render_options,
    // }
    var graph_id = response.context.graph_id;
    var graph = response.graph;
    graph["id"] = graph_id;
    graph["ajax_context"] = response.context;
    graph["render_options"] = graph["ajax_context"]["render_options"];
    g_graphs[graph_id] = graph;

    // replace eventual references
    if (g_dragging_graph && g_dragging_graph.graph.id == graph.id) g_dragging_graph.graph = graph;
    if (g_resizing_graph && g_resizing_graph.graph.id == graph.id) g_resizing_graph.graph = graph;

    graph_container.innerHTML = response["html"];

    render_graph_and_subgraphs(graph);
    g_graph_update_in_process = false;
}

// re-render the given graph and check whether or not there are subgraphs
// which need to be re-rendered too.
function render_graph_and_subgraphs(graph) {
    render_graph(graph);

    for (var graph_id in g_graphs) {
        if (graph_id != graph.id && graph_id.substr(0, graph.id.length) == graph.id) {
            render_graph(g_graphs[graph_id]);
        }
    }
}

// Is called on the graph overview page when clicking on a timerange
// graph to change the timerange of the main graphs.
export function change_graph_timerange(graph, duration) {
    // Find the main graph by DOM tree:
    // <div class=graph_with_timeranges><div container of maingraph></td><table><tr><td>...myself
    var maingraph_container = get_main_graph_container(graph["canvas_obj"]);

    var main_graph_id = maingraph_container.id;
    var main_graph = g_graphs[main_graph_id];

    var now = Math.floor(new Date().getTime() / 1000);

    main_graph.start_time = now - duration;
    main_graph.end_time = now;

    reload_pause.pause(g_page_update_delay);
    sync_all_graph_timeranges(main_graph_id, false);
}

function update_pdf_export_link_timerange(start_time, end_time) {
    var context_buttons = document.getElementsByClassName("context_pdf_export");
    for (var i = 0; i < context_buttons.length; i++) {
        var context_button = context_buttons[i];
        if (context_button != undefined) {
            var link = context_button.getElementsByTagName("a")[0];
            link.href = utils.makeuri({start_time: start_time, end_time: end_time}, link.href);
        }
    }
}

var g_timerange_update_queue = [];

// Syncs all graphs on this page to the same time range as the selected graph.
// Be aware: set_graph_timerange triggers an AJAX request. Most browsers have
// a limit on the concurrent AJAX requests, so we need to slice the requests.
function sync_all_graph_timeranges(graph_id, skip_origin) {
    if (skip_origin === undefined) skip_origin = true;

    g_timerange_update_queue = []; // abort all pending requests

    var graph = g_graphs[graph_id];
    for (var name in g_graphs) {
        // only look for the other graphs. Don't update graphs having fixed
        // time ranges, like the timerange chooser graphs on the overview page
        if ((!skip_origin || name != graph_id) && !g_graphs[name].render_options.fixed_timerange) {
            g_timerange_update_queue.push([name, graph.start_time, graph.end_time]);
        }
    }

    update_delayed_graphs_timerange(graph.start_time, graph.end_time);
    update_pdf_export_link_timerange(graph.start_time, graph.end_time);

    // Kick off 4 graph timerange updaters (related to the number of maximum
    // parallel AJAX request)
    for (var i = 0; i < 4; i++) update_next_graph_timerange();
}

function update_next_graph_timerange() {
    var job = g_timerange_update_queue.pop();
    if (job) set_graph_timerange(job[0], job[1], job[2]);
}

function set_graph_timerange(graph_id, start_time, end_time) {
    var graph = g_graphs[graph_id];
    var canvas = graph["canvas_obj"];
    if (canvas) {
        var step = (end_time - start_time) / canvas.width / 2;

        // wenn er einmal grob wurde, nie wieder fein wird, auch wenn man in
        // einen Bereich draggt, der wieder fein vorhanden wäre? Evtl. müssen
        // wir den Wunsch-Step neu berechnen. Oder sicher speichern, also
        // den ursprügnlichen Wunsch-Step anders als den vom RRD zurückgegebene.

        var post_data =
            "context=" +
            encodeURIComponent(JSON.stringify(graph.ajax_context)) +
            "&start_time=" +
            encodeURIComponent(start_time) +
            "&end_time=" +
            encodeURIComponent(end_time) +
            "&step=" +
            encodeURIComponent(step);

        ajax.call_ajax("ajax_graph.py", {
            method: "POST",
            post_data: post_data,
            response_handler: handle_graph_timerange_update,
            handler_data: get_graph_container(canvas),
        });
    }
}

// First updates the current graph and then continues with the next graph
function handle_graph_timerange_update(graph_container, ajax_response, http_code) {
    handle_graph_update(graph_container, ajax_response, http_code);
    update_next_graph_timerange();
}
